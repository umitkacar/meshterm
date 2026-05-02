# Migration Guide: AppleScript to Python API

> Step-by-step guide to migrate your iTerm2 automation from AppleScript to Python API.

---

## Why Migrate?

| Aspect | AppleScript | Python API |
|--------|-------------|------------|
| **Status** | ⚠️ Deprecated | ✅ Active |
| **New Features** | None | Regular updates |
| **Async** | ❌ | ✅ Native |
| **Events** | ❌ | ✅ Full support |
| **Error Handling** | Basic | Comprehensive |
| **Documentation** | Static | Growing |

---

## Migration Checklist

- [ ] Enable Python API in iTerm2
- [ ] Install `iterm2` Python module
- [ ] Test basic connection
- [ ] Convert scripts one by one
- [ ] Test converted scripts
- [ ] Update any calling scripts/automation

---

## Concept Mapping

### Basic Structure

```
AppleScript                        Python API
───────────                        ──────────

tell application "iTerm2"     →    import iterm2
    ...                            async def main(connection):
end tell                               ...
                                   iterm2.run_until_complete(main)
```

### Object Access

```
AppleScript                        Python API
───────────                        ──────────

current window               →     app.current_window
current tab of current       →     window.current_tab
    window
current session of current   →     tab.current_session
    tab of current window
```

---

## Command Translations

### Window Operations

| AppleScript | Python API |
|-------------|------------|
| `create window with default profile` | `await iterm2.Window.async_create(connection)` |
| `create window with profile "Name"` | `await iterm2.Window.async_create(connection, profile="Name")` |
| `close` | `await window.async_close()` |
| `set bounds to {x1,y1,x2,y2}` | `await window.async_set_frame(iterm2.Frame(...))` |

### Tab Operations

| AppleScript | Python API |
|-------------|------------|
| `create tab with default profile` | `await window.async_create_tab()` |
| `create tab with profile "Name"` | `await window.async_create_tab(profile="Name")` |

### Session Operations

| AppleScript | Python API |
|-------------|------------|
| `write text "command"` | `await session.async_send_text("command\n")` |
| `set name to "Name"` | `await session.async_set_name("Name")` |
| `split vertically with default profile` | `await session.async_split_pane(vertical=True)` |
| `split horizontally with profile "Name"` | `await session.async_split_pane(vertical=False, profile="Name")` |

---

## Example Migrations

### Example 1: Simple Command

**AppleScript:**
```applescript
tell application "iTerm2"
    tell current session of current tab of current window
        write text "ls -la"
    end tell
end tell
```

**Python API:**
```python
import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    session = app.current_window.current_tab.current_session
    await session.async_send_text("ls -la\n")

iterm2.run_until_complete(main)
```

### Example 2: Create Window with Name

**AppleScript:**
```applescript
tell application "iTerm2"
    create window with default profile
    tell current session of current tab of current window
        set name to "Development"
        write text "cd ~/projects"
    end tell
end tell
```

**Python API:**
```python
import iterm2

async def main(connection):
    window = await iterm2.Window.async_create(connection)
    session = window.current_tab.current_session
    await session.async_set_name("Development")
    await session.async_send_text("cd ~/projects\n")

iterm2.run_until_complete(main)
```

### Example 3: Split Panes Layout

**AppleScript:**
```applescript
tell application "iTerm2"
    tell current session of current tab of current window
        set name to "Left"
        split vertically with default profile
    end tell
    tell second session of current tab of current window
        set name to "Right"
    end tell
end tell
```

**Python API:**
```python
import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    tab = app.current_window.current_tab

    left = tab.current_session
    await left.async_set_name("Left")

    right = await left.async_split_pane(vertical=True)
    await right.async_set_name("Right")

iterm2.run_until_complete(main)
```

### Example 4: Multi-Window Setup

**AppleScript:**
```applescript
tell application "iTerm2"
    set win1 to (create window with default profile)
    tell win1
        set bounds to {0, 0, 960, 1080}
        tell current session of current tab
            set name to "Editor"
            write text "vim ."
        end tell
    end tell

    set win2 to (create window with default profile)
    tell win2
        set bounds to {960, 0, 1920, 1080}
        tell current session of current tab
            set name to "Terminal"
        end tell
    end tell
end tell
```

**Python API:**
```python
import iterm2

async def main(connection):
    # Window 1
    win1 = await iterm2.Window.async_create(connection)
    session1 = win1.current_tab.current_session
    await session1.async_set_name("Editor")
    await session1.async_send_text("vim .\n")

    # Window 2
    win2 = await iterm2.Window.async_create(connection)
    session2 = win2.current_tab.current_session
    await session2.async_set_name("Terminal")

    # Note: Window positioning requires Frame API
    # await win1.async_set_frame(iterm2.Frame(0, 0, 960, 1080))

iterm2.run_until_complete(main)
```

---

## Bash Integration Migration

### Before (osascript)

```bash
#!/bin/bash
osascript << 'EOF'
tell application "iTerm2"
    create window with default profile
    tell current session of current tab of current window
        write text "echo 'Hello'"
    end tell
end tell
EOF
```

### After (Python)

```bash
#!/bin/bash
python3 << 'EOF'
import iterm2

async def main(connection):
    window = await iterm2.Window.async_create(connection)
    session = window.current_tab.current_session
    await session.async_send_text("echo 'Hello'\n")

iterm2.run_until_complete(main)
EOF
```

Or better, create a Python script:

```python
#!/usr/bin/env python3
# ~/scripts/create_window.py
import iterm2
import sys

async def main(connection):
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    window = await iterm2.Window.async_create(connection)
    session = window.current_tab.current_session
    if command:
        await session.async_send_text(f"{command}\n")

iterm2.run_until_complete(main)
```

```bash
# Usage
python3 ~/scripts/create_window.py "ls -la"
```

---

## Error Handling Migration

### AppleScript Error Handling

```applescript
try
    tell application "iTerm2"
        create window with profile "NonExistent"
    end tell
on error errMsg number errNum
    display dialog "Error: " & errMsg
end try
```

### Python Error Handling

```python
import iterm2

async def main(connection):
    try:
        app = await iterm2.async_get_app(connection)
        window = await iterm2.Window.async_create(
            connection,
            profile="NonExistent"
        )
    except iterm2.ProfileNotFoundError:
        print("Profile not found")
    except iterm2.AppNotRunningError:
        print("iTerm2 is not running")
    except Exception as e:
        print(f"Error: {e}")

iterm2.run_until_complete(main)
```

---

## New Capabilities After Migration

### Event Monitoring (Not possible in AppleScript)

```python
async def monitor_new_sessions(connection):
    async with iterm2.NewSessionMonitor(connection) as mon:
        while True:
            session_id = await mon.async_get()
            print(f"New session: {session_id}")
```

### Variable Watching

```python
async def watch_directory(connection):
    async with iterm2.VariableMonitor(
        connection,
        iterm2.VariableScopes.SESSION,
        "path",
        None
    ) as mon:
        while True:
            change = await mon.async_get()
            print(f"Directory: {change.new_value}")
```

### Custom Status Bar

```python
component = iterm2.StatusBarComponent(
    short_description="My Widget",
    detailed_description="Custom component",
    knobs=[],
    exemplar="Widget",
    update_cadence=5,
    identifier="com.example.widget"
)

@iterm2.StatusBarRPC
async def widget_coro(knobs):
    return "Hello from Python!"

await component.async_register(connection, widget_coro)
```

---

## Related Documentation

- [Python API Guide](./python-api-guide.md)
- [Python API Reference](./python-api-reference.md)
- [Workflow Overview](./workflow-overview.md)
