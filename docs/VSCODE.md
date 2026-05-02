# VS Code Integration — Zero-Code tmux Sidecar

**Status:** Phase 1 (stable) — Phase 2 (extension) pending
**Target audiences:** Mac, Linux, Remote-SSH, WSL, Dev Containers
**Philosophy:** meshterm already controls tmux; if VS Code's integrated terminal
*lives inside tmux*, meshterm controls it transparently.

---

## Why

VS Code's integrated terminal runs on top of `xterm.js` and does **not**
expose a Python scripting API like iTerm2 does. Three approaches are
possible for programmatic control:

1. **Write a VS Code extension** — full native integration, 15-25 hours of
   work, requires TypeScript, maintenance burden. Deferred to Phase 2.
2. **OSC 633 shell integration** — limited, fragile across platforms, only
   sees completed commands, cannot inject input. Not recommended.
3. **tmux sidecar** ⭐ — make the VS Code terminal *be* a tmux session.
   Zero code, one settings change, works on every OS VS Code supports.

Phase 1 documents approach 3.

---

## How it works

VS Code lets you define **custom terminal profiles** via
`terminal.integrated.profiles.*`. A profile is just "what program
should run when the user opens a new terminal". By default it's
`bash`/`zsh`. We swap that for:

```bash
/bin/bash -c 'tmux new-session -A -s vscode-$(hostname)-$$'
```

- `tmux new-session -A -s <name>` — attach to `<name>` if it exists,
  otherwise create it (`-A` = attach-or-create)
- `$(hostname)` — pin the session to the current machine (so Remote-SSH
  and WSL get their own sessions, not the host's)
- `$$` — pin to this specific shell PID so opening a second VS Code
  terminal creates a second tmux session instead of attaching to the
  same one (optional — omit for "one terminal per host" behavior)

Once open, meshterm's libtmux backend can find, read, and write to that
session:

```python
from meshterm.libtmux_session import LibtmuxSession
s = LibtmuxSession.from_name("vscode-my-machine-12345")
s.send_command("pytest tests/ -q", wait=1.0)
print(s.read_screen_text()[-500:])
```

---

## Mac configuration

Edit `~/Library/Application Support/Code/User/settings.json`
(or use `Cmd+,` → Settings → search `terminal.integrated.profiles`):

```json
{
  "terminal.integrated.profiles.osx": {
    "meshterm (tmux sidecar)": {
      "path": "/bin/zsh",
      "args": [
        "-l",
        "-c",
        "tmux new-session -A -s vscode-$(hostname -s)-$$"
      ],
      "icon": "terminal-tmux",
      "color": "terminal.ansiGreen"
    }
  },
  "terminal.integrated.defaultProfile.osx": "meshterm (tmux sidecar)"
}
```

**Requirements:**
- `tmux` installed: `brew install tmux`
- zsh available (default shell on modern macOS)

**Verify:**
```bash
# In VS Code terminal (Cmd+`):
echo $TMUX            # Should print a socket path
tmux display-message -p '#S'   # Should print vscode-<hostname>-<pid>
```

---

## Linux configuration

Edit `~/.config/Code/User/settings.json`
(or Remote-SSH: `~/.vscode-server/data/Machine/settings.json`):

```json
{
  "terminal.integrated.profiles.linux": {
    "meshterm (tmux sidecar)": {
      "path": "/bin/bash",
      "args": [
        "-l",
        "-c",
        "tmux new-session -A -s vscode-$(hostname -s)-$$"
      ],
      "icon": "terminal-tmux",
      "color": "terminal.ansiGreen"
    }
  },
  "terminal.integrated.defaultProfile.linux": "meshterm (tmux sidecar)"
}
```

**Requirements:**
- `tmux` installed: `sudo apt install tmux` / `dnf install tmux` / etc.
- Shell: bash (or adapt the profile path)

**Remote-SSH:** The same settings under
`~/.vscode-server/data/Machine/settings.json` on the remote host
make VS Code Remote terminals run in tmux on the remote machine.
meshterm running on that remote machine can then control them.

---

## WSL configuration

WSL uses the Linux profile. Put the settings in **Windows**'s
`%APPDATA%\Code\User\settings.json` under `profiles.linux` key as above,
but *also* define a WSL-specific variant if you use multiple distros:

```json
{
  "terminal.integrated.profiles.windows": {
    "meshterm (tmux sidecar in WSL)": {
      "path": "wsl.exe",
      "args": ["-d", "Ubuntu", "bash", "-lc",
               "tmux new-session -A -s vscode-wsl-$$"]
    }
  },
  "terminal.integrated.defaultProfile.windows": "meshterm (tmux sidecar in WSL)"
}
```

---

## Session naming strategies

The default `vscode-$(hostname)-$$` gives one tmux session per VS Code
terminal tab. Alternatives depending on your workflow:

| Name pattern | Behavior | Use case |
|---|---|---|
| `vscode-$(hostname)-$$` | One session per tab | Independent workspaces per tab |
| `vscode-$(hostname)` | One session per machine | Shared state across tabs |
| `vscode-$(pwd | sha1sum | cut -c1-8)` | One session per project dir | Project-scoped control |
| `vscode-agent-$(id -un)` | One session per user | Multi-user dev machines |

Swap the `-s` argument to try any of these.

---

## Control with meshterm

Once a VS Code terminal is running inside tmux, you can drive it
from anywhere meshterm is installed:

### Local control (same machine)

```python
from meshterm.libtmux_session import LibtmuxSession

