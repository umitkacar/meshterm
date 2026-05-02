# meshterm API Mapping: iTerm2 → libtmux → meshterm

### How every iTerm2 Python API method maps to libtmux and meshterm

**Date:** 2026-03-30

---

## 7 Required Feature Mapping

| # | Feature | iTerm2 API | libtmux API | meshterm API | Gap |
|---|---------|-----------|-------------|-------------|-----|
| 1 | Text injection | `session.async_send_text(text)` | `pane.send_keys(text, enter=False)` | `session.send(text)` | None |
| 2 | Key injection | `session.async_send_text("\r")` | `pane.send_keys("Enter")` / `pane.send_keys("Escape")` | `session.send_key(Key.ENTER)` | None |
| 3 | Screen reading | `session.async_get_screen_contents()` | `pane.capture_pane()` | `session.read_screen()` | libtmux returns list[str], no cursor/metadata |
| 4 | Session enum | `app.windows[].tabs[].sessions` | `server.list_sessions()` + `session.list_windows()` + `window.list_panes()` | `app.sessions` | None |
| 5 | Session UUID | `session.session_id` (UUID v4) | `pane.pane_id` (%0, %1...) | `session.uuid` (generated, Redis-backed) | libtmux uses %N, not UUID |
| 6 | Session metadata | `session.async_get_variable("name"/"jobName")` | `pane.pane_current_command` / `pane.pane_title` | `session.metadata` | Partial |
| 7 | Headless IPC | WebSocket over Unix socket | libtmux talks to tmux server via socket | Same as libtmux | None |

---

## Detailed Method Mapping

### Connection / App Level

| iTerm2 | libtmux | meshterm |
|--------|---------|---------|
| `iterm2.Connection.async_create()` | `libtmux.Server()` | `meshterm.connect()` |
| `iterm2.async_get_app(connection)` | `server` (already the app) | `meshterm.app()` |
| `app.windows` | `server.sessions` | `app.sessions` |
| `app.current_window` | `server.attached_sessions[0]` | `app.current_session` |
| `iterm2.run_until_complete(func)` | N/A (sync) | `meshterm.run(func)` (async wrapper) |

### Session (iTerm2 Session = libtmux Pane)

| iTerm2 | libtmux | meshterm | Notes |
|--------|---------|---------|-------|
| `session.async_send_text(text)` | `pane.send_keys(text, enter=False)` | `session.send(text)` | libtmux literal=True for exact text |
| `session.async_send_text("\r")` | `pane.send_keys("Enter")` | `session.send_key(Key.ENTER)` | CR not LF! |
| `session.async_send_text("\x1b")` | `pane.send_keys("Escape")` | `session.send_key(Key.ESC)` | |
| `session.async_send_text("\x03")` | `pane.send_keys("C-c")` | `session.send_key(Key.CTRL_C)` | |
| `session.async_get_screen_contents()` | `pane.capture_pane()` | `session.read_screen()` | returns ScreenContents |
| `contents.line(i).string` | `capture_pane()[i]` | `screen.lines[i]` | |
| `contents.number_of_lines` | `len(capture_pane())` | `screen.num_lines` | |
| `contents.cursor_coord` | `pane.cursor_x/y` (via display_message) | `screen.cursor` | libtmux needs workaround |
| `session.session_id` | `pane.pane_id` (%N format) | `session.uuid` | meshterm generates UUID, maps to pane_id |
| `session.async_set_name(name)` | `pane.set_title(name)` | `session.set_name(name)` | |
| `session.async_get_variable("name")` | `pane.pane_title` | `session.name` | |
| `session.async_get_variable("jobName")` | `pane.pane_current_command` | `session.current_command` | |
| `session.async_get_variable("pid")` | `pane.pane_pid` | `session.pid` | |
| `session.async_get_variable("tty")` | `pane.pane_tty` | `session.tty` | |
| `session.async_get_variable("path")` | `pane.pane_current_path` | `session.cwd` | |

### Window Management

| iTerm2 | libtmux | meshterm | Notes |
|--------|---------|---------|-------|
| `Window.async_create(conn)` | `server.new_session()` | `app.create_session(name)` | tmux session = iTerm2 window |
| `window.tabs` | `session.windows` | `session.windows` | |
| `tab.sessions` | `window.panes` | `window.panes` | |
| `tab.current_session` | `window.active_pane` | `window.active_pane` | libtmux property |
| `window.async_activate()` | `session.attach()` | `session.focus()` | |
| `window.async_close()` | `session.kill()` | `session.close()` | |

### Screen Reading (ScreenContents equivalent)

```python
# iTerm2:
contents = await session.async_get_screen_contents()
for i in range(contents.number_of_lines):
    line = contents.line(i).string.replace('\x00', '')

# libtmux:
lines = pane.capture_pane()  # returns list[str]

# meshterm (proposed):
screen = session.read_screen()
screen.lines         # list[str]
screen.num_lines     # int
screen.cursor        # (x, y) tuple
screen.scrollback    # int (lines above visible)
screen.raw           # full text with newlines
```

---

## meshterm Extensions (not present in libtmux)

### 1. UUID Session Tracking
```python
# libtmux: pane.pane_id = "%0" (not a UUID)
# meshterm: session.uuid = "26c304f7-..." (Redis-backed)
session = app.get_session_by_uuid("26c304f7-...")
```

### 2. wait_for(pattern)
```python
# libtmux: not available (requires manual polling)
# meshterm:
output = await session.wait_for(r"\$\s*$", timeout=30)  # wait for shell prompt
output = await session.wait_for("Build succeeded", timeout=120)
```

### 3. Screen Diffing
```python
# libtmux: not available
# meshterm:
diff = session.screen_diff()  # what changed since last read
diff.added_lines    # new lines
diff.changed_lines  # modified lines
diff.is_idle        # no change = idle
```

### 4. claude-mesh Transport
```python
# meshterm as claude-mesh transport:
from claude_mesh.transport import get_transport
t = get_transport("meshterm")  # uses local libtmux, no SSH hop
await t.send("titan", "task done")  # direct, <1ms
```

---

## libtmux v0.55.0 Important Notes

- `pane.send_keys(text, enter=True)` — defaults to sending Enter; meshterm uses `enter=False` by default
- `pane.capture_pane()` — `-a` flag exposes alternate screen buffer (critical for Claude Code)
- `pane.pane_current_command` — foreground process name (ssh, python3, claude)
- `server.is_alive()` — check whether tmux server is running
- `pane.display_message("#{cursor_x} #{cursor_y}")` — cursor position workaround

---

## Hierarchy Mapping

```
iTerm2:                    libtmux:                   meshterm:
App                        Server                     App
 └── Window                 └── Session                └── Session (UUID)
      └── Tab                    └── Window                 └── Window
           └── Session (UUID)         └── Pane (%%N)              └── Pane
```

NOT: iTerm2'de Session = tek terminal. libtmux'ta Pane = tek terminal.
meshterm bunu soyutlayacak — kullanici "session" der, arkada pane yonetilir.
