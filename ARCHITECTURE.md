# meshterm Architecture

**Version:** 0.2.0 | **Date:** 2026-03-30

---

## Overview

meshterm is a custom PTY-based terminal server with Unix domain socket IPC and an iTerm2-compatible Python API. It is NOT a tmux wrapper. The server owns real PTY file descriptors, runs a pyte VT100 parser to maintain screen state, and exposes control via JSON-RPC 2.0 over length-prefixed Unix socket frames.

The client-side API mirrors iTerm2's Python scripting interface (`App`, `Window`, `Tab`, `Session`) so that scripts written for iTerm2 on macOS can run on Linux with minimal changes.

```
+---------------------------------------------------+
|              meshterm server process               |
|                                                    |
|  os.openpty()  -->  PTY master fd                  |
|  pyte.Screen   -->  VT100 parsed screen state      |
|  MeshTermServer --> JSON-RPC dispatch over UDS     |
+---------------------------------------------------+
         |  Unix domain socket
         |  JSON-RPC 2.0, length-prefix framing
         |
+---------------------------------------------------+
|              Client (same or external process)      |
|                                                    |
|  Connection     -->  async JSON-RPC client          |
|  MeshTermApp    -->  App/Window/Tab/Session tree    |
|  MeshTermTransport --> claude-mesh Transport ABC   |
+---------------------------------------------------+
```

---

## Module Map (8 files)

```
src/meshterm/
    __init__.py       Public API, run_until_complete()
    connection.py     Unix socket client, JSON-RPC 2.0 framing
    server.py         PTY management, VT parser, RPC handler dispatch
    session.py        Client-side session proxy, ScreenContents dataclass
    app.py            Application root, async_get_app() factory
    window.py         Window management (client-side proxy)
    tab.py            Tab management (client-side proxy)
    transport.py      claude-mesh Transport ABC integration
```

### Dependency graph

```
__init__.py
  imports: connection, app, session, window, tab, server

app.py
  imports: window (for MeshTermWindow construction)
  calls: connection.async_call("app.get_state")

window.py
  imports: tab (for MeshTermTab construction)
  calls: connection.async_call("window.*")

tab.py
  imports: session (for MeshTermSession construction)
  calls: connection.async_call("tab.*")

session.py
  imports: connection (type only)
  calls: connection.async_call("session.*")

connection.py
  imports: nothing from meshterm (leaf module)
  provides: frame encoding, socket path resolution, Connection class

server.py
  imports: connection (_encode_frame, _read_frame, path helpers)
  owns: SessionState dataclass, all RPC handler implementations

transport.py
  imports: connection, app
  imports: claude_mesh.transport.base (external)
  implements: Transport ABC (send_text, send_key, read_screen, discover)
```

---

## IPC Protocol

**Transport:** Unix domain socket at `$XDG_RUNTIME_DIR/meshterm/ipc.sock` (fallback: `/tmp/meshterm-$UID/ipc.sock`). Override with `$MESHTERM_SOCKET`.

**Framing:** Length-prefixed binary frames.
```
[4-byte big-endian uint32: payload length][UTF-8 JSON payload]
```
Maximum frame size: 16 MiB.

**Protocol:** JSON-RPC 2.0. Requests have an `id` field; notifications omit it. Server pushes events as notifications to all connected clients.

**Authentication:** Cookie-based. Server writes a random 64-hex-char token to `~/.config/meshterm/auth_cookie` (mode 0600). Clients must send this cookie in the handshake frame. Disable with `MESHTERM_NO_AUTH=1` for development.

**Handshake sequence:**
```
Client --> Server:  {"jsonrpc":"2.0","method":"handshake","params":{"client_version":"0.1.0","cookie":"..."},"id":0}
Server --> Client:  {"jsonrpc":"2.0","result":{"status":"connected","server_version":"0.1.0"},"id":0}
```

After handshake, the client sends RPC requests and the server responds. The client runs a background `_listen_loop` task to dispatch responses to pending futures and route server notifications to subscription queues.

---

## PTY Management

The server creates terminal sessions using `os.openpty()`, which returns a `(master_fd, slave_fd)` pair. The child shell process gets the slave side. The server holds the master fd and:

1. **Writes** to master_fd when `session.send_text` or `session.send_key` RPC is called.
2. **Reads** from master_fd (via asyncio fd watcher) and feeds output to `pyte.Stream`.
3. **pyte.Screen** maintains the rendered character grid (rows x cols) with cursor position.
4. **get_screen_contents** serializes `screen.display` into a list of line dicts.
5. **Resize** uses `ioctl(TIOCSWINSZ)` on the master fd and calls `screen.resize()`.
6. **Close** sends SIGHUP (or SIGKILL if force) to the child PID and closes the fd.

The `SessionState` dataclass holds per-session state:
```python
@dataclass
class SessionState:
    session_id: str
    name: str
    profile: str
    pid: int            # child shell PID
    master_fd: int      # PTY master file descriptor
    tty: str            # /dev/pts/N path
    rows: int = 24
    cols: int = 80
    screen: Any = None  # pyte.Screen instance
    stream: Any = None  # pyte.Stream instance
    user_vars: dict[str, str]
```

---

## Implementation Status

### RPC Handlers (server.py)

