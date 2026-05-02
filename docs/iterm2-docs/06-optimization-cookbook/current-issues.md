# Current Issues Reference

> Known issues from RAMAS APPLESCRIPT-ITERM2-COOKBOOK and their solutions.

---

## The Big Three

### 1. Tab Title Trap (Error -10000)

**Symptom:**
```
error "iTerm2 got an error: Can't set title of tab..." number -10000
```

**Cause:** Tab objects don't have a settable `title` property.

**AppleScript Fix:**
```applescript
-- ❌ FAILS
tell current tab of current window
    set title to "My Title"
end tell

-- ✅ WORKS
tell current session of current tab of current window
    set name to "My Title"  -- Session name propagates to tab
end tell
```

**Python API (No Issue):**
```python
await session.async_set_name("My Title")  # Just works
```

---

### 2. Apostrophe Catastrophe (Error -2740)

**Symptom:**
```
Syntax Error: Expected expression but found unknown token.
```

**Cause:** Missing `'s` in `AppleScript's`.

**Fix:**
```applescript
-- ❌ WRONG
set AppleScripts text item delimiters to ","

-- ✅ CORRECT
set AppleScript's text item delimiters to ","
```

**Python API (No Issue):** String handling is straightforward.

---

### 3. Quote Hell (Bash + AppleScript)

**Symptom:** Various syntax errors when embedding quotes.

**Solutions:**

| Approach | Complexity | Reliability |
|----------|------------|-------------|
| Heredoc | Low | High |
| Temp file | Medium | Highest |
| Escape sequence | High | Medium |
| **Python API** | Low | Highest |

**Recommended:** Migrate to Python API.

---

## Additional Issues

### 4. Race Conditions

**Symptom:** Commands target wrong window/session.

**Cause:** No delay after window creation.

**Fix:**
```applescript
create window with default profile
delay 0.5  -- Wait for window to be ready
tell current session of current tab of current window
    write text "command"
end tell
```

---

### 5. Window/Session ID Confusion

**Symptom:** Error -1728 (Can't get object).

**Cause:** Window/session IDs change between operations.

**Fix:** Re-query objects after each major operation.

---

## Migration Recommendation

| Issue | AppleScript Fix | Python API Status |
|-------|-----------------|-------------------|
| Tab Title | Use session.name | ✅ No issue |
| Apostrophe | Add 's | ✅ No issue |
| Quote Hell | Heredoc/temp file | ✅ No issue |
| Race Conditions | Add delays | ✅ Better handling |
| ID Confusion | Re-query | ✅ Object references |

**Conclusion:** Python API eliminates most AppleScript issues.

---

## Related Documentation

- [AppleScript Fixes](./applescript-fixes.md)
- [Python API Solutions](./python-api-solutions.md)
- [Migration Guide](../03-scripting/migration-guide.md)
