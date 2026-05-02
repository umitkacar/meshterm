# Error Codes Reference

> Common AppleScript and Python API error codes.

---

## AppleScript Errors

| Code | Name | Cause | Solution |
|------|------|-------|----------|
| **-10000** | AppleEvent handler failed | Invalid property (tab.title) | Use session.name |
| **-2740** | Syntax error | Missing `'s` | Add apostrophe |
| **-1728** | Can't get object | Invalid reference | Re-query object |
| **-1700** | Can't make into type | Type coercion failed | Check data types |
| **-600** | Application not running | iTerm2 closed | Start iTerm2 |
| **-128** | User canceled | Dialog canceled | Handle cancellation |
| **-43** | File not found | Path doesn't exist | Check path |
| **-50** | Parameter error | Bad parameter | Check arguments |

---

## Python API Exceptions

| Exception | Cause | Solution |
|-----------|-------|----------|
| `AppNotRunningError` | iTerm2 not running | Start iTerm2 |
| `RPCError` | API communication failed | Check connection |
| `ProfileNotFoundError` | Profile doesn't exist | Verify profile name |
| `SessionNotFoundError` | Session closed | Re-query session |
| `WindowNotFoundError` | Window closed | Re-query window |

---

## Error Handling Example

### AppleScript

```applescript
try
    tell application "iTerm2"
        create window with profile "NonExistent"
    end tell
on error errMsg number errNum
    if errNum = -10000 then
        log "Invalid property"
    else if errNum = -600 then
        log "iTerm2 not running"
    else
        log "Error " & errNum & ": " & errMsg
    end if
end try
```

### Python API

```python
try:
    window = await iterm2.Window.async_create(connection)
except iterm2.AppNotRunningError:
    print("iTerm2 is not running")
except iterm2.RPCError as e:
    print(f"RPC Error: {e}")
```

---

## Related Documentation

- [Gotchas Reference](../04-applescript-fundamentals/gotchas-reference.md)
- [Current Issues](../06-optimization-cookbook/current-issues.md)
