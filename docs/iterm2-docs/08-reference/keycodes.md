# Key Codes Reference

> Common key codes for scripting and automation.

---

## Modifier Keys

| Key | Symbol | AppleScript | Hex |
|-----|--------|-------------|-----|
| Command | ⌘ | `command down` | - |
| Option | ⌥ | `option down` | - |
| Control | ⌃ | `control down` | - |
| Shift | ⇧ | `shift down` | - |

---

## Special Keys (AppleScript)

```applescript
tell application "System Events"
    key code 36  -- Return
    key code 48  -- Tab
    key code 51  -- Delete (Backspace)
    key code 53  -- Escape
    key code 123 -- Left Arrow
    key code 124 -- Right Arrow
    key code 125 -- Down Arrow
    key code 126 -- Up Arrow
    key code 116 -- Page Up
    key code 121 -- Page Down
    key code 115 -- Home
    key code 119 -- End
end tell
```

---

## Terminal Control Characters

| Char | Hex | Purpose |
|------|-----|---------|
| Ctrl+C | 0x03 | Interrupt |
| Ctrl+D | 0x04 | EOF |
| Ctrl+Z | 0x1A | Suspend |
| Ctrl+L | 0x0C | Clear |
| Ctrl+A | 0x01 | Line start |
| Ctrl+E | 0x05 | Line end |
| Ctrl+U | 0x15 | Clear line |
| Ctrl+K | 0x0B | Kill to end |

---

## Send Hex Code Example

```applescript
tell application "System Events"
    -- Send Ctrl+C
    keystroke "c" using control down
end tell
```

---

## Related Documentation

- [Quick Reference](./quick-reference.md)
