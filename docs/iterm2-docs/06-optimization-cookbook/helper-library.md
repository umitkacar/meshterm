# Helper Library

> Reusable code for iTerm2 automation.

---

## Python Helper Module

```python
#!/usr/bin/env python3
"""iterm2_helpers.py - Reusable iTerm2 automation utilities."""
import iterm2
import asyncio
from typing import Optional, List, Dict, Any

# ============================================================
# Window Operations
# ============================================================

async def create_window(
    connection,
    name: Optional[str] = None,
    command: Optional[str] = None,
    profile: Optional[str] = None
) -> tuple:
    """Create window with optional name and command."""
    if profile:
        window = await iterm2.Window.async_create(connection, profile=profile)
    else:
        window = await iterm2.Window.async_create(connection)

    session = window.current_tab.current_session

    if name:
        await session.async_set_name(name)

    if command:
        await session.async_send_text(f"{command}\n")

    return window, session


async def create_split_layout(
    connection,
    panes: List[Dict[str, Any]]
) -> tuple:
    """
    Create window with split panes.

    panes = [
        {"name": "Editor", "command": "vim ."},
        {"name": "Terminal", "split": "vertical"},
        {"name": "Logs", "command": "tail -f log", "split": "horizontal"},
    ]
    """
    window = await iterm2.Window.async_create(connection)
    tab = window.current_tab
    sessions = []
    session = tab.current_session

    for i, pane in enumerate(panes):
        if i > 0:
            vertical = pane.get("split", "vertical") == "vertical"
            session = await session.async_split_pane(vertical=vertical)

        await session.async_set_name(pane.get("name", f"Pane {i+1}"))

        if pane.get("command"):
            await session.async_send_text(f"{pane['command']}\n")

        sessions.append(session)

    return window, sessions


# ============================================================
# Session Operations
# ============================================================

async def send_to_current(connection, text: str):
    """Send text to current session."""
    app = await iterm2.async_get_app(connection)
    if app.current_window:
        session = app.current_window.current_tab.current_session
        await session.async_send_text(text)


async def send_to_all_sessions(connection, text: str):
    """Send text to all sessions in all windows."""
    app = await iterm2.async_get_app(connection)
    for window in app.windows:
        for tab in window.tabs:
            for session in tab.sessions:
                await session.async_send_text(text)


# ============================================================
# Layout Management
# ============================================================

async def create_dev_layout(
    connection,
    project_path: str,
    editor_cmd: str = "vim .",
    server_cmd: Optional[str] = None
):
    """Create standard development layout."""
    panes = [
        {"name": "Editor", "command": f"cd {project_path} && {editor_cmd}"},
        {"name": "Terminal", "command": f"cd {project_path}", "split": "vertical"},
    ]

    if server_cmd:
        panes.append({
            "name": "Server",
            "command": f"cd {project_path} && {server_cmd}",
            "split": "horizontal"
        })

    return await create_split_layout(connection, panes)


async def create_ssh_layout(
    connection,
    servers: List[Dict[str, str]]
):
    """
    Create layout for multiple SSH connections.

    servers = [
        {"name": "Prod", "host": "prod.example.com"},
        {"name": "Stage", "host": "stage.example.com"},
    ]
    """
    panes = []
    for i, server in enumerate(servers):
        pane = {
            "name": server["name"],
            "command": f"ssh {server['host']}",
        }
        if i > 0:
            pane["split"] = "vertical"
        panes.append(pane)

    return await create_split_layout(connection, panes)


# ============================================================
# Utility Functions
# ============================================================

async def wait_for_prompt(session, timeout: float = 30.0):
    """Wait for shell prompt (requires shell integration)."""
    # Check if at shell prompt
    at_prompt = await session.async_get_variable("session.terminalHasInput")
    if at_prompt:
        return True

    # Simple wait approach
    await asyncio.sleep(0.5)
    return True


async def get_current_directory(session) -> Optional[str]:
    """Get current directory (requires shell integration)."""
    try:
        return await session.async_get_variable("path")
    except:
        return None
```

---

## Usage Examples

```python
import iterm2
from iterm2_helpers import create_dev_layout, create_ssh_layout

async def main(connection):
    # Development layout
    window, sessions = await create_dev_layout(
        connection,
        "~/projects/myapp",
        editor_cmd="code .",
        server_cmd="npm run dev"
    )

    # SSH layout
    window2, sessions2 = await create_ssh_layout(
        connection,
        [
            {"name": "Prod", "host": "prod.example.com"},
            {"name": "Stage", "host": "stage.example.com"},
        ]
    )

iterm2.run_until_complete(main)
```

---

## Related Documentation

- [Python API Guide](../03-scripting/python-api-guide.md)
- [Terminal Automation](../05-integration-patterns/terminal-automation.md)
