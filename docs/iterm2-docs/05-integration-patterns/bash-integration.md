# Bash + iTerm2 Integration

> Calling iTerm2 automation from shell scripts.

---

## AppleScript via osascript

### Inline Command

```bash
osascript -e 'tell application "iTerm2" to create window with default profile'
```

### Heredoc (Recommended)

```bash
osascript << 'EOF'
tell application "iTerm2"
    create window with default profile
    tell current session of current tab of current window
        write text "echo 'Hello'"
    end tell
end tell
EOF
```

### Temp File Pattern

```bash
SCRIPT=$(mktemp /tmp/iterm.XXXXXX.scpt)
cat > "$SCRIPT" << 'EOF'
tell application "iTerm2"
    create window with default profile
end tell
EOF
osascript "$SCRIPT"
rm -f "$SCRIPT"
```

---

## Python API from Bash

```bash
python3 << 'EOF'
import iterm2

async def main(connection):
    window = await iterm2.Window.async_create(connection)
    session = window.current_tab.current_session
    await session.async_send_text("ls -la\n")

iterm2.run_until_complete(main)
EOF
```

---

## Helper Functions

```bash
#!/bin/bash

iterm_new_window() {
    local command="${1:-}"
    python3 << EOF
import iterm2

async def main(connection):
    window = await iterm2.Window.async_create(connection)
    session = window.current_tab.current_session
    if "${command}":
        await session.async_send_text("${command}\n")

iterm2.run_until_complete(main)
EOF
}

iterm_send_text() {
    local text="$1"
    python3 << EOF
import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    session = app.current_window.current_tab.current_session
    await session.async_send_text("${text}\n")

iterm2.run_until_complete(main)
EOF
}

# Usage
iterm_new_window "cd ~/projects"
iterm_send_text "npm run dev"
```

---

## Related Documentation

- [Python Integration](./python-integration.md)
- [Multi-Window Launcher](./multi-window-launcher.md)
