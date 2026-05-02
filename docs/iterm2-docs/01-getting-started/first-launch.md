# First Launch Guide

> Essential steps to configure iTerm2 after your first launch.

---

## Table of Contents

- [Initial Setup Wizard](#initial-setup-wizard)
- [Understanding the Interface](#understanding-the-interface)
- [Essential Keyboard Shortcuts](#essential-keyboard-shortcuts)
- [Creating Your First Profile](#creating-your-first-profile)
- [Quick Customizations](#quick-customizations)

---

## Initial Setup Wizard

When you first launch iTerm2, you may see prompts for:

### 1. Check for Updates
```
"Check for updates automatically?"
→ Recommended: Yes
```

### 2. Shell Integration
```
"Install Shell Integration?"
→ Recommended: Yes (enables command tracking, directory history)
```

### 3. Default Terminal
```
"Make iTerm2 the default terminal?"
→ Recommended: Yes
```

---

## Understanding the Interface

```
┌─────────────────────────────────────────────────────────────────────┐
│ [×][−][+]  Tab 1  │  Tab 2  │  +                              ⚙️   │ ← Tab Bar
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  user@hostname ~ $                                                  │ ← Session
│  █                                                                  │   (Terminal)
│                                                                     │
│                                                                     │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│ [Status Bar - optional]                                             │ ← Status Bar
└─────────────────────────────────────────────────────────────────────┘
```

### Key UI Elements

| Element | Description | Shortcut |
|---------|-------------|----------|
| **Tab Bar** | Contains all tabs in window | ⌘T (new tab) |
| **Session** | Terminal instance | ⌘N (new window) |
| **Split Panes** | Divide session | ⌘D (vertical), ⌘⇧D (horizontal) |
| **Status Bar** | Customizable info bar | Settings → Profiles → Session |
| **Toolbelt** | Side panel with tools | ⌘⇧B |

---

## Essential Keyboard Shortcuts

### Navigation

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
| Split Vertically | `⌘D` |
| Split Horizontally | `⌘⇧D` |
| Navigate Panes | `⌘⌥↑↓←→` |
| Maximize Pane | `⌘⇧↩` |
| Close Pane | `⌘W` |

### Search & Edit

| Action | Shortcut |
|--------|----------|
| Find | `⌘F` |
| Find Next | `⌘G` |
| Clear Buffer | `⌘K` |
| Clear to Start | `⌃U` |
| Copy Mode | `⌘⇧C` |

### Productivity

| Action | Shortcut |
|--------|----------|
| Autocomplete | `⌘;` |
| Paste History | `⌘⇧H` |
| Command History | `⌘⇧;` |
| Recent Directories | `⌘⌥/` |
| Open URL/File | `⌘-click` |

---

## Creating Your First Profile

Profiles store appearance and behavior settings. Let's create a custom profile:

### Step 1: Open Profile Settings

```
iTerm2 → Settings (⌘,) → Profiles
```

### Step 2: Create New Profile

1. Click `+` at bottom left
2. Name it (e.g., "Development")
3. Configure settings below

### Step 3: Essential Profile Settings

#### Colors Tab
```
Color Presets... → Select a theme
Recommended: Solarized Dark, Dracula, One Dark
```

#### Text Tab
```
Font: Select a coding font
Recommended:
- JetBrains Mono (ligatures)
- Fira Code (ligatures)
- SF Mono (Apple default)
- Menlo (classic)

Size: 13-14pt recommended
```

#### Window Tab
```
Columns: 120
Rows: 35
Style: Normal (or No Title Bar for minimal look)
```

#### Terminal Tab
```
Scrollback Lines: 10000 (or unlimited)
```

#### Session Tab
```
Status bar enabled: ✓
Configure Status Bar: Add components
```

### Step 4: Set as Default

```
Profiles → [Your Profile] → Other Actions → Set as Default
```

---

## Quick Customizations

### Theme Setup (5 seconds)

```
Settings → Profiles → Colors → Color Presets... → [Choose Theme]
```

Popular themes:
- **Solarized Dark** - Easy on eyes, high contrast
- **Dracula** - Purple-themed, modern
- **One Dark** - Atom-inspired
- **Nord** - Blue-tinted, calm
- **Gruvbox** - Retro, warm colors

### Font with Ligatures

```bash
# Install coding fonts via Homebrew
brew tap homebrew/cask-fonts
brew install --cask font-jetbrains-mono
brew install --cask font-fira-code
brew install --cask font-hack-nerd-font
```

Then in Settings:
```
Profiles → Text → Font → JetBrains Mono
☑ Use ligatures
```

### Natural Text Editing

Enable macOS-like text navigation:

```
Settings → Profiles → Keys → Key Mappings → Presets... → Natural Text Editing
```

This enables:
- `⌥←` / `⌥→` - Move by word
- `⌘←` / `⌘→` - Move to line start/end
- `⌥⌫` - Delete word

### Hotkey Window (Quake-style)

Create a system-wide dropdown terminal:

```
Settings → Keys → Hotkey → Create a Dedicated Hotkey Window
Hotkey: Double-tap ⌥ (or custom key)
```

---

## Verification Checklist

After setup, verify these work:

- [ ] New tab opens with custom profile
- [ ] Split panes work (`⌘D`, `⌘⇧D`)
- [ ] Theme/colors look correct
- [ ] Font renders properly (check ligatures: `->` `=>` `!=`)
- [ ] Shell integration marks appear (blue/green triangles)
- [ ] Hotkey window appears (if configured)
- [ ] Autocomplete works (`⌘;`)

---

## Next Steps

- [Basic Configuration](basic-configuration.md) - Advanced settings
- [Split Panes](../02-features-reference/split-panes.md) - Master window layouts
- [Profiles](../02-features-reference/profiles.md) - Profile management

---

## Quick Reference Card

```
╔═══════════════════════════════════════════════════════════╗
║                 iTerm2 ESSENTIAL SHORTCUTS                 ║
╠═══════════════════════════════════════════════════════════╣
║  ⌘N     New Window     │  ⌘D     Split Vertical          ║
║  ⌘T     New Tab        │  ⌘⇧D    Split Horizontal        ║
║  ⌘W     Close          │  ⌘⌥↑↓←→ Navigate Panes          ║
║  ⌘←→    Switch Tabs    │  ⌘⇧↩    Maximize Pane           ║
╠═══════════════════════════════════════════════════════════╣
║  ⌘;     Autocomplete   │  ⌘F     Find                    ║
║  ⌘⇧H    Paste History  │  ⌘K     Clear Buffer            ║
║  ⌘⇧C    Copy Mode      │  ⌘,     Settings                ║
╚═══════════════════════════════════════════════════════════╝
```
