# meshterm

> Linux terminal emulator with iTerm2-compatible programmatic control.

**Version:** 0.2.8 | **Status:** Beta | **Tests:** 246 passing | **Python 3.11+** | **License:** Apache-2.0

## Platform Support

| Platform | Status | Setup |
|----------|--------|-------|
| **Linux** (Ubuntu 20.04+, Fedora 35+, Debian 11+) | Primary target, fully tested | `apt/dnf install tmux && pip install "meshterm[cli,backend-tmux]"` |
| **macOS 12+** | Cross-platform Python API + libtmux | `brew install tmux && pip install "meshterm[cli,backend-tmux]"` |
| **Windows 10/11 + WSL2** | Should work (untested) | `wsl --install` then follow Linux command **inside WSL2** |
| **Windows native (no WSL)** | Not supported | See note below |

**Why no native Windows?** meshterm depends on Unix sockets (IPC), POSIX signals
(`SIGHUP`), and `tmux` (libtmux backend). None have native Windows equivalents.
**WezTerm** is the closest tmux alternative on native Windows (38/40 rubric vs
tmux 36/40); a `wezterm` backend is tracked as a future feature (v0.4.0+ if
community demand emerges).

**Windows users — recommended path** (~10 minutes setup):

1. **PowerShell (Admin):** `wsl --install -d Ubuntu-22.04` → reboot
2. Inside WSL2 Ubuntu:
   ```bash
   sudo apt update && sudo apt install -y python3.11 python3-pip tmux
   pip install "meshterm[cli,backend-tmux]"
   meshterm --help
   ```
3. **VSCode integration**: install
   [Remote — WSL extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-wsl)
   for native UX.

---

## What is it?

`meshterm` is a Python package that provides:

1. An **iTerm2-compatible API** for scripting terminal sessions on Linux
   (where iTerm2 itself is macOS-only). The `MeshTermApp`, `MeshTermWindow`,
   `MeshTermTab`, and `MeshTermSession` classes mirror iTerm2's Python API
   surface so the same patterns work on both platforms.

2. A **libtmux-backed backend** (primary) that wraps `tmux` for robust session
   control without custom PTY management.

3. A **custom PTY server** (experimental) using `pyte` for VT100 parsing and
   JSON-RPC 2.0 over a Unix domain socket for client/server IPC.

4. **Claude Code conversation introspection** via `JsonlHistory` — reads
   `~/.claude/projects/<slug>/<UUID>.jsonl` to extract tool calls, thinking
   blocks, and semantic message history.

5. **Remote SSH control** via `RemoteMeshTerm` (paramiko) — drive another
   host's tmux sessions over SSH with strict host-key verification and
   session-name whitelisting.

6. **Idle detection** via `Monitor` / `IdleChecker` for triggering actions
   when a terminal becomes quiescent.

7. **Shell history introspection** via `BashHistory` for reading
   `~/.bash_history`.

---

## Installation

```bash
pip install "meshterm[cli,backend-tmux]"
```

Extras:

- `[cli]` — `click` + `rich` for the command-line interface
- `[backend-tmux]` — `libtmux` (required for `LibtmuxSession`)
- `[test]` — `pytest`, `pytest-asyncio`, `hypothesis`, `paramiko` for testing
- `paramiko` is also pulled in transitively if you use `RemoteMeshTerm`

---

## Quick start — iTerm2-compatible async API

```python
import meshterm

async def main():
    async with meshterm.Connection.unix() as conn:
        app = await meshterm.async_get_app(conn)
        session = app.current_window.current_tab.current_session
        await session.async_send_text("echo hello\r")
        contents = await session.async_get_screen_contents()
        for line in contents.lines:
            print(line.string)

meshterm.run_until_complete(main)
```

## Quick start — libtmux backend (recommended)

