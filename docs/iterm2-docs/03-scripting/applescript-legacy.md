# AppleScript for iTerm2 (Legacy)

> ⚠️ **DEPRECATED**: AppleScript support is maintained for backward compatibility only. Use Python API for new projects.

---

## Status

| Aspect | Status |
|--------|--------|
| **Official Status** | Deprecated |
| **New Features** | None planned |
| **Bug Fixes** | Critical only |
| **Recommendation** | Migrate to Python API |

---

## Basic Syntax

### Create Window

```applescript
tell application "iTerm2"
    create window with default profile
end tell
```

### Create with Profile

```applescript
tell application "iTerm2"
    create window with profile "Development"
end tell
```

### Access Current Session

```applescript
tell application "iTerm2"
    tell current session of current tab of current window
        -- Commands here
    end tell
end tell
```

---

## Common Operations

### Send Text

```applescript
tell application "iTerm2"
    tell current session of current tab of current window
        write text "echo 'Hello World'"
    end tell
end tell
```

### Set Session Name

```applescript
tell application "iTerm2"
    tell current session of current tab of current window
        set name to "My Session"
    end tell
end tell
```

### Split Pane

```applescript
tell application "iTerm2"
    tell current session of current tab of current window
        split vertically with default profile
        -- or
        split horizontally with default profile
    end tell
end tell
```

### Create Tab

```applescript
tell application "iTerm2"
    tell current window
        create tab with default profile
    end tell
end tell
```

---

## Known Issues

### Tab Title Trap (Error -10000)

**Problem:** Cannot set tab title directly.

```applescript
-- ❌ THIS FAILS
tell current tab of current window
    set title to "My Title"  -- Error -10000!
end tell
```

**Solution:** Set session name instead (tab updates automatically).

```applescript
-- ✅ THIS WORKS
tell current session of current tab of current window
    set name to "My Title"
end tell
```

### Apostrophe Issues (Error -2740)

**Problem:** Missing apostrophe in `AppleScript's`.

```applescript
-- ❌ WRONG
set AppleScripts text item delimiters to ","

-- ✅ CORRECT
set AppleScript's text item delimiters to ","
```

### Quote Escaping

**Problem:** Bash + AppleScript quote collision.

```bash
# ❌ FAILS - quote hell
osascript -e 'tell app "iTerm2" to write text "echo 'hello'"'

# ✅ WORKS - heredoc
osascript << 'EOF'
tell application "iTerm2"
    tell current session of current tab of current window
        write text "echo 'hello'"
    end tell
end tell
EOF

# ✅ WORKS - temp file
echo 'tell application "iTerm2"
    tell current session of current tab of current window
        write text "echo '"'"'hello'"'"'"
    end tell
end tell' > /tmp/script.scpt
osascript /tmp/script.scpt
rm /tmp/script.scpt
```

---

## Object Model

```
Application
    └── Windows (every window)
            └── Tabs (every tab)
                    └── Sessions (every session)
```

### Properties

| Object | Properties |
|--------|------------|
| **Window** | id, name, bounds |
| **Tab** | sessions, current session |
| **Session** | id, name, tty, profile name |

---

## Running from Bash

### Inline

```bash
osascript -e 'tell application "iTerm2" to create window with default profile'
```

### Heredoc (Recommended)

```bash
osascript << 'APPLESCRIPT'
tell application "iTerm2"
    create window with default profile
    tell current session of current tab of current window
        write text "ls -la"
    end tell
end tell
APPLESCRIPT
```

### File

```bash
osascript /path/to/script.scpt
```

---

## Limitations vs Python API

| Feature | AppleScript | Python API |
|---------|-------------|------------|
| Event subscription | ❌ | ✅ |
| Async operations | ❌ | ✅ |
| Status bar components | ❌ | ✅ |
| Variable monitoring | ❌ | ✅ |
| Error handling | Basic | Full |
| Active development | ❌ | ✅ |

---

## Migration Recommendation

For any new automation:
1. **Use Python API** - Modern, supported, full-featured
2. **See [Migration Guide](./migration-guide.md)** - Step-by-step conversion

For existing AppleScript:
1. **Evaluate complexity** - Simple scripts may stay
2. **Plan migration** - Complex automation should migrate
3. **Apply fixes** - Use documented workarounds

---

## Related Documentation

- [Migration Guide](./migration-guide.md) - Convert to Python
- [Python API Guide](./python-api-guide.md) - Modern approach
- [AppleScript Reference](./applescript-reference.md) - Detailed reference
