# GUI Scripting with System Events

> Control applications without native AppleScript support.

---

## Overview

GUI scripting simulates user interaction (clicks, keystrokes) via System Events.

---

## Enable Accessibility

```
System Settings → Privacy & Security → Accessibility
→ Add Script Editor (or your app)
```

---

## Basic Operations

### Click Button

```applescript
tell application "System Events"
    tell process "AppName"
        click button "OK" of window 1
    end tell
end tell
```

### Menu Items

```applescript
tell application "System Events"
    tell process "AppName"
        click menu item "Copy" of menu "Edit" of menu bar 1
    end tell
end tell
```

### Keystrokes

```applescript
tell application "System Events"
    keystroke "Hello World"
    keystroke "v" using command down  -- Paste
    key code 36  -- Return key
end tell
```

---

## UI Element Hierarchy

```
Application
└── Window
    ├── Button
    ├── Text Field
    ├── Pop Up Button
    └── Group
        └── More elements...
```

### Inspect Elements

```applescript
tell application "System Events"
    tell process "AppName"
        entire contents of window 1
    end tell
end tell
```

---

## Common Patterns

### Wait for Window

```applescript
tell application "System Events"
    repeat until exists window 1 of process "AppName"
        delay 0.1
    end repeat
end tell
```

### Click by Position

```applescript
tell application "System Events"
    click at {100, 200}
end tell
```

---

## Related Documentation

- [Language Basics](./language-basics.md)
- [Common Patterns](./common-patterns.md)
