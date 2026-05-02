# Python API Reference

> Complete reference for all 30 iTerm2 Python API modules (v2.14, Feb 2026).
>
> **PyPI:** `pip install iterm2` (v2.14) | **Python:** 3.6+ (3.14 compatible)

---

## Module Overview

| Module | Purpose | Status |
|--------|---------|--------|
| **Alert** | Display alerts and PolyModalAlert dialogs | Stable |
| **App** | Application-level operations | Stable |
| **Arrangement** | Save/restore window layouts | Stable |
| **Binding** | Key binding management | New (undocumented) |
| **Broadcast** | Send input to multiple sessions | Stable |
| **Color** | Color manipulation | Stable |
| **ColorPresets** | Manage color schemes | Stable |
| **Connection** | API connection management | Stable |
| **CustomControl** | Custom escape sequences | Stable |
| **FilePanel** | Native Open/Save file dialogs | New (undocumented) |
| **Focus** | Focus tracking and management | Stable |
| **Keyboard** | Keyboard input | Stable |
| **LifeCycle** | App lifecycle events | Stable |
| **MainMenu** | Menu bar customization | Stable |
| **Preferences** | App preferences | Stable |
| **Profile** | Profile management | Stable |
| **Prompt** | Prompt customization + history | Enhanced |
| **Registration** | Script registration | Stable |
| **Screen** | Screen content access | Stable |
| **Selection** | Text selection | Stable |
| **Session** | Terminal session control | Stable |
| **StatusBar** | Status bar components | Stable |
| **Tab** | Tab management | Stable |
| **Tmux** | tmux integration | Stable |
| **Tool** | Toolbelt tools | Stable |
| **Transaction** | Atomic operations | Stable |
| **Triggers** | Trigger definitions (26 types) | New (undocumented) |
| **Utilities** | Helper functions | Stable |
| **Variables** | Variable access | Stable |
| **Window** | Window management | Stable |

---

## Core Modules

### App

```python
import iterm2

async def main(connection):
    # Get app instance
    app = await iterm2.async_get_app(connection)

    # Properties
    print(f"Windows: {len(app.windows)}")
    print(f"Current window: {app.current_window}")
    print(f"Current terminal window: {app.current_terminal_window}")

    # Get variable
    theme = await app.async_get_variable("effectiveTheme")
```

### Window

```python
# Create window
window = await iterm2.Window.async_create(connection)
window = await iterm2.Window.async_create(connection, profile="Name")

# Properties
window.window_id
window.tabs
window.current_tab

# Methods
await window.async_activate()
await window.async_close()
await window.async_create_tab()
await window.async_create_tab(profile="Name")
await window.async_set_fullscreen(True)
await window.async_set_tabs([tab1, tab2])  # Reorder
```

### Tab

```python
tab = window.current_tab

# Properties
tab.tab_id
tab.sessions
tab.current_session
tab.root

# Methods
await tab.async_activate()
await tab.async_close()
await tab.async_select_pane_in_direction("left")
await tab.async_set_title("My Tab")
await tab.async_update_layout()
```

### Session

```python
session = tab.current_session

# Properties
session.session_id
session.name
session.profile

# Text Operations
await session.async_send_text("command\n")
await session.async_send_text("text", suppress_broadcast=True)

# Session Management
await session.async_set_name("Name")
await session.async_activate()
await session.async_close()

# Split Panes
new = await session.async_split_pane(vertical=True)
new = await session.async_split_pane(vertical=False, profile="Name")

# Variables
path = await session.async_get_variable("path")
await session.async_set_variable("user.custom", "value")

# Screen Content
contents = await session.async_get_screen_contents()
for line in contents.lines:
    print(line.string)
```

---

## Profile Module

