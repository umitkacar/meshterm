# Python API Guide

> The modern, recommended approach for iTerm2 automation.

---

## Overview

The Python API provides full programmatic control of iTerm2 with:
- **30 specialized modules** (4 new: Binding, FilePanel, Triggers, PolyModalAlert)
- Async/await support (Python 3.14 compatible)
- Event subscription with 5 new trigger event types
- WebSocket communication
- Active development (v2.14, Feb 2026)

---

## Setup

### 1. Enable Python API

```
iTerm2 → Settings (⌘,) → General → Magic → ☑ Enable Python API
```

### 2. Install Module

```bash
# Using pip
pip install iterm2

# Using uv (recommended)
uv pip install iterm2

# Verify
python -c "import iterm2; print('OK')"
```

### 3. First Script

```python
#!/usr/bin/env python3
import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_window
    if window:
        session = window.current_tab.current_session
        await session.async_send_text("echo 'Hello from Python API!'\n")
    else:
        print("No window found")

iterm2.run_until_complete(main)
```

---

## Core Concepts

### Connection

All operations require a connection to iTerm2:

```python
import iterm2

async def main(connection):
    # connection is provided automatically
    pass

# This establishes the connection
iterm2.run_until_complete(main)
```

### Async/Await

All API methods are async:

```python
async def main(connection):
    # Get app reference
    app = await iterm2.async_get_app(connection)

    # Create window
    window = await iterm2.Window.async_create(connection)

    # Get session
    session = window.current_tab.current_session

    # Send text
    await session.async_send_text("ls -la\n")
```

### Object Model

```
App
 └── Windows[]
      └── Tabs[]
           └── Sessions[]
```

---

## Common Operations

### Window Management

```python
async def window_operations(connection):
    app = await iterm2.async_get_app(connection)

    # Create new window
    window = await iterm2.Window.async_create(connection)

    # Create with specific profile
    window = await iterm2.Window.async_create(
        connection,
        profile="Development"
    )

    # Get current window
    current = app.current_window

    # List all windows
    for window in app.windows:
        print(f"Window ID: {window.window_id}")

    # Activate window
    await window.async_activate()

    # Close window
    await window.async_close()
```

### Tab Operations

```python
async def tab_operations(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_window

    # Create new tab
    tab = await window.async_create_tab()

    # Create with profile
    tab = await window.async_create_tab(profile="SSH")

    # Get current tab
    current_tab = window.current_tab

    # Select tab
    await tab.async_activate()

    # Close tab
    await tab.async_close()
```

### Session Operations

```python
async def session_operations(connection):
    app = await iterm2.async_get_app(connection)
    session = app.current_window.current_tab.current_session

    # Send text/command
    await session.async_send_text("echo 'Hello'\n")

    # Set session name
    await session.async_set_name("My Terminal")

    # Get session variable
    path = await session.async_get_variable("path")
    print(f"Current directory: {path}")

    # Split pane
    new_session = await session.async_split_pane(vertical=True)

    # Split with profile
    new_session = await session.async_split_pane(
        vertical=False,
        profile="Logs"
    )
```

### Profile Management

```python
async def profile_operations(connection):
    # Get all profiles
    profiles = await iterm2.PartialProfile.async_query(connection)

    for profile in profiles:
        print(f"Profile: {profile.name}")

    # Get default profile
    default = await iterm2.Profile.async_get_default(connection)

    # Create new profile
    new_profile = iterm2.LocalWriteOnlyProfile()
    new_profile.set_name("Custom Profile")
    new_profile.set_badge_text("\\(user)@\\(hostname)")
    await new_profile.async_create(connection)
```

---

## Advanced Features

### Event Subscription

```python
async def monitor_sessions(connection):
    app = await iterm2.async_get_app(connection)

    async with iterm2.NewSessionMonitor(connection) as mon:
        while True:
            session_id = await mon.async_get()
            print(f"New session created: {session_id}")

iterm2.run_until_complete(monitor_sessions)
```

### Variable Monitoring

