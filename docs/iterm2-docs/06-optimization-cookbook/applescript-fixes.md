# AppleScript Fixes

> Workarounds for common AppleScript + iTerm2 issues.

---

## Safe Heredoc Pattern

```bash
#!/bin/bash
osascript << 'APPLESCRIPT_EOF'
tell application "iTerm2"
    create window with default profile
    delay 0.5
    tell current session of current tab of current window
        set name to "My Session"
        write text "echo 'Hello World'"
    end tell
end tell
APPLESCRIPT_EOF
```

---

## Temp File Pattern

```bash
#!/bin/bash
run_applescript() {
    local script_content="$1"
    local temp_script=$(mktemp /tmp/iterm.XXXXXX.scpt)

    echo "$script_content" > "$temp_script"
    local result=$(osascript "$temp_script" 2>&1)
    local exit_code=$?

    rm -f "$temp_script"

    if [ $exit_code -ne 0 ]; then
        echo "ERROR: $result" >&2
        return $exit_code
    fi

    echo "$result"
}

# Usage
run_applescript '
tell application "iTerm2"
    create window with default profile
end tell
'
```

---

## Error Handling Wrapper

```bash
#!/bin/bash
safe_osascript() {
    local max_retries=3
    local retry=0
    local result=""
    local exit_code=1

    while [ $retry -lt $max_retries ]; do
        result=$(osascript "$@" 2>&1)
        exit_code=$?

        case $exit_code in
            0)
                echo "$result"
                return 0
                ;;
            -600)
                echo "iTerm2 not running, starting..." >&2
                open -a iTerm2
                sleep 2
                ;;
            *)
                echo "Error $exit_code: $result" >&2
                ;;
        esac

        retry=$((retry + 1))
    done

    return 1
}
```

---

## Quote Escaping Function

```bash
escape_for_applescript() {
    local text="$1"
    # Replace ' with '\''
    text="${text//\'/\'\\\'\'}"
    echo "$text"
}

# Usage
SAFE_TEXT=$(escape_for_applescript "Hello 'World'")
osascript -e "display dialog \"$SAFE_TEXT\""
```

---

## Window Stability Pattern

```applescript
tell application "iTerm2"
    activate
    delay 0.5

    set newWindow to (create window with default profile)
    delay 0.5

    set windowID to id of newWindow

    tell window id windowID
        tell current session of current tab
            set name to "Stable Session"
            write text "echo 'Ready'"
        end tell
    end tell
end tell
```

---

## Related Documentation

- [Current Issues](./current-issues.md)
- [Python API Solutions](./python-api-solutions.md)