```python
# Query profiles
profiles = await iterm2.PartialProfile.async_query(connection)

# Get full profile
full = await partial_profile.async_get_full_profile()

# Get default
default = await iterm2.Profile.async_get_default(connection)

# Create new profile
new_profile = iterm2.LocalWriteOnlyProfile()
new_profile.set_name("My Profile")
new_profile.set_foreground_color(iterm2.Color(255, 255, 255))
new_profile.set_background_color(iterm2.Color(0, 0, 0))
new_profile.set_badge_text("\\(user)")
new_profile.set_triggers([...])

await new_profile.async_create(connection)

# Modify existing
changes = iterm2.LocalWriteOnlyProfile()
changes.set_name("New Name")
await profile.async_set_local_write_only_profile(changes)
```

---

## Color Module

```python
# Create color
red = iterm2.Color(255, 0, 0)
transparent_blue = iterm2.Color(0, 0, 255, 128)

# Color presets
presets = await iterm2.ColorPreset.async_get_list(connection)
preset = await iterm2.ColorPreset.async_get(connection, "Solarized Dark")
```

---

## Status Bar Module

```python
# Create component
component = iterm2.StatusBarComponent(
    short_description="My Widget",
    detailed_description="Description",
    knobs=[
        iterm2.StringKnob("Label", "key", "default")
    ],
    exemplar="Sample",
    update_cadence=5,  # seconds
    identifier="com.example.widget"
)

# Register with callback
@iterm2.StatusBarRPC
async def widget_callback(knobs):
    return "Display Text"

await component.async_register(connection, widget_callback)
```

---

## Monitor Modules

### NewSessionMonitor

```python
async with iterm2.NewSessionMonitor(connection) as mon:
    while True:
        session_id = await mon.async_get()
        print(f"New session: {session_id}")
```

### VariableMonitor

```python
async with iterm2.VariableMonitor(
    connection,
    iterm2.VariableScopes.SESSION,
    "path",
    None  # or specific session
) as mon:
    while True:
        change = await mon.async_get()
        print(f"Path: {change.new_value}")
```

### FocusMonitor

```python
async with iterm2.FocusMonitor(connection) as mon:
    while True:
        update = await mon.async_get()
        if update.window_changed:
            print(f"Window focused: {update.window_id}")
```

---

## Broadcast Module

```python
# Get broadcast domains
domains = await iterm2.BroadcastDomain.async_get(connection)

# Set broadcasting for session
await session.async_set_broadcast_domains([domain])
```

---

## Arrangement Module

```python
# List arrangements
arrangements = await iterm2.Arrangement.async_list(connection)

# Save current
await iterm2.Arrangement.async_save(connection, "My Layout")

# Restore
await iterm2.Arrangement.async_restore(connection, "My Layout")
```

---

## Transaction Module

```python
# Atomic operations
async with iterm2.Transaction(connection):
    window = await iterm2.Window.async_create(connection)
    tab = await window.async_create_tab()
    session = tab.current_session
    await session.async_set_name("Atomic")
```

---

## Variables Reference

### Session Variables

| Variable | Description |
|----------|-------------|
| `path` | Current directory |
| `name` | Session name |
| `hostname` | Connected host |
| `username` | Current user |
| `lastCommand` | Last command info |
| `jobName` | Current job |
| `termid` | Terminal ID |
| `profileName` | Profile name |

### App Variables

| Variable | Description |
|----------|-------------|
| `effectiveTheme` | Current theme |
| `pid` | Process ID |

### User Variables

```python
# Set
await session.async_set_variable("user.myvar", "value")

# Get
value = await session.async_get_variable("user.myvar")
```

---

## New Modules (v2.10+)

### Binding Module

Manage global and per-profile key bindings programmatically.

```python
import iterm2

async def manage_keybindings(connection):
    # Get global key bindings
    bindings = await iterm2.async_get_global_key_bindings(connection)

    for binding in bindings:
        print(f"Key: {binding.key}, Action: {binding.action}")

    # Create a new key binding
    new_binding = iterm2.KeyBinding(
        key="cmd+shift+t",
        action=iterm2.BindingAction.SEND_TEXT,
        parameter="Hello from binding\n"
    )

    # Set global bindings
    bindings.append(new_binding)
    await iterm2.async_set_global_key_bindings(connection, bindings)
```