| Method | Status | Notes |
|--------|--------|-------|
| `handshake` | REAL | Cookie auth, version exchange |
| `app.get_state` | REAL | Returns PID, version, window list |
| `app.get_variable` | REAL | pid, version, theme |
| `session.send_text` | REAL | `os.write(master_fd, text)` |
| `session.send_key` | REAL | Full key map: arrows, F1-F12, ctrl+letter, modifiers |
| `session.get_screen_contents` | REAL | Reads from `pyte.Screen.display`, returns cursor position |
| `session.get_scrollback` | STUB | Returns empty list. Needs `pyte.HistoryScreen` integration |
| `session.set_name` | REAL | Updates `SessionState.name` |
| `session.activate` | STUB | No GUI layer yet |
| `session.close` | REAL | SIGHUP/SIGKILL + fd cleanup + broadcast event |
| `session.split_pane` | STUB | Returns empty dict. Needs PTY creation + layout manager |
| `session.get_variable` | REAL | Built-in vars (name, pid, tty, cols, rows) + user vars |
| `session.set_variable` | REAL | Stores in `SessionState.user_vars` |
| `session.set_grid_size` | REAL | `ioctl(TIOCSWINSZ)` + `screen.resize()` |
| `window.create` | STUB | Returns empty dict |
| `window.activate` | STUB | No-op |
| `window.close` | STUB | No-op |
| `window.create_tab` | STUB | Returns empty dict |
| `window.set_title` | STUB | No-op |
| `window.set_position` | STUB | No-op |
| `window.set_size` | STUB | No-op |
| `window.set_fullscreen` | STUB | No-op |
| `window.set_tabs` | STUB | No-op |
| `tab.activate` | STUB | No-op |
| `tab.close` | STUB | No-op |
| `tab.set_title` | STUB | No-op |
| `tab.split_pane` | STUB | Returns empty dict |
| `tab.select_pane_in_direction` | STUB | No-op |
| `subscribe` | REAL | Returns subscription confirmation |

**Summary:** 12 REAL handlers, 14 STUB handlers. Core session I/O works. Window/tab management and GUI integration are stubs.

### Client-Side Proxies

| Module | Status | Notes |
|--------|--------|-------|
| `Connection` | REAL | Full async JSON-RPC client with listen loop, subscriptions, error handling |
| `MeshTermApp` | REAL | Builds Window/Tab/Session tree from server state, supports refresh |
| `MeshTermWindow` | REAL (client) | All methods issue RPC calls. Server handlers are stubs |
| `MeshTermTab` | REAL (client) | All methods issue RPC calls. Server handlers are stubs |
| `MeshTermSession` | REAL | Full API: send_text, send_key, screen reading, variables, resize, close |
| `MeshTermTransport` | REAL | Implements all 4 Transport ABC primitives |

---

## claude-mesh Integration

`transport.py` implements the `claude_mesh.transport.base.Transport` ABC, making meshterm a drop-in transport for claude-mesh on Linux.

**Transport primitives implemented:**

| Method | Implementation |
|--------|---------------|
| `send_text(target, text)` | Finds session by name, calls `session.send_text` RPC |
| `send_key(target, key)` | Maps claude-mesh constants (CR, CTRL_C, ESC) to meshterm key names |
| `read_screen(target, lines)` | Calls `session.get_screen_contents` RPC, joins lines |
| `discover()` | Enumerates all sessions across all windows/tabs |
| `close()` | Disconnects from IPC server |

**Session discovery strategy** (same as ITerm2Transport):
1. Check `session_map` dict for known UUID
2. Search all sessions by name containing the target codename

**Intended priority order in claude-mesh:**
```
Linux:
  1. MeshTermTransport  (local, direct Unix socket, zero network overhead)
  2. SSH + iTerm2 API   (remote Mac control)
  3. Redis Streams      (Linux<->Linux fallback)
```

---

## What Changed from the Original Plan

The original ARCHITECTURE.md (v0.1.0) described a tmux + libtmux design with modules like `screen.py`, `keys.py`, `events.py`, `discovery.py`, and a `compat/iterm2.py` compatibility layer.

**What actually got built:** A custom PTY server instead. The current codebase:

- Manages PTY file descriptors directly via `os.openpty()` -- no tmux dependency
- Runs a pyte VT100 parser for screen state -- no `tmux capture-pane`
- Uses JSON-RPC 2.0 over Unix domain socket -- not tmux control mode
- The iTerm2-compatible API is the primary API, not a compatibility layer
- Connection/server architecture supports multiple concurrent clients
- Cookie-based authentication for security

**Why this is better than the tmux plan:**
- No external process dependency (tmux server)
- Direct PTY control gives lower latency and finer-grained access
- pyte VT parser gives accurate screen state including cursor position and alternate screen detection
- JSON-RPC is a cleaner protocol than parsing tmux control mode output

**What it costs:**
- Window/tab management must be built from scratch (14 stub handlers)
- No free multiplexing -- must implement session lifecycle ourselves
- GUI layer (if needed) requires separate work

**Decision validated by team.** More powerful but more work. The core session I/O path is complete and proven.

---

## Dependencies (actual)

```toml
[project]
dependencies = [
    "pyte>=0.8.0",          # VT100 terminal parser (pure Python)
]

# NOTE: libtmux and pydantic are listed in pyproject.toml but NOT used
# by any current source file. They are holdovers from the original plan.
# Clean up in next release.

[project.optional-dependencies]
mesh = ["claude-mesh"]      # For MeshTermTransport
cli = ["click>=8.0", "rich>=13.0"]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "ruff>=0.4.0"]
```

---

## File Sizes (for orientation)

| File | Lines | Role |
|------|-------|------|
| `server.py` | 609 | Largest. All RPC handlers live here |
| `session.py` | 437 | Client proxy + ScreenContents/ScreenLine dataclasses |
| `connection.py` | 360 | Frame encoding, socket resolution, async Connection |
| `window.py` | 217 | Client proxy for window operations |
| `transport.py` | 210 | claude-mesh Transport integration |
| `tab.py` | 150 | Client proxy for tab operations |
| `app.py` | 130 | Application root + async_get_app factory |
| `__init__.py` | 62 | Public re-exports + run_until_complete |
