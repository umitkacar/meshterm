# Split Panes

> Divide your terminal into multiple sessions within a single tab.

---

## Overview

Split panes allow you to run multiple terminal sessions side by side, maximizing screen real estate and improving workflow efficiency.

```
┌────────────────────────────────────────────────────────┐
│                    Single Pane                         │
│                       (Default)                        │
└────────────────────────────────────────────────────────┘

         ⌘D (vertical)         ⌘⇧D (horizontal)
              │                      │
              ▼                      ▼

┌──────────────┬─────────────────┐  ┌──────────────────────┐
│              │                 │  │       Pane 1         │
│   Pane 1     │     Pane 2      │  ├──────────────────────┤
│              │                 │  │       Pane 2         │
└──────────────┴─────────────────┘  └──────────────────────┘
     Vertical Split                   Horizontal Split
```

---

## Keyboard Shortcuts

| Action | Shortcut | Description |
|--------|----------|-------------|
| **Split Vertically** | `⌘D` | Create pane to the right |
| **Split Horizontally** | `⌘⇧D` | Create pane below |
| **Navigate Panes** | `⌘⌥↑↓←→` | Move focus between panes |
| **Next Pane** | `⌘]` | Cycle forward |
| **Previous Pane** | `⌘[` | Cycle backward |
| **Maximize Pane** | `⌘⇧↩` | Toggle fullscreen pane |
| **Close Pane** | `⌘W` | Close current pane |
| **Swap Panes** | `⌘⇧⌥←→` | Swap pane positions |

---

## Common Layouts

### Two Panes (Editor + Terminal)

```
┌─────────────────────┬─────────────────────┐
│                     │                     │
│       Editor        │      Terminal       │
│     (vim/code)      │    (npm run dev)    │
│                     │                     │
└─────────────────────┴─────────────────────┘
```

**Setup:**
1. `⌘D` - Split vertically
2. Left: `vim .` or open editor
3. Right: `npm run dev` or commands

### Three Panes (Dev Environment)

```
┌─────────────────────┬─────────────────────┐
│                     │      Terminal       │
│       Editor        ├─────────────────────┤
│                     │       Logs          │
└─────────────────────┴─────────────────────┘
```

**Setup:**
1. `⌘D` - Split vertically
2. Focus right pane
3. `⌘⇧D` - Split horizontally

### Four Panes (Quad)

```
┌─────────────────────┬─────────────────────┐
│       Pane 1        │       Pane 2        │
├─────────────────────┼─────────────────────┤
│       Pane 3        │       Pane 4        │
└─────────────────────┴─────────────────────┘
```

**Setup:**
1. `⌘D` - Split vertically
2. `⌘⇧D` - Split first pane horizontally
3. Focus second pane (`⌘⌥→`)
4. `⌘⇧D` - Split second pane horizontally

---

## Resizing Panes

### Using Keyboard

| Action | Shortcut |
|--------|----------|
| **Resize Left** | `⌃⌘←` |
| **Resize Right** | `⌃⌘→` |
| **Resize Up** | `⌃⌘↑` |
| **Resize Down** | `⌃⌘↓` |

### Using Mouse

- **Drag divider** - Click and drag the pane border
- **Double-click divider** - Reset to equal sizes

---

## Pane Titles

Show what each pane is running:

```
Settings → Profiles → Session
☑ Show per-pane title bar with split panes
```

Title shows:
- Session name (if set)
- Current command
- Current directory

---

## Python API Examples

### Create Split Layout

```python
import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = await iterm2.Window.async_create(connection)
    tab = window.current_tab

    # Get the initial session
    left = tab.current_session

    # Split vertically (creates pane to the right)
    right = await left.async_split_pane(vertical=True)

    # Split the right pane horizontally
    bottom_right = await right.async_split_pane(vertical=False)

    # Name the sessions
    await left.async_set_name("Editor")
    await right.async_set_name("Terminal")
    await bottom_right.async_set_name("Logs")

    # Run commands
    await left.async_send_text("vim .\n")
    await right.async_send_text("npm run dev\n")
    await bottom_right.async_send_text("tail -f logs/*.log\n")

iterm2.run_until_complete(main)
```

### Split with Profile

```python
# Split using a specific profile
right = await left.async_split_pane(
    vertical=True,
    profile="Remote SSH"
)
```

### Get All Sessions in Tab

```python
async def list_sessions(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_window
    tab = window.current_tab

    for session in tab.sessions:
        name = await session.async_get_variable("name")
        print(f"Session: {name}")
```

---

## AppleScript Examples (Legacy)

### Create Split

```applescript
tell application "iTerm2"
    tell current session of current tab of current window
        -- Split vertically
        split vertically with default profile

        -- Or split horizontally
        split horizontally with default profile
    end tell
end tell
```

### Navigate Between Panes

```applescript
tell application "iTerm2"
    tell current tab of current window
        select session at 0  -- Select first session
    end tell
end tell
```

---

## Advanced Features

### Broadcast Input

Send keystrokes to all panes simultaneously:

```
Shell → Broadcast Input → Broadcast Input to All Panes in Current Tab
```

**Use Case:** Run same command on multiple servers

### Synchronized Scrolling

Not natively supported, but can use tmux integration for this.

### Moving Panes

Move a pane to:
- Another tab: Drag the pane title to tab bar
- Another window: Drag to window title or desktop

---

## Troubleshooting

### Panes Not Equal Size

```
View → Make Panes Same Size
```

Or double-click the divider.

### Can't Navigate to Pane

Check for:
- Blocked by dialog
- Pane is in fullscreen
- Focus is in search bar

Try `Esc` then `⌘⌥→`.

### Split Creates Wrong Direction

Remember:
- `⌘D` = Vertical (side by side)
- `⌘⇧D` = Horizontal (top/bottom)

---

## Related Documentation

- [Window Arrangements](./profiles.md#arrangements)
- [Python API: Session](../03-scripting/python-api-reference.md#session)
- [tmux Integration](./tmux-integration.md)