**Key Classes:**
- `KeyBinding` — A single key binding definition
- `BindingAction` — 64+ predefined actions
- `PasteConfiguration` — Paste behavior settings
- `MoveSelectionUnit` — Selection movement units
- `SnippetIdentifier` — Snippet references

### FilePanel Module

Display native macOS Open/Save file dialogs (requires iTerm2 3.5.0beta6+).

```python
import iterm2

async def open_file_dialog(connection):
    panel = iterm2.OpenPanel(
        options=[
            iterm2.OpenPanel.CAN_CHOOSE_DIRECTORIES,
            iterm2.OpenPanel.ALLOWS_MULTIPLE_SELECTION,
            iterm2.OpenPanel.SHOWS_HIDDEN_FILES
        ]
    )
    result = await panel.async_run(connection)
    if result:
        print(f"Selected: {result}")

async def save_file_dialog(connection):
    panel = iterm2.SavePanel()
    result = await panel.async_run(connection)
    if result:
        print(f"Save to: {result}")
```

### Triggers Module

Define 26 trigger types programmatically with regex matching and automated actions.

```python
import iterm2

# Available trigger types (26 total):
# HighlightTrigger, SendTextTrigger, RunCommandTrigger,
# AlertTrigger, RPCTrigger, FoldTrigger, SGRTrigger,
# BufferInputTrigger, SetNamedMarkTrigger, AnnotateTrigger,
# BounceDockIconTrigger, CaptureOutputTrigger, ...

# Match types for event-based triggers:
# EVENT_LONG_RUNNING_COMMAND, EVENT_CUSTOM_ESCAPE_SEQUENCE,
# EVENT_SESSION_ENDED, EVENT_ACTIVITY_AFTER_IDLE, EVENT_BELL_RECEIVED
```

**New Trigger Types (2025-2026):**

| Trigger | Added | Description |
|---------|-------|-------------|
| `SetNamedMarkTrigger` | Jan 2025 | Create named scroll markers |
| `FoldTrigger` | Jan 2025 | Code folding markers |
| `SGRTrigger` | Mar 2025 | Terminal graphics (Select Graphic Rendition) |
| `BufferInputTrigger` | Dec 2025 | Input buffering control |

### PolyModalAlert (v2.12+)

Rich multi-element modal dialogs (extends Alert module).

```python
import iterm2

async def rich_dialog(connection):
    alert = iterm2.PolyModalAlert()
    alert.add_text_field("Enter your name:", "name_field", "default")
    alert.add_checkbox_item("Enable logging", "logging", True)
    alert.add_combobox("Select environment:", "env",
                       ["development", "staging", "production"])
    alert.add_button("OK")
    alert.add_button("Cancel")

    result = await alert.async_run(connection)
    # result is a PolyModalResult with field values
```

### Prompt Enhancements

```python
import iterm2

async def list_command_history(connection):
    # NEW: Retrieve prompt unique IDs within a session
    prompts = await iterm2.async_list_prompts(
        connection,
        session_id="session-uuid",
        first=0,
        last=10
    )
    for prompt in prompts:
        print(f"Prompt ID: {prompt.unique_id}")
```

---

## Version Compatibility

| iterm2 PyPI | iTerm2 App | Key Addition |
|-------------|-----------|--------------|
| 2.14 | 3.6.9 | URL loading, type safety, Python 3.14 compat |
| 2.13 | 3.6.x | BufferInputTrigger |
| 2.12 | 3.6.x | PolyModalAlert, SGRTrigger |
| 2.11 | 3.5.x+ | Bug fixes |
| 2.10 | 3.5.x+ | SGRTrigger, Binding/FilePanel/Triggers modules |

---

## Related Documentation

- [Python API Guide](./python-api-guide.md)
- [Official API Docs](https://iterm2.com/python-api/)
