# Hotkey Window

> System-wide instant access terminal with a single keystroke.

---

## Overview

The Hotkey Window provides Quake-style dropdown terminal access from anywhere on your Mac. Press a hotkey and your terminal appears; press again and it hides.

---

## Configuration

### Basic Setup

```
Settings → Keys → Hotkey → Create a Dedicated Hotkey Window
```

### Hotkey Options

| Setting | Recommended |
|---------|-------------|
| **Hotkey** | Double-tap ⌥ or ⌃` |
| **Pin hotkey window** | As needed |
| **Animate show/hide** | Yes |
| **Floating window** | Yes (stays on top) |

---

## Window Styles

| Style | Description |
|-------|-------------|
| **Normal** | Standard window |
| **Fullscreen** | Covers entire screen |
| **Top of Screen** | Dropdown from top |
| **Bottom** | Slides from bottom |
| **Left/Right** | Side panels |

---

## Advanced Options

### Profile Assignment

Assign a specific profile to hotkey window:

```
Settings → Profiles → Keys → Hotkey Window
☑ A hotkey opens a dedicated window with this profile
```

### Multiple Hotkey Windows

Create different hotkey windows for different purposes:
1. Quick commands (small, top)
2. SSH sessions (side panel)
3. Full development (fullscreen)

---

## Python API

```python
import iterm2

async def toggle_hotkey_window(connection):
    app = await iterm2.async_get_app(connection)
    # Hotkey windows are regular windows with special properties
    for window in app.windows:
        if await window.async_get_variable("isHotkeyWindow"):
            # Found hotkey window
            await window.async_activate()

iterm2.run_until_complete(toggle_hotkey_window)
```

---

## Related Documentation

- [Profiles](./profiles.md)
- [Window Arrangements](./profiles.md#arrangements)