```python
from meshterm.libtmux_session import LibtmuxSession

# Look up an existing tmux session by name
s = LibtmuxSession.from_name("worker-1")
print(f"UUID: {s.uuid}, PID: {s.pid}, CWD: {s.cwd}")
print(f"Current command: {s.current_command}")

# Send a command using the SEND-VERIFY-PROCEED pattern
s.send_command("pytest tests/ -q", wait=1.0)

# Read the screen
screen = s.read_screen()
for line in screen.lines[-10:]:
    print(line.string)

# Wait for a specific output pattern
s.wait_for("passed", timeout=30)
```

## Quick start — RemoteMeshTerm (SSH)

```python
from meshterm import RemoteMeshTerm

# Strict host-key verification by default (F1 hardening)
# Use SSH keys; password auth emits DeprecationWarning (F2 hardening)
with RemoteMeshTerm(
    host="192.0.2.4",
    username="server",
    key_filename="~/.ssh/id_ed25519",
    # strict_host_keys=True is the default; unknown hosts are REJECTED
) as rt:
    # Session names are validated against [a-zA-Z0-9_.-]+ (F6 hardening)
    rt.send_text("worker-1", "pytest tests/ -q", enter=True)
    screen = rt.read_screen_text("worker-1", lines=30)
    print(screen)
```

## Quick start — Claude Code JSONL introspection

```python
from meshterm import JsonlHistory

# Load a Claude Code session by UUID
hist = JsonlHistory.from_uuid("d647c698-ffa4-424e-b5ef-d452a053ba8f")
print(f"Total entries: {len(hist)}")
print(f"Tool call counts: {hist.tool_call_counts()}")

# Inspect every Bash command the model issued
for tc in hist.tool_calls(name="Bash"):
    print(f"[{tc.timestamp}] {tc.arg('command')[:80]}")
    if tc.result:
        print(f"  -> {tc.result[:80]}")

# Extract chain-of-thought
for thinking in hist.thinking_blocks():
    print(thinking.preview)

# One-shot summary
hist.print_summary()
```

## Quick start — Idle detection

```python
from meshterm import Monitor, MonitorConfig

def on_idle(idle_seconds, sessions):
    print(f"All {len(sessions)} sessions idle for {idle_seconds:.0f}s")

cfg = MonitorConfig(idle_threshold=900, poll_interval=5)
mon = Monitor(config=cfg)
mon.on_trigger(on_idle)
mon.start(blocking=False)  # returns immediately, runs in a daemon thread
```

---

## Architecture

```
    Client (Python)
         |
         |  iTerm2-compatible API
         |  (async/await)
         v
    +------------------------+
    |   MeshTermApp          |
    |   |-- MeshTermWindow   |
    |   |   \-- MeshTermTab  |
    |   |       \-- Session  |
    |   \-- ScreenContents   |
    +------------------------+
         |
         |  JSON-RPC 2.0 over Unix socket
         |  (local only, cookie auth)
         v
    +------------------------+
    |   MeshTermServer       |
    |   |-- PTY management   |
    |   |-- pyte VT parser   |
    |   \-- Session registry |
    +------------------------+

Alternative (primary) path - direct libtmux:

    LibtmuxSession.from_name("worker-1")
         |
         |  libtmux (ORM over tmux CLI)
         v
    +------------------------+
    |   tmux server          |
    |   |-- session "worker-1"
    |   |   \-- pane %0      |
    |   \-- session "worker-2"
    |       \-- pane %1      |
    +------------------------+

Remote path - RemoteMeshTerm:

    RemoteMeshTerm(host, key_filename=...)
         |
         |  paramiko SSH
         |  (strict host keys, key auth preferred)
         v
    +------------------------+
    |   Remote tmux server   |
    |   (shlex.quote + name  |
    |    whitelist)          |
    +------------------------+
```

---

## Security model