```python
async def watch_directory(connection):
    async with iterm2.VariableMonitor(
        connection,
        iterm2.VariableScopes.SESSION,
        "path",
        None  # All sessions
    ) as mon:
        while True:
            change = await mon.async_get()
            print(f"Directory changed: {change.new_value}")
```

### Custom Status Bar Component

```python
async def status_bar_component(connection):
    component = iterm2.StatusBarComponent(
        short_description="My Component",
        detailed_description="Shows custom info",
        knobs=[],
        exemplar="Example",
        update_cadence=None,
        identifier="com.example.mycomponent"
    )

    @iterm2.StatusBarRPC
    async def my_component_coro(knobs):
        return "Hello from Python!"

    await component.async_register(
        connection,
        my_component_coro
    )
```

### Triggers via Python

```python
async def setup_triggers(connection):
    profiles = await iterm2.PartialProfile.async_query(connection)

    for partial in profiles:
        profile = await partial.async_get_full_profile()

        # Add error highlighting trigger
        triggers = profile.triggers or []
        triggers.append({
            "regex": "(?i)error|fail|exception",
            "action": "HighlightTextTrigger",
            "parameter": {
                "color": {"Red": 1.0, "Green": 0.0, "Blue": 0.0}
            }
        })

        # Update profile
        change = iterm2.LocalWriteOnlyProfile()
        change.set_triggers(triggers)
        await profile.async_set_local_write_only_profile(change)
```

---

## Complete Example: Development Layout

```python
#!/usr/bin/env python3
"""Create a development environment with multiple panes."""
import iterm2

async def create_dev_layout(connection):
    app = await iterm2.async_get_app(connection)

    # Create new window
    window = await iterm2.Window.async_create(connection)
    tab = window.current_tab

    # Main editor pane (left)
    editor = tab.current_session
    await editor.async_set_name("Editor")

    # Split for terminal (right)
    terminal = await editor.async_split_pane(vertical=True)
    await terminal.async_set_name("Terminal")

    # Split terminal for logs (bottom right)
    logs = await terminal.async_split_pane(vertical=False)
    await logs.async_set_name("Logs")

    # Run commands
    await editor.async_send_text("vim .\n")
    await terminal.async_send_text("npm run dev\n")
    await logs.async_send_text("tail -f logs/*.log\n")

    print("Development layout created!")

if __name__ == "__main__":
    iterm2.run_until_complete(create_dev_layout)
```

---

## Error Handling

```python
async def safe_operations(connection):
    try:
        app = await iterm2.async_get_app(connection)
        window = app.current_window

        if window is None:
            print("No window available")
            return

        session = window.current_tab.current_session
        await session.async_send_text("ls\n")

    except iterm2.AppNotRunningError:
        print("iTerm2 is not running")
    except iterm2.RPCError as e:
        print(f"RPC Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
```

---

## Scripts Directory

Place scripts in:

```
~/Library/Application Support/iTerm2/Scripts/
```

For auto-launch:

```
~/Library/Application Support/iTerm2/Scripts/AutoLaunch/
```

---

---

## What's New in v2.14

| Feature | Version | Description |
|---------|---------|-------------|
| **PolyModalAlert** | 2.12 | Rich dialogs with checkboxes, comboboxes, text fields |
| **Binding module** | 2.10 | Programmatic key binding management (64+ actions) |
| **FilePanel module** | 2.10 | Native Open/Save file dialogs |
| **Triggers module** | 2.10 | 26 trigger types with regex matching |
| **async_list_prompts()** | 2.12 | Retrieve prompt history by session |
| **4 new trigger types** | 2.10-2.13 | Fold, SGR, BufferInput, SetNamedMark |
| **Python 3.14 compat** | 2.14 | Event loop fixes for latest Python |
| **URL loading** | 2.14 | Browser session URL loading API |
| **Type safety** | 2.14 | mypy type checking, ABC delegates |

---

## Related Documentation

- [Python API Reference](./python-api-reference.md) - All 30 modules
- [Migration Guide](./migration-guide.md) - From AppleScript
- [Workflow Overview](./workflow-overview.md) - Architecture
