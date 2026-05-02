# AppleScript Reference for iTerm2

> Complete AppleScript API reference for iTerm2 (Legacy).

---

## Application Commands

### create window

```applescript
create window with default profile
create window with profile "ProfileName"
```

**Returns:** Reference to new window

### current window

```applescript
tell current window
    -- operations
end tell
```

---

## Window Commands

### Properties

| Property | Type | Access |
|----------|------|--------|
| `id` | integer | read-only |
| `name` | text | read/write |
| `bounds` | rectangle | read/write |
| `position` | point | read/write |
| `frontmost` | boolean | read-only |

### Methods

```applescript
tell window 1
    -- Create new tab
    create tab with default profile
    create tab with profile "Name"

    -- Access tabs
    tell current tab
        -- tab operations
    end tell

    -- Close
    close
end tell
```

### Window Bounds

```applescript
tell current window
    -- Set position and size
    set bounds to {100, 100, 800, 600}

    -- Get bounds
    set windowBounds to bounds
end tell
```

---

## Tab Commands

### Properties

| Property | Type | Access |
|----------|------|--------|
| `current session` | session | read-only |
| `sessions` | list | read-only |
| `index` | integer | read-only |

### Methods

```applescript
tell current tab of current window
    -- Access sessions
    tell current session
        -- session operations
    end tell

    -- Select session
    select session 1

    -- Close
    close
end tell
```

---

## Session Commands

### Properties

| Property | Type | Access |
|----------|------|--------|
| `id` | text | read-only |
| `name` | text | read/write |
| `tty` | text | read-only |
| `profile name` | text | read-only |
| `is at shell prompt` | boolean | read-only |
| `columns` | integer | read-only |
| `rows` | integer | read-only |

### Text Operations

```applescript
tell current session of current tab of current window
    -- Write text (with newline)
    write text "ls -la"

    -- Write text without executing
    write text "partial command" without newline

    -- Write with delay between characters
    write text "slow typing" with delay

    -- Get/set contents
    set contents to text of session
end tell
```

### Session Management

```applescript
tell current session of current tab of current window
    -- Set name
    set name to "My Session"

    -- Split pane
    split vertically with default profile
    split horizontally with profile "Name"

    -- Close
    close
end tell
```

### Profile Operations

```applescript
tell current session of current tab of current window
    -- Get profile
    set currentProfile to profile name

    -- Colors (requires profile change)
    set foreground color to {65535, 65535, 65535}
    set background color to {0, 0, 0}
end tell
```

---

## Full Script Examples

### Multi-Window Setup

```applescript
tell application "iTerm2"
    -- Create first window
    set win1 to (create window with default profile)
    tell win1
        set bounds to {0, 0, 960, 1080}
        tell current session of current tab
            set name to "Editor"
            write text "vim ."
        end tell
    end tell

    -- Create second window
    set win2 to (create window with default profile)
    tell win2
        set bounds to {960, 0, 1920, 1080}
        tell current session of current tab
            set name to "Terminal"
        end tell
    end tell
end tell
```

### Split Layout

```applescript
tell application "iTerm2"
    tell current session of current tab of current window
        -- Split vertically
        set rightPane to (split vertically with default profile)

        -- Name original (left)
        set name to "Left"
        write text "echo 'Left pane'"
    end tell

    -- Configure right pane
    tell second session of current tab of current window
        set name to "Right"
        write text "echo 'Right pane'"
    end tell
end tell
```

### Iterate All Sessions

```applescript
tell application "iTerm2"
    repeat with w in windows
        repeat with t in tabs of w
            repeat with s in sessions of t
                tell s
                    write text "echo 'Session: ' && tty"
                end tell
            end repeat
        end repeat
    end repeat
end tell
```

---

## Error Handling

```applescript
try
    tell application "iTerm2"
        create window with profile "NonExistent"
    end tell
on error errMsg number errNum
    display dialog "Error " & errNum & ": " & errMsg
end try
```

### Common Errors

| Error | Number | Cause |
|-------|--------|-------|
| AppleEvent handler failed | -10000 | Invalid property |
| Syntax error | -2740 | Missing apostrophe |
| Can't get object | -1728 | Invalid reference |
| Application not running | -600 | iTerm2 not open |

---

## Tips

### Delay for Stability

```applescript
tell application "iTerm2"
    create window with default profile
    delay 0.5  -- Wait for window
    tell current session of current tab of current window
        write text "command"
    end tell
end tell
```

### Check if Running

```applescript
if application "iTerm2" is running then
    tell application "iTerm2"
        -- operations
    end tell
else
    display dialog "iTerm2 is not running"
end if
```

---

## Related Documentation

- [AppleScript Legacy](./applescript-legacy.md)
- [Migration Guide](./migration-guide.md)