| ID | Severity | Finding | Fix |
|---|---|---|---|
| F1 | HIGH | `RemoteMeshTerm` used `AutoAddPolicy` (MITM risk) | `RejectPolicy` is now default; `strict_host_keys=True` enforces strict verification; opt-out requires explicit flag and emits `UserWarning` |
| F2 | HIGH | `RemoteMeshTerm.password` stored in memory | `DeprecationWarning` on use; `key_filename` is the recommended path; local reference dropped after `connect()` |
| F3 | HIGH | `MeshTermServer._h_session_send_text` had no length limit (PTY DoS) | `_MAX_SEND_TEXT_BYTES = 1 MiB` hard limit; `ValueError` on overflow |
| F4 | MEDIUM | `MESHTERM_NO_AUTH=1` bypass silently | Runtime warning emitted when auth is disabled |
| F5 | MEDIUM | Socket permission TOCTOU race | `os.umask(0o077)` set before `start_unix_server` |
| F6 | MEDIUM | tmux session names not validated (injection risk) | `_validate_session_name` whitelist `[a-zA-Z0-9_.-]+`, wired into all 14 public methods |
| F7 | LOW | Cookie file permission TOCTOU race | `os.open(..., O_CREAT, 0o600)` atomic creation |

### Key security properties

- **Local-only IPC.** The custom PTY server binds to
  `$XDG_RUNTIME_DIR/meshterm/ipc.sock` with 0o600 permissions. No network
  exposure. Cookie authentication prevents cross-user access.
- **Strict SSH host keys.** `RemoteMeshTerm` rejects unknown host keys by
  default. System `known_hosts` is loaded automatically; an optional
  `known_hosts_file` parameter supports dedicated key stores.
- **Session-name whitelist.** Every method taking a tmux session name calls
  `_validate_session_name`, which enforces non-empty, no-leading-dash, length
  <= 128, and the `[a-zA-Z0-9_.-]+` regex. `shlex.quote` provides
  defense-in-depth on top of the whitelist.
- **Payload limits.** `_h_session_send_text` rejects inputs larger than
  1 MiB. Escape-sequence filtering is intentionally *not* applied, because
  legitimate workflows (ANSI colors, control keys, arrow-key navigation)
  depend on them; the length limit is the pragmatic front-line defense.

---

## Module overview

| Module | Purpose |
|---|---|
| `meshterm.app` | `MeshTermApp` — application root, windows/sessions registry |
| `meshterm.window` / `meshterm.tab` | Window and tab management (mostly stubs pending GUI integration) |
| `meshterm.session` | `MeshTermSession` — client-side session proxy + `ScreenContents` dataclass |
| `meshterm.server` | `MeshTermServer` — experimental custom PTY server with JSON-RPC dispatch |
| `meshterm.connection` | Unix-socket client + cookie authentication |
| `meshterm.libtmux_session` | `LibtmuxSession`, `LibtmuxApp` — primary backend (libtmux) |
| `meshterm.remote` | `RemoteMeshTerm` — SSH-based remote tmux control |
| `meshterm.jsonl_history` | `JsonlHistory`, `ToolCall`, `ThinkingBlock`, `Message` — Claude Code conversation reader |
| `meshterm.bash_history` | `BashHistory` — shell command history reader |
| `meshterm.idle` | `IdleChecker` — per-session idle state machine |
| `meshterm.monitor` | `Monitor` — daemon-style multi-session idle detection with callbacks |
| `meshterm.idle_monitor` | `IdleMonitor` — async variant of `Monitor` for custom-backend servers |
| `meshterm.cli` | `meshterm` command-line interface (Click-based) |

---

## Testing

```bash
pytest tests/ -q
```

**Coverage** (v0.2.8):

- `tests/unit/` — pure unit tests (no external dependencies, paramiko mocked)
- `tests/integration/` — live tmux tests (requires `tmux` installed)
- `tests/test_idle.py`, `tests/test_live_tmux.py`, `tests/test_stress.py`
  — additional suites

Total: **246 passing, 21 skipped** (skipped = platform-specific, mostly
macOS-only paths).

Security-focused tests include:

- `test_jsonl_history.py` — JSONL parsing, malformed-line handling,
  tool-call extraction, thinking-block extraction, message summaries.
