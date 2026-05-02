# tmux Integration

> Native iTerm2 interface for tmux sessions.

---

## Overview

iTerm2's tmux integration lets you use native iTerm2 tabs and split panes instead of tmux's built-in UI, while keeping all tmux session management benefits.

---

## Getting Started

### Start New Session

```bash
tmux -CC
```

### Attach to Existing

```bash
tmux -CC attach
# or
tmux -CC attach -t session-name
```

---

## How It Works

| tmux Concept | iTerm2 Equivalent |
|--------------|-------------------|
| tmux window | iTerm2 tab |
| tmux pane | iTerm2 split pane |
| tmux session | iTerm2 window |

**Benefits:**
- No prefix key needed
- Native copy/paste
- Mouse support works naturally
- iTerm2 shortcuts work
- Scrollback works normally

---

## Commands

| Action | iTerm2 Way |
|--------|-----------|
| New window | `⌘T` |
| Split vertical | `⌘D` |
| Split horizontal | `⌘⇧D` |
| Navigate panes | `⌘⌥↑↓←→` |
| Close pane | `⌘W` |
| Detach | Shell → tmux → Detach |

---

## Dashboard

Access tmux dashboard:

```
Shell → tmux → Dashboard
```

Features:
- View all sessions
- Rename sessions
- Kill sessions
- Switch sessions

---

## Buried Sessions

When you close a tmux-integrated window, the session becomes "buried":

```
Session → Buried Sessions → [session name]
```

---

## Python API

```python
import iterm2

async def list_tmux_connections(connection):
    app = await iterm2.async_get_app(connection)
    tmux_connections = await iterm2.async_get_tmux_connections(connection)

    for tc in tmux_connections:
        print(f"tmux session: {tc.connection_id}")

iterm2.run_until_complete(list_tmux_connections)
```

---

## Related Documentation

- [Split Panes](./split-panes.md)
- [Buried Sessions](./all-features.md#buried-sessions)
