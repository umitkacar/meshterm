# Performance Tips

> Optimize iTerm2 automation scripts.

---

## Python API Tips

### 1. Batch Operations with Transactions

```python
async def batch_operations(connection):
    # Operations within transaction are atomic
    async with iterm2.Transaction(connection):
        window = await iterm2.Window.async_create(connection)
        tab = await window.async_create_tab()
        session = tab.current_session
        await session.async_set_name("Batch Created")
```

### 2. Minimize API Calls

```python
# ❌ Inefficient - multiple API calls
async def slow_approach(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_window
    tab = window.current_tab
    session = tab.current_session
    name = await session.async_get_variable("name")
    path = await session.async_get_variable("path")

# ✅ Better - cache references
async def fast_approach(connection):
    app = await iterm2.async_get_app(connection)
    session = app.current_window.current_tab.current_session
    # Get multiple variables if needed
```

### 3. Async Parallelism

```python
import asyncio

async def parallel_windows(connection):
    # Create windows in parallel
    tasks = [
        iterm2.Window.async_create(connection),
        iterm2.Window.async_create(connection),
        iterm2.Window.async_create(connection),
    ]
    windows = await asyncio.gather(*tasks)
    return windows
```

---

## AppleScript Tips

### 1. Minimize tell Blocks

```applescript
-- ❌ Nested tells
tell application "iTerm2"
    tell current window
        tell current tab
            tell current session
                write text "command"
            end tell
        end tell
    end tell
end tell

-- ✅ Flattened
tell application "iTerm2"
    tell current session of current tab of current window
        write text "command"
    end tell
end tell
```

### 2. Use Window IDs

```applescript
-- ❌ May target wrong window after delay
tell application "iTerm2"
    create window with default profile
    delay 0.5
    tell current window  -- Might not be our new window!
        -- ...
    end tell
end tell

-- ✅ Store window reference
tell application "iTerm2"
    set newWindow to (create window with default profile)
    delay 0.5
    tell newWindow
        -- Definitely our window
    end tell
end tell
```

### 3. Reduce Delays

```applescript
-- Only delay when necessary
tell application "iTerm2"
    set win to (create window with default profile)
    -- Only delay if next operation depends on window being ready
    delay 0.3  -- Minimal delay
    tell win
        tell current session of current tab
            write text "fast"
        end tell
    end tell
end tell
```

---

## Bash Integration Tips

### 1. Use Python over osascript

```bash
# ❌ Slow - osascript startup overhead
osascript << 'EOF'
tell application "iTerm2"
    -- ...
end tell
EOF

# ✅ Faster for multiple operations
python3 << 'EOF'
import iterm2

async def main(connection):
    # Multiple operations, single connection
    pass

iterm2.run_until_complete(main)
EOF
```

### 2. Single Script for Multiple Operations

```bash
# ❌ Multiple osascript calls
osascript -e 'tell app "iTerm2" to create window'
osascript -e 'tell app "iTerm2" to write text "cmd1"'
osascript -e 'tell app "iTerm2" to write text "cmd2"'

# ✅ Single script
osascript << 'EOF'
tell application "iTerm2"
    create window with default profile
    tell current session of current tab of current window
        write text "cmd1"
        write text "cmd2"
    end tell
end tell
EOF
```

---

## Memory Considerations

### 1. Long-Running Scripts

```python
# Close references when done
async def long_running(connection):
    while True:
        # Do work
        await asyncio.sleep(60)
        # Don't hold references to closed windows
```

### 2. Large Output

For scripts that generate lots of output:
- Increase scrollback buffer
- Or periodically clear: `await session.async_send_text("clear\n")`

---

## Related Documentation

- [Python API Guide](../03-scripting/python-api-guide.md)
- [Helper Library](./helper-library.md)