- `test_bash_history.py` — history loading, search (case-sensitive and
  case-insensitive), command-frequency counting, reload.
- `test_remote.py` — `_validate_session_name` whitelist (12+ attack vectors),
  strict-host-keys default, password-deprecation warning, wiring of the
  validator into all 14 public methods.

---

## VS Code Integration

For **zero-code** VS Code terminal integration that works on Mac, Linux,
Remote-SSH, and WSL, see [docs/VSCODE.md](docs/VSCODE.md). The approach uses
VS Code's terminal profile system to auto-launch a tmux session inside each
new terminal tab, which meshterm then controls transparently.

```jsonc
// settings.json (Mac example)
{
  "terminal.integrated.profiles.osx": {
    "meshterm (tmux sidecar)": {
      "path": "/bin/zsh",
      "args": ["-l", "-c",
               "tmux new-session -A -s vscode-$(hostname -s)-$$"]
    }
  },
  "terminal.integrated.defaultProfile.osx": "meshterm (tmux sidecar)"
}
```

Once applied, `LibtmuxSession.from_name("vscode-*")` can drive the VS Code
terminal from any Python process on the same machine, and `RemoteMeshTerm`
can drive it over SSH. See the doc for Linux, WSL, session-naming
strategies, troubleshooting, and integration with sister projects.

---

## Roadmap

- **Type hints** on all public API surfaces (`mypy --strict` clean)
- **Integration tests** against a real SSH server (OpenSSH or docker)
- **Fuzz testing** for `_validate_session_name` using `hypothesis`
- **tmux control-mode** real-time event stream (replaces poll loop)
- **Remote PTY bridge** — wrap `MeshTermServer` over SSH for fully symmetric
  client/server over the network
- **WezTerm backend** for native Windows support (v0.4.0+ if demand emerges)

---

## License

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

---

## The mesh-trio: why these three projects exist together

`meshterm` is the **terminal control layer** of the **mesh-trio** ecosystem.

| Layer | Project | Role |
|-------|---------|------|
| Communication | [claude-mesh](https://github.com/umitkacar/claude-mesh) | Cross-platform bidirectional message passing between Claude Code sessions across machines. |
| Terminal control | **meshterm** (this project) | Linux terminal automation with iTerm2-compatible Python API; drives `tmux` sessions locally and over SSH. |
| Observation | [meshboard](https://github.com/umitkacar/meshboard) | Real-time dashboard that ingests events from claude-mesh + meshterm and renders them as a live web UI. |

### Why use meshterm with the others?

- **claude-mesh + meshterm**: claude-mesh's `meshterm` transport (soft-imported)
  uses meshterm's local IPC socket to drive a Linux Claude Code terminal
  without an SSH hop. Faster than SSH for same-host workflows.
- **meshterm + meshboard**: meshboard's `meshterm_producer` subscribes to
  meshterm session events (idle/busy/output-changed) and surfaces them in the
  live dashboard for human oversight.
- **All three together**: an operator workstation runs meshboard, sees a
  unified timeline of (a) communication events from claude-mesh and
  (b) terminal events from meshterm, across the entire colony.

### How to use them together

```bash
# On a Linux node (Ubuntu/Fedora/Debian)
pip install "meshterm[cli,backend-tmux]"
tmux new-session -A -s claude-worker
meshterm status                         # list tmux sessions
meshterm send claude-worker "echo hi"   # drive the session

# On the same node, optional: install claude-mesh + meshboard
pip install claude-mesh meshboard

# Now claude-mesh can route messages via meshterm IPC instead of SSH
mesh --transport meshterm send eagle "task complete"

# And meshboard can observe meshterm session activity in real time
meshboard       # http://localhost:8585/live
```

## Credits

**Author:** Dr. Umit Kacar — [github.com/umitkacar](https://github.com/umitkacar)
**Email:** kacarumit.phd@gmail.com

Inspired by iTerm2's Python API (Mac-native).
