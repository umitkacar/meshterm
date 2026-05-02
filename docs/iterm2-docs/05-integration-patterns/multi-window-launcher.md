# Multi-Window Launcher

> Create complex multi-window layouts programmatically.

---

## Python API Approach (Recommended)

```python
#!/usr/bin/env python3
"""Multi-window development environment launcher."""
import iterm2
import asyncio

LAYOUT = {
    "windows": [
        {
            "name": "Development",
            "bounds": [0, 0, 960, 1080],
            "panes": [
                {"name": "Editor", "command": "vim .", "split": None},
                {"name": "Terminal", "command": None, "split": "vertical"},
            ]
        },
        {
            "name": "Servers",
            "bounds": [960, 0, 1920, 540],
            "panes": [
                {"name": "Backend", "command": "npm run backend", "split": None},
                {"name": "Frontend", "command": "npm run frontend", "split": "vertical"},
            ]
        },
        {
            "name": "Logs",
            "bounds": [960, 540, 1920, 1080],
            "panes": [
                {"name": "App Logs", "command": "tail -f logs/app.log", "split": None},
            ]
        }
    ]
}

async def create_layout(connection):
    for win_config in LAYOUT["windows"]:
        window = await iterm2.Window.async_create(connection)
        tab = window.current_tab
        session = tab.current_session

        for i, pane in enumerate(win_config["panes"]):
            if i > 0:
                if pane["split"] == "vertical":
                    session = await session.async_split_pane(vertical=True)
                else:
                    session = await session.async_split_pane(vertical=False)

            await session.async_set_name(pane["name"])

            if pane["command"]:
                await session.async_send_text(f"{pane['command']}\n")

        # Small delay between windows
        await asyncio.sleep(0.3)

if __name__ == "__main__":
    iterm2.run_until_complete(create_layout)
```

---

## AppleScript Approach (Legacy)

```applescript
tell application "iTerm2"
    -- Window 1: Development
    set win1 to (create window with default profile)
    tell win1
        set bounds to {0, 0, 960, 1080}
        tell current session of current tab
            set name to "Editor"
            write text "vim ."
            split vertically with default profile
        end tell
        tell session 2 of current tab
            set name to "Terminal"
        end tell
    end tell

    delay 0.5

    -- Window 2: Servers
    set win2 to (create window with default profile)
    tell win2
        set bounds to {960, 0, 1920, 540}
        tell current session of current tab
            set name to "Backend"
            write text "npm run backend"
        end tell
    end tell
end tell
```

---

## Configuration File Pattern

```yaml
# layout.yaml
project: MyApp
directory: ~/projects/myapp
windows:
  - name: Development
    panes:
      - name: Editor
        command: vim .
      - name: Terminal
        split: vertical

  - name: Services
    panes:
      - name: API
        command: npm run api
      - name: Web
        command: npm run web
        split: vertical
```

```python
#!/usr/bin/env python3
import iterm2
import yaml

async def main(connection):
    with open("layout.yaml") as f:
        config = yaml.safe_load(f)

    for win_config in config["windows"]:
        window = await iterm2.Window.async_create(connection)
        session = window.current_tab.current_session

        for i, pane in enumerate(win_config["panes"]):
            if i > 0:
                vertical = pane.get("split") == "vertical"
                session = await session.async_split_pane(vertical=vertical)

            await session.async_set_name(pane["name"])

            if pane.get("command"):
                cmd = pane["command"]
                if config.get("directory"):
                    cmd = f"cd {config['directory']} && {cmd}"
                await session.async_send_text(f"{cmd}\n")

iterm2.run_until_complete(main)
```

---

## Related Documentation

- [Terminal Automation](./terminal-automation.md)
- [Python API Guide](../03-scripting/python-api-guide.md)
