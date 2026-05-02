# AppleScript Error Handling

> Managing errors and exceptions in AppleScript.

---

## Try-On Error Block

```applescript
try
    -- Code that might fail
    tell application "NonExistentApp"
        activate
    end tell
on error errMsg number errNum
    -- Handle error
    display dialog "Error " & errNum & ": " & errMsg
end try
```

---

## Error Information

| Variable | Content |
|----------|---------|
| `errMsg` | Error message text |
| `errNum` | Error number |
| `errFrom` | Object that caused error |
| `errTo` | Expected type/class |

```applescript
try
    set x to "abc" as number
on error errMsg number errNum from errFrom to errTo
    log "Message: " & errMsg
    log "Number: " & errNum
    log "From: " & errFrom
    log "To: " & errTo
end try
```

---

## Common Error Numbers

| Number | Description |
|--------|-------------|
| -10000 | Apple Event handler failed |
| -2740 | Syntax error |
| -1728 | Can't get object |
| -1700 | Can't make into type |
| -600 | Application not running |
| -128 | User canceled |
| -43 | File not found |
| -50 | Parameter error |

---

## Throwing Errors

```applescript
-- Simple error
error "Something went wrong"

-- With number
error "Invalid input" number 501

-- Full error
error "File not found" number -43 from "myfile.txt"
```

---

## Patterns

### Retry Pattern

```applescript
set maxRetries to 3
set retryCount to 0

repeat
    try
        -- Attempt operation
        tell application "iTerm2"
            create window with default profile
        end tell
        exit repeat -- Success, exit loop

    on error errMsg number errNum
        set retryCount to retryCount + 1
        if retryCount >= maxRetries then
            error "Failed after " & maxRetries & " attempts: " & errMsg
        end if
        delay 1 -- Wait before retry
    end try
end repeat
```

### Default Value Pattern

```applescript
try
    set result to some risky operation
on error
    set result to "default value"
end try
```

---

## Related Documentation

- [Language Basics](./language-basics.md)
- [Gotchas Reference](./gotchas-reference.md)
