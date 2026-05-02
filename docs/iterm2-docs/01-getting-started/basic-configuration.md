# Basic Configuration Guide

> Essential iTerm2 settings for optimal productivity and appearance.

---

## Table of Contents

- [Settings Overview](#settings-overview)
- [General Settings](#general-settings)
- [Appearance Settings](#appearance-settings)
- [Profile Configuration](#profile-configuration)
- [Key Bindings](#key-bindings)
- [Recommended Configurations](#recommended-configurations)

---

## Settings Overview

Access settings via `⌘,` or `iTerm2 → Settings`

```
Settings Window Structure:
├── General          # App behavior, startup, closing
├── Appearance       # Theme, tabs, windows
├── Profiles         # Per-profile settings (most important!)
│   ├── General      # Working directory, command
│   ├── Colors       # Color scheme
│   ├── Text         # Font, cursor
│   ├── Window       # Size, style, background
│   ├── Terminal     # Scrollback, notifications
│   ├── Session      # Status bar, logs
│   ├── Keys         # Key mappings
│   └── Advanced     # Triggers, semantic history
├── Keys             # Global hotkeys
├── Arrangements     # Window layouts
├── Pointer          # Mouse behavior
└── Advanced         # Expert settings
```

---

## General Settings

### Startup

| Setting | Recommended | Purpose |
|---------|-------------|---------|
| **Open profiles window** | No | Cleaner startup |
| **Window restoration policy** | Use System Window Restoration | Resume sessions |
| **Quit when all windows closed** | No | Keep app running |

### Closing

| Setting | Recommended | Purpose |
|---------|-------------|---------|
| **Confirm closing multiple sessions** | Yes | Prevent accidents |
| **Confirm "Quit iTerm2"** | Only if there are... | Safety check |

### Magic

```
☑ Enable Python API                    # Required for scripting
☑ GPU Rendering                        # Better performance
☑ Use Metal                            # macOS GPU acceleration
```

### Services

```
☑ Check for updates automatically
☑ Load preferences from custom folder  # For sync: ~/Dropbox/iTerm2
```

---

## Appearance Settings

### General

| Setting | Recommended | Effect |
|---------|-------------|--------|
| **Theme** | Minimal | Clean look |
| **Tab bar location** | Top | Standard |
| **Status bar location** | Bottom | Less intrusive |

### Tabs

```
☑ Show tab bar even when there is only one tab    # Always visible
☐ Show tab numbers                                 # Cleaner
☐ Show tab close buttons                          # Prevent accidents
☑ Stretch tabs to fill bar                        # Better look
```

### Panes

```
☑ Show per-pane title bar with split panes        # Know which pane is which
☐ Separate background images per pane             # Usually unnecessary
```

### Windows

```
☑ Show window number in title bar                 # Multi-window navigation
☑ Show border around window                       # Clear boundaries
Hide scrollbars: Yes                              # Cleaner look
```

---

## Profile Configuration

### Colors (Most Important!)

#### Quick Theme Setup

```
Profiles → Colors → Color Presets... → Import...
```

**Top Themes:**

| Theme | Style | Get It |
|-------|-------|--------|
| **Dracula** | Dark, purple | draculatheme.com |
| **One Dark** | Dark, balanced | Built-in |
| **Solarized Dark** | Dark, low contrast | Built-in |
| **Nord** | Dark, blue | nordtheme.com |
| **Catppuccin** | Dark, pastel | catppuccin.com |
| **Tokyo Night** | Dark, blue/purple | GitHub |

#### Custom Colors

Key colors to customize:

```
Basic Colors:
├── Foreground: Main text color
├── Background: Terminal background
├── Bold: Bold text color
├── Selection: Selected text background
└── Cursor: Cursor color and text

ANSI Colors (16):
├── Black, Red, Green, Yellow (normal + bright)
├── Blue, Magenta, Cyan, White (normal + bright)
└── These affect command output colors
```

### Text

#### Font Configuration

```
Font: JetBrains Mono
Size: 13
☑ Use ligatures                        # -> becomes →
☑ Anti-aliased                         # Smooth text
☐ Use bold fonts                       # Optional
☑ Draw bold text in bright colors      # Better visibility
```

#### Cursor

| Style | Recommended |
|-------|-------------|
| **Cursor type** | Vertical bar or Underline |
| **Blinking cursor** | Yes |
| **Smart cursor color** | Yes |

### Window

```
Columns: 120                           # Wide enough for code
Rows: 35                               # Standard height
☐ Hide after opening                   # For hotkey windows only

Style: Normal                          # Or "No Title Bar" for minimal
☑ Show window number                   # For multi-window
```

### Terminal

```
Scrollback lines: 10000               # Or unlimited (-1)
☑ Save lines to scrollback when cleared
☑ Save lines to scrollback in alternate screen mode

Notifications:
☑ Silence bell                        # No annoying sounds
☑ Flash visual bell                   # Subtle notification
☑ Show bell icon in tabs              # See which tab belled
```

### Session

#### Status Bar (Highly Recommended)

```
☑ Status bar enabled
Configure Status Bar → Add components:

Recommended Components:
├── Current Directory      # Show pwd
├── git state             # Show branch, status
├── CPU Utilization       # Monitor system
├── Memory Utilization    # Monitor RAM
├── Clock                 # Current time
└── Search                # Quick search
```

**Status Bar Layout:**

```
┌────────────────────────────────────────────────────────────────────┐
│ 📁 ~/projects/myapp │ 🔀 main ✓ │ CPU: 12% │ RAM: 45% │ 14:32 │ 🔍 │
└────────────────────────────────────────────────────────────────────┘
```

---

## Key Bindings

### Global Hotkeys

```
Settings → Keys → Hotkey

☑ Show/hide all windows with a system-wide hotkey
Hotkey: ⌥Space (or Double-tap ⌥)
```

### Profile Key Mappings

```
Settings → Profiles → Keys → Key Mappings

Presets... → Natural Text Editing     # macOS-like text editing

Additional Mappings:
⌥← : Send Escape Sequence "b"         # Word left
⌥→ : Send Escape Sequence "f"         # Word right
⌘← : Send Hex Code "0x01"             # Line start
⌘→ : Send Hex Code "0x05"             # Line end
⌘⌫ : Send Hex Code "0x15"             # Delete line
```

### Touch Bar (if available)

```
Settings → Keys → Touch Bar

Customize buttons:
├── New Tab
├── Man Page
├── Status (colors)
└── Function Keys
```

---

## Recommended Configurations

### Developer Setup

```
Profile: "Development"
├── Colors: Dracula or One Dark
├── Font: JetBrains Mono 13pt with ligatures
├── Window: 140×40
├── Terminal: Unlimited scrollback
├── Session: Status bar with git, CPU, directory
└── Keys: Natural Text Editing
```

### Minimal Setup

```
Profile: "Minimal"
├── Colors: Custom (dark gray background)
├── Font: SF Mono 12pt
├── Window: No Title Bar style
├── Terminal: 10000 scrollback
├── Session: No status bar
└── Keys: Default
```

### Remote/SSH Setup

```
Profile: "Remote"
├── Colors: Different color scheme (identify remote)
├── Font: Same as local
├── Terminal: Unlimited scrollback
├── Session: Status bar showing hostname
├── General: Custom badge "[SSH]"
└── Triggers: Highlight sudo, error, warning
```

---

## Sync Settings Across Machines

### Option 1: Dotfiles

```bash
# Export preferences
cp ~/Library/Preferences/com.googlecode.iterm2.plist ~/dotfiles/

# On new machine
cp ~/dotfiles/com.googlecode.iterm2.plist ~/Library/Preferences/
```

### Option 2: Cloud Sync

```
Settings → General → Preferences
☑ Load preferences from a custom folder or URL
Folder: ~/Dropbox/iTerm2 (or iCloud, Google Drive)

☑ Save changes to folder when iTerm2 quits
```

### Option 3: Dynamic Profiles

Create JSON files in `~/Library/Application Support/iTerm2/DynamicProfiles/`:

```json
{
  "Profiles": [
    {
      "Name": "Synced Profile",
      "Guid": "unique-guid-here",
      "Dynamic Profile Parent Name": "Default",
      "Normal Font": "JetBrainsMono-Regular 13",
      "Use Bright Bold": true
    }
  ]
}
```

---

## Performance Tuning

### For Slower Machines

```
Settings → General → Magic
☐ GPU Rendering                        # Disable if issues

Settings → Advanced
Drawing: Reduce max FPS
Terminal: Reduce scrollback buffer
```

### For Large Output

```
Settings → Profiles → Terminal
Scrollback lines: 100000              # Increase for logs
☑ Unlimited scrollback                # Use with caution (RAM!)
```

---

## Next Steps

- [Split Panes](../02-features-reference/split-panes.md) - Window layouts
- [Profiles](../02-features-reference/profiles.md) - Advanced profile management
- [Shell Integration](../02-features-reference/shell-integration.md) - Enhanced features

---

## Configuration Checklist

- [ ] Theme/colors configured
- [ ] Font with ligatures set
- [ ] Status bar enabled and configured
- [ ] Natural Text Editing preset applied
- [ ] Hotkey window configured
- [ ] Shell integration installed
- [ ] Settings synced (optional)
