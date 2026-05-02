# AppleScript Gotchas Reference

> Common pitfalls and how to avoid them.

---

## The Big Three (iTerm2 Specific)

### 1. Tab Title Trap (Error -10000)

**Problem:**
```applescript
-- ❌ THIS FAILS
tell current tab of current window
    set title to "My Title"  -- Error -10000!
end tell
```

**Solution:**
```applescript
-- ✅ THIS WORKS
tell current session of current tab of current window
    set name to "My Title"  -- Tab updates automatically
end tell
```

**Why:** Tabs don't have a settable `title` property. Session `name` propagates to tab.

---

### 2. Apostrophe Catastrophe (Error -2740)

**Problem:**
```applescript
-- ❌ WRONG - Missing apostrophe
set AppleScripts text item delimiters to ","

-- ❌ WRONG - Wrong character
set AppleScript's text item delimiters to ","  -- Smart quote!
```

**Solution:**
```applescript
-- ✅ CORRECT
set AppleScript's text item delimiters to ","
```

**Why:** `AppleScript's` is possessive form. Must use straight apostrophe.

---

### 3. Quote Hell (Bash Integration)

**Problem:**
```bash
# ❌ FAILS - Nested quotes
osascript -e 'tell app "iTerm2" to write text "echo 'hello'"'
```

**Solutions:**

```bash
# ✅ Solution 1: Heredoc
osascript << 'EOF'
tell application "iTerm2"
    tell current session of current tab of current window
        write text "echo 'hello'"
    end tell
end tell
EOF

# ✅ Solution 2: Temp file
cat > /tmp/script.scpt << 'EOF'
tell application "iTerm2"
    tell current session of current tab of current window
        write text "echo 'hello'"
    end tell
end tell
EOF
osascript /tmp/script.scpt
rm /tmp/script.scpt

# ✅ Solution 3: Escape sequence
osascript -e 'tell application "iTerm2" to tell current session of current tab of current window to write text "echo '"'"'hello'"'"'"'
```

---

## Other Common Gotchas

### 4. Application Name Case

```applescript
-- ❌ Wrong case
tell application "iterm2"  -- May fail

-- ✅ Exact case
tell application "iTerm2"
```

### 5. Missing Delay After Window Creation

```applescript
-- ❌ May fail - window not ready
tell application "iTerm2"
    create window with default profile
    tell current session of current tab of current window
        write text "command"  -- May target wrong window!
    end tell
end tell

-- ✅ Add delay
tell application "iTerm2"
    create window with default profile
    delay 0.5
    tell current session of current tab of current window
        write text "command"
    end tell
end tell
```

### 6. List Index Starting at 1

```applescript
set myList to {"a", "b", "c"}

-- ❌ Python habit
set first to item 0 of myList  -- Error!

-- ✅ AppleScript starts at 1
set first to item 1 of myList
```

### 7. Copy vs Set for Lists

```applescript
set originalList to {1, 2, 3}

-- ❌ This creates a reference
set newList to originalList
set item 1 of newList to 99
-- originalList is now {99, 2, 3}!

-- ✅ This creates a copy
copy originalList to newList
set item 1 of newList to 99
-- originalList is still {1, 2, 3}
```

### 8. Text Item Delimiters Scope

```applescript
-- ❌ Forgot to restore
set AppleScript's text item delimiters to ","
set parts to text items of "a,b,c"
-- Delimiters still "," for rest of script!

-- ✅ Save and restore
set oldDelims to AppleScript's text item delimiters
set AppleScript's text item delimiters to ","
set parts to text items of "a,b,c"
set AppleScript's text item delimiters to oldDelims
```

### 9. Unicode in osascript

```bash
# ❌ May have encoding issues
osascript -e 'display dialog "日本語"'

# ✅ Use heredoc or file
osascript << 'EOF'
display dialog "日本語"
EOF
```

### 10. Timeout Issues

```applescript
-- Default timeout is 2 minutes
-- For long operations:
with timeout of 600 seconds
    tell application "SomeApp"
        -- long operation
    end tell
end timeout
```

---

## Quick Reference Card

| Gotcha | Symptom | Fix |
|--------|---------|-----|
| Tab title | -10000 | Use session name |
| Apostrophe | -2740 | Add `'s` |
| Quotes | Syntax error | Heredoc or temp file |
| App name | Not found | Check exact case |
| No delay | Wrong target | Add `delay 0.5` |
| Index 0 | Error | Start at 1 |
| List copy | Mutation | Use `copy` |
| Delimiters | Side effects | Save/restore |
| Unicode | Garbled | Use heredoc |
| Timeout | Hangs | `with timeout` |

---

## Related Documentation

- [Error Handling](./error-handling.md)
- [AppleScript Legacy](../03-scripting/applescript-legacy.md)
- [Migration Guide](../03-scripting/migration-guide.md)
