# Terminal Automation Scenarios

> Real-world automation examples for iTerm2.

---

## Development Environment

### Start Project

```python
import iterm2

async def start_project(connection, project_path):
    window = await iterm2.Window.async_create(connection)
    tab = window.current_tab

    # Editor pane
    editor = tab.current_session
    await editor.async_set_name("Editor")
    await editor.async_send_text(f"cd {project_path} && vim .\n")

    # Terminal pane
    terminal = await editor.async_split_pane(vertical=True)
    await terminal.async_set_name("Terminal")
    await terminal.async_send_text(f"cd {project_path}\n")

    # Server pane
    server = await terminal.async_split_pane(vertical=False)
    await server.async_set_name("Server")
    await server.async_send_text(f"cd {project_path} && npm run dev\n")

iterm2.run_until_complete(lambda c: start_project(c, "~/projects/myapp"))
```

---

## SSH Session Manager

```python
import iterm2

SERVERS = [
    {"name": "Production", "host": "prod.example.com", "color": "red"},
    {"name": "Staging", "host": "stage.example.com", "color": "orange"},
    {"name": "Dev", "host": "dev.example.com", "color": "green"},
]

async def connect_servers(connection):
    window = await iterm2.Window.async_create(connection)

    for i, server in enumerate(SERVERS):
        if i == 0:
            session = window.current_tab.current_session
        else:
            session = await session.async_split_pane(vertical=True)

        await session.async_set_name(server["name"])
        await session.async_send_text(f"ssh {server['host']}\n")

iterm2.run_until_complete(connect_servers)
```

---

## Log Monitoring

```python
import iterm2

LOG_FILES = [
    "/var/log/app/error.log",
    "/var/log/app/access.log",
    "/var/log/app/debug.log",
]

async def monitor_logs(connection):
    window = await iterm2.Window.async_create(connection)
    session = window.current_tab.current_session

    for i, log_file in enumerate(LOG_FILES):
        if i > 0:
            session = await session.async_split_pane(vertical=False)

        await session.async_set_name(log_file.split("/")[-1])
        await session.async_send_text(f"tail -f {log_file}\n")

iterm2.run_until_complete(monitor_logs)
```

---

## Daily Standup Setup

```python
import iterm2

async def standup_setup(connection):
    # Window 1: Code
    code_win = await iterm2.Window.async_create(connection)
    code_session = code_win.current_tab.current_session
    await code_session.async_send_text("cd ~/work && git status\n")

    # Window 2: Tasks
    tasks_win = await iterm2.Window.async_create(connection)
    tasks_session = tasks_win.current_tab.current_session
    await tasks_session.async_send_text("cat ~/TODO.md\n")

iterm2.run_until_complete(standup_setup)
```

---

## Related Documentation

- [Multi-Window Launcher](./multi-window-launcher.md)
- [Python API Guide](../03-scripting/python-api-guide.md)