# List all VS Code sessions
import libtmux
for s in libtmux.Server().sessions:
    if s.name.startswith("vscode-"):
        print(s.name)

# Attach by exact name
s = LibtmuxSession.from_name("vscode-my-laptop-12345")
s.send_command("git status", wait=1.0)
print(s.read_screen_text())
```

### Remote control (over SSH)

```python
from meshterm.remote import RemoteMeshTerm

with RemoteMeshTerm(
    host="dev-box.internal",
    username="me",
    key_filename="~/.ssh/id_ed25519",
) as rt:
    # Discover VS Code tmux sessions on the remote host
    for s in rt.list_sessions():
        if s["name"].startswith("vscode-"):
            print(f"  {s['name']}")
    # Send to the first one
    rt.send_text("vscode-dev-box-22345", "npm test\r", enter=False)
```

### Via claude-mesh

If claude-mesh is installed, the same session is reachable through the
mesh router:

```python
from claude_mesh.transport import get_transport
t = get_transport("meshterm")
await t.send_text("vscode-my-laptop-12345", "python -m pytest\r")
```

---

## Shell integration ≠ replacement

VS Code's built-in shell integration (OSC 633) still works inside tmux.
Command detection, command history, gutter marks — all functional.
tmux is transparent to VS Code's terminal features.

Exception: the "Terminal: Focus Next Command" shortcut walks VS Code's
command record, not tmux's scrollback. If you want that to work over
tmux history, use `Ctrl+B, PgUp` (tmux copy mode) instead.

---

## Troubleshooting

### "tmux not found" when opening a new terminal
Install tmux on the target OS. For Remote-SSH, install on the remote
machine, not locally.

### "session already exists" errors
The profile uses `-A` so attach-or-create is the default. If you see
this error it usually means two profiles are racing. Clean up stale
sessions: `tmux kill-server`.

### Ctrl+B conflicts with VS Code shortcuts
VS Code grabs `Ctrl+B` for the sidebar toggle. Options:
1. Remap tmux prefix: `~/.tmux.conf` → `set -g prefix C-a`
2. Remap VS Code shortcut: bind `workbench.action.toggleSidebarVisibility`
   to something else.

### Mouse doesn't work in tmux inside VS Code
Add to `~/.tmux.conf`:
```
set -g mouse on
```
Reload: `tmux source-file ~/.tmux.conf`

### VS Code scrolls instead of tmux
When mouse mode is enabled, tmux grabs scroll events. Hold `Shift`
while scrolling to let VS Code handle it (native selection works too).

---

## Phase 2 — Future: VS Code Extension

A dedicated extension would offer:
- A status bar button showing "connected to mesh"
- Command palette: `Mesh: Send to agent`, `Mesh: Read agent`
- Configurable session naming without editing JSON
- Native notification when another mesh agent pings your terminal
- Token-authenticated local bridge (no tmux exposure needed)

Scope: 15-25 hours, TypeScript, published to VS Code Marketplace.
Deferred until after UERC 2026 (focus on the core mission first).

---

## Summary

- **Zero code change** to meshterm or claude-mesh
- **One settings change** per VS Code workspace
- **Works on** Mac, Linux, WSL, Remote-SSH, Dev Containers
- **Preserves** shell integration, native VS Code features
- **Enables** `LibtmuxSession.from_name("vscode-*")` control immediately

See also:
- `README.md` — main meshterm docs
- `remote.py` — SSH-based cross-host control
- `libtmux_session.py` — the primary backend
