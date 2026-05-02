# Python API Solutions

> Modern solutions using iTerm2 Python API - No more AppleScript issues!

---

## Why Python API?

| AppleScript Issue | Python API Status |
|-------------------|-------------------|
| Tab Title Trap | ✅ Eliminated |
| Apostrophe Issues | ✅ Eliminated |
| Quote Hell | ✅ Eliminated |
| Race Conditions | ✅ Better handling |
| Error Handling | ✅ Full try/except |
| Async Operations | ✅ Native support |

---

## RAMAS Multi-Window Launcher (Migrated)

### Original AppleScript (Problematic)

```applescript
-- Had issues with:
-- - Quote escaping in bash
-- - Tab title trap
-- - Race conditions
tell application "iTerm2"
    set win1 to (create window with default profile)
    -- ... problematic code
end tell
```

### Python API Solution (Clean)

```python
#!/usr/bin/env python3
"""RAMAS Multi-Window Launcher - Python API Version"""
import iterm2
import asyncio

WORKERS = [
    {"name": "[GREEN] WORKER-1", "color": "green", "command": "echo 'Worker 1'"},
    {"name": "[BLUE] WORKER-2", "color": "blue", "command": "echo 'Worker 2'"},
    {"name": "[YELLOW] WORKER-3", "color": "yellow", "command": "echo 'Worker 3'"},
]

async def create_worker_windows(connection):
    """Create multiple worker windows with proper naming."""
    windows = []

    for worker in WORKERS:
        # Create window
        window = await iterm2.Window.async_create(connection)
        session = window.current_tab.current_session

        # Set session name (propagates to tab)
        await session.async_set_name(worker["name"])

        # Run command
        if worker["command"]:
            await session.async_send_text(f"{worker['command']}\n")

        windows.append(window)

        # Small delay for stability
        await asyncio.sleep(0.3)

    return windows

if __name__ == "__main__":
    iterm2.run_until_complete(create_worker_windows)
```

---

## Session Naming (Tab Title Trap Fixed)

```python
async def name_session(connection):
    app = await iterm2.async_get_app(connection)
    session = app.current_window.current_tab.current_session

    # This just works - no Tab Title Trap!
    await session.async_set_name("[GREEN] My Worker")
```

---

## Text with Special Characters (Quote Hell Fixed)

```python
async def send_complex_command(connection):
    app = await iterm2.async_get_app(connection)
    session = app.current_window.current_tab.current_session

    # All quotes handled naturally
    command = '''echo "Hello 'World'" && echo "It's working!"'''
    await session.async_send_text(f"{command}\n")
```

---

## Error Handling (Proper Exceptions)

```python
async def safe_operations(connection):
    try:
        app = await iterm2.async_get_app(connection)
        window = app.current_window

        if window is None:
            print("No window available, creating one...")
            window = await iterm2.Window.async_create(connection)

        session = window.current_tab.current_session
        await session.async_send_text("ls -la\n")

    except iterm2.AppNotRunningError:
        print("iTerm2 is not running")
    except iterm2.RPCError as e:
        print(f"RPC Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
```

---

## Async Window Creation (No Race Conditions)

```python
async def create_layout(connection):
    """Python API handles timing internally."""
    # Window 1
    win1 = await iterm2.Window.async_create(connection)
    session1 = win1.current_tab.current_session
    await session1.async_set_name("Editor")

    # Window 2 - No delay needed, async handles it
    win2 = await iterm2.Window.async_create(connection)
    session2 = win2.current_tab.current_session
    await session2.async_set_name("Terminal")

    # Commands run after windows are ready
    await session1.async_send_text("vim .\n")
    await session2.async_send_text("npm run dev\n")
```

---

## Bash Integration (Clean)

```bash
#!/bin/bash
# No heredoc nightmares, no quote escaping

python3 << 'EOF'
import iterm2

async def main(connection):
    window = await iterm2.Window.async_create(connection)
    session = window.current_tab.current_session
    await session.async_set_name("From Bash")
    await session.async_send_text("echo 'Clean and simple!'\n")

iterm2.run_until_complete(main)
EOF
```

---

## Helper Library

```python
# iterm2_helpers.py
import iterm2

async def create_named_window(connection, name, command=None):
    """Create window with name and optional command."""
    window = await iterm2.Window.async_create(connection)
    session = window.current_tab.current_session
    await session.async_set_name(name)

    if command:
        await session.async_send_text(f"{command}\n")

    return window, session

async def create_split_layout(connection, panes):
    """Create window with split panes."""
    window = await iterm2.Window.async_create(connection)
    session = window.current_tab.current_session

    for i, pane in enumerate(panes):
        if i > 0:
            vertical = pane.get("split", "vertical") == "vertical"
            session = await session.async_split_pane(vertical=vertical)

        await session.async_set_name(pane["name"])

        if pane.get("command"):
            await session.async_send_text(f"{pane['command']}\n")

    return window
```

---

## Related Documentation

- [Current Issues](./current-issues.md)
- [Python API Guide](../03-scripting/python-api-guide.md)
- [Migration Guide](../03-scripting/migration-guide.md)
