# iTerm2 Scripting Workflow Overview

> Understanding the architecture of iTerm2 automation approaches.

---

## Scripting Approaches Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        iTerm2 SCRIPTING WORKFLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │     USER        │
                              │  (Developer)    │
                              └────────┬────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
          ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
          │   BASH SCRIPT   │ │  PYTHON SCRIPT  │ │ APPLESCRIPT     │
          │   (shell.sh)    │ │   (script.py)   │ │ (script.scpt)   │
          └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
                   │                   │                   │
                   ▼                   ▼                   ▼
          ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
          │    osascript    │ │  iterm2 module  │ │  Apple Events   │
          │   (CLI bridge)  │ │  (Python API)   │ │  (Direct IPC)   │
          └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
                   │                   │                   │
                   │         ⭐ MODERN │                   │ ⚠️ DEPRECATED
                   │                   │                   │
                   └───────────────────┴───────────────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────────────┐
                    │           iTerm2 APPLICATION          │
                    │  ┌──────────────────────────────────┐ │
                    │  │         Python API Server        │ │
                    │  │  (26 modules, websocket-based)   │ │
                    │  └──────────────────────────────────┘ │
                    │                  │                    │
                    │  ┌───────────────┼───────────────┐    │
                    │  ▼               ▼               ▼    │
                    │ ┌─────┐      ┌─────┐        ┌─────┐   │
                    │ │WINDOW│      │ TAB │        │SESSION│ │
                    │ └─────┘      └─────┘        └─────┘   │
                    └──────────────────────────────────────┘
```

---

## Three Approaches Compared

| Aspect | Python API | AppleScript | Bash + osascript |
|--------|------------|-------------|------------------|
| **Status** | ⭐ RECOMMENDED | ⚠️ DEPRECATED | 🔧 Workaround |
| **Connection** | WebSocket | Apple Events (IPC) | osascript CLI |
| **Speed** | Fast | Medium | Slow |
| **Error Handling** | ✅ try/except | ⚠️ Limited | ❌ Very weak |
| **Async Support** | ✅ Native asyncio | ❌ None | ❌ None |
| **Modules** | 26 specialized | N/A | N/A |
| **Quote Escaping** | ❌ None needed | ⚠️ Sometimes | ✅ Major issue |
| **Learning Curve** | Medium | Low | Low |
| **New Features** | ✅ Active | ❌ None | N/A |

---

## Decision Flowchart

```
                    Need iTerm2 Automation?
                            │
              ┌─────────────┴─────────────┐
              │                           │
         New Project?               Legacy Code?
              │                           │
              ▼                           ▼
     ┌────────────────┐          ┌────────────────┐
     │  Python API    │          │  Evaluate      │
     │  ⭐ USE THIS    │          │  Migration     │
     └───────┬────────┘          └───────┬────────┘
             │                           │
             ▼                           ▼
     • Modern async/await        Worth migrating?
     • 26 modules                       │
     • Active development        ┌──────┴──────┐
     • No quote issues           │             │
                                Yes           No
                                 │             │
                                 ▼             ▼
                         ┌──────────┐  ┌──────────┐
                         │ Migrate  │  │ Keep     │
                         │ to Python│  │ + Fix    │
                         └──────────┘  └──────────┘
```

---

## Object Hierarchy

All three approaches interact with the same object model:

```
Application (iTerm2)
    │
    ├── Window
    │   │
    │   ├── Tab
    │   │   │
    │   │   ├── Session (Terminal instance)
    │   │   │   ├── name
    │   │   │   ├── profile
    │   │   │   ├── variables
    │   │   │   └── ...
    │   │   │
    │   │   └── Session
    │   │
    │   └── Tab
    │
    └── Window
```

**Key Insight:** Sessions are where all the action happens. Tabs are just containers.

---

## Quick Comparison Examples

### Create Window with Session Name

**Python API (Recommended):**
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

**AppleScript (Deprecated):**
```applescript
tell application "iTerm2"
    create window with default profile
    tell current session of current tab of current window
        set name to "My Session"
        write text "echo 'Hello'"
    end tell
end tell
```

**Bash + osascript (Workaround):**
```bash
osascript << 'EOF'
tell application "iTerm2"
    create window with default profile
    tell current session of current tab of current window
        set name to "My Session"
        write text "echo 'Hello'"
    end tell
end tell
EOF
```

---

## Communication Protocols

### Python API (WebSocket)

```
┌─────────────┐         WebSocket          ┌─────────────┐
│   Python    │ ◄─────────────────────────► │   iTerm2    │
│   Script    │     JSON-RPC messages      │   Server    │
└─────────────┘                            └─────────────┘
     async/await                           Port: dynamic
```

**Advantages:**
- Persistent connection
- Bidirectional communication
- Event subscription
- Efficient for multiple operations

### AppleScript (Apple Events)

```
┌─────────────┐        Apple Events        ┌─────────────┐
│ AppleScript │ ─────────────────────────► │   iTerm2    │
│   Engine    │         IPC/XPC            │     App     │
└─────────────┘                            └─────────────┘
     Synchronous                           Direct process
```

**Limitations:**
- One command at a time
- No event subscription
- Synchronous only
- Limited error info

---

## When to Use What

| Scenario | Recommendation |
|----------|----------------|
| New automation project | Python API |
| Complex multi-window layouts | Python API |
| Status bar customization | Python API |
| Event-driven automation | Python API |
| Simple one-off command | osascript (quick) |
| Existing AppleScript codebase | Keep or migrate |
| Integration with Keyboard Maestro | AppleScript |
| Integration with Shortcuts.app | AppleScript |

---

## Migration Path

```
┌─────────────────────────────────────────────────────────────────┐
│                    MIGRATION STRATEGY                            │
└─────────────────────────────────────────────────────────────────┘

    AppleScript                    Python API
    ───────────                    ──────────

    tell application "iTerm2"  →   import iterm2
                                   async def main(connection):

    create window with         →   window = await iterm2.Window
        default profile                .async_create(connection)

    current session of         →   session = window.current_tab
        current tab of                       .current_session
        current window

    set name to "X"            →   await session.async_set_name("X")

    write text "cmd"           →   await session.async_send_text("cmd\n")

    split vertically           →   await session.async_split_pane(
                                       vertical=True)

    end tell                   →   iterm2.run_until_complete(main)
```

---

## Related Documentation

- [Python API Guide](./python-api-guide.md) - ⭐ Modern approach
- [Python API Reference](./python-api-reference.md) - 26 modules
- [AppleScript Legacy](./applescript-legacy.md) - Deprecated
- [Migration Guide](./migration-guide.md) - How to migrate
