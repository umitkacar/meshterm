# Quick Reference

> Essential iTerm2 3.6.9 shortcuts and commands at a glance.
>
> **Updated:** 2026-03-23

---

## Keyboard Shortcuts

### Window & Tab Management

| Action | Shortcut |
|--------|----------|
| New Window | `⌘N` |
| New Tab | `⌘T` |
| Close Tab/Pane | `⌘W` |
| Next Tab | `⌘→` or `⌘⇧]` |
| Previous Tab | `⌘←` or `⌘⇧[` |
| Go to Tab 1-9 | `⌘1` - `⌘9` |

### Split Panes

| Action | Shortcut |
|--------|----------|
| Split Vertical | `⌘D` |
| Split Horizontal | `⌘⇧D` |
| Navigate Panes | `⌘⌥↑↓←→` |
| Maximize Pane | `⌘⇧↩` |

### Search & Edit

| Action | Shortcut |
|--------|----------|
| Find | `⌘F` |
| Autocomplete | `⌘;` |
| Paste History | `⌘⇧H` |
| Command History | `⌘⇧;` |
| Copy Mode | `⌘⇧C` |
| Clear Buffer | `⌘K` |

### Navigation

| Action | Shortcut |
|--------|----------|
| Previous Command | `⌘⇧↑` |
| Next Command | `⌘⇧↓` |
| Recent Directories | `⌘⌥/` |
| Open Quickly | `⌘⇧O` |
| Cursor Guide | `⌘/` |

### New Features

| Action | Location |
|--------|----------|
| AI Chat | Window → AI Chat |
| Explain Output | Edit → Explain Output with AI |
| Composer | View → Show Composer |
| Auto Composer | View → Auto Composer |
| Window Projects | Window → Projects |
| Session Logging | Session → Log → Log to File |
| Instant Replay | `⌘⌥B` |

---

## Shell Integration Utilities

```bash
imgcat image.png     # Display image
imgls                # List with thumbnails
it2copy              # Copy to clipboard
it2dl file           # Download file
it2ul file           # Upload file
it2check             # Verify integration
```

---

## Python API Quick Start

```python
import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = await iterm2.Window.async_create(connection)
    session = window.current_tab.current_session
    await session.async_set_name("My Session")
    await session.async_send_text("echo 'Hello'\n")

iterm2.run_until_complete(main)
```

---

## AppleScript Quick Start (Legacy)

```applescript
tell application "iTerm2"
    create window with default profile
    tell current session of current tab of current window
        set name to "My Session"
        write text "echo 'Hello'"
    end tell
end tell
```

---

## Common Paths

| Location | Path |
|----------|------|
| Settings | `~/Library/Preferences/com.googlecode.iterm2.plist` |
| Scripts | `~/Library/Application Support/iTerm2/Scripts/` |
| Auto-Launch | `~/Library/Application Support/iTerm2/Scripts/AutoLaunch/` |
| Dynamic Profiles | `~/Library/Application Support/iTerm2/DynamicProfiles/` |
| Window Projects | `~/Library/Application Support/iTerm2/` (JSON) |
| Session Logs | Configured per profile (Settings → Profiles → Session) |

---

## Version Info

| Component | Current |
|-----------|---------|
| **iTerm2** | 3.6.9 (Mar 2026) |
| **Python API** | v2.14 (Feb 2026) |
| **macOS** | 12.4+ required |
| **Python** | 3.6+ (3.14 compatible) |
| **Modules** | 30 |
| **Trigger Actions** | 26 |
