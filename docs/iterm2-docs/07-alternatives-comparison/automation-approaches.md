# Automation Approaches Comparison

> Comparing ways to automate terminal operations on macOS.

---

## Approaches Overview

| Approach | Type | iTerm2 Support | Learning |
|----------|------|----------------|----------|
| **Python API** | Native | ✅ Full | Medium |
| **AppleScript** | System | ⚠️ Deprecated | Low |
| **JXA** | System | ⚠️ Deprecated | Medium |
| **osascript** | CLI | ⚠️ Bridge | Low |
| **Hammerspoon** | Third-party | Via AppleScript | Medium |
| **Keyboard Maestro** | Third-party | Via AppleScript | Low |
| **Shortcuts.app** | System | Via AppleScript | Low |

---

## Feature Matrix

| Feature | Python API | AppleScript | JXA |
|---------|------------|-------------|-----|
| **Async** | ✅ | ❌ | ❌ |
| **Events** | ✅ | ❌ | ❌ |
| **Status Bar** | ✅ | ❌ | ❌ |
| **Error Handling** | ✅ Full | ⚠️ Basic | ⚠️ Basic |
| **Quote Issues** | ❌ None | ✅ Yes | ⚠️ Some |
| **Active Dev** | ✅ | ❌ | ❌ |

---

## Code Comparison

### Create Window

**Python API:**
```python
window = await iterm2.Window.async_create(connection)
```

**AppleScript:**
```applescript
tell application "iTerm2"
    create window with default profile
end tell
```

**JXA:**
```javascript
Application("iTerm2").createWindow()
```

---

## Recommendations

| Scenario | Best Approach |
|----------|---------------|
| New iTerm2 automation | Python API |
| Quick one-off command | osascript |
| macOS Shortcuts integration | AppleScript |
| Cross-app automation | Hammerspoon |
| Complex workflows | Python API |

---

## Related Documentation

- [Python API Guide](../03-scripting/python-api-guide.md)
- [AppleScript Legacy](../03-scripting/applescript-legacy.md)
- [When to Use What](./when-to-use-what.md)
