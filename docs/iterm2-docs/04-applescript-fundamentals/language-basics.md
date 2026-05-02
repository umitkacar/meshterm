# AppleScript Language Basics

> Core syntax and concepts for AppleScript programming.

---

## Overview

AppleScript is Apple's English-like scripting language for macOS automation. It controls applications via Apple Events.

---

## Basic Syntax

### Comments

```applescript
-- Single line comment

(*
   Multi-line
   comment
*)

# Hash comment (also works)
```

### Tell Blocks

```applescript
-- Target an application
tell application "Finder"
    -- commands for Finder
end tell

-- Nested tells
tell application "iTerm2"
    tell current window
        tell current tab
            -- commands
        end tell
    end tell
end tell
```

### Variables

```applescript
-- Set variable
set myVariable to "Hello"
set myNumber to 42
set myList to {1, 2, 3}

-- Copy (for mutable types)
copy myList to newList
```

---

## Data Types

| Type | Example |
|------|---------|
| **Text/String** | `"Hello World"` |
| **Integer** | `42` |
| **Real** | `3.14` |
| **Boolean** | `true`, `false` |
| **List** | `{1, 2, 3}` |
| **Record** | `{name:"John", age:30}` |
| **Date** | `current date` |

### String Operations

```applescript
set str to "Hello World"

-- Concatenation
set result to str & " More text"

-- Length
set len to length of str

-- Character access
set firstChar to character 1 of str
set lastChar to character -1 of str

-- Substring
set sub to characters 1 thru 5 of str as text
```

### List Operations

```applescript
set myList to {1, 2, 3, 4, 5}

-- Access item
set first to item 1 of myList
set last to item -1 of myList

-- Add item
set end of myList to 6

-- Count
set count to count of myList

-- Contains
if myList contains 3 then
    -- do something
end if
```

---

## Control Flow

### If Statement

```applescript
if condition then
    -- code
end if

if condition then
    -- code
else
    -- alternative
end if

if x > 10 then
    -- code
else if x > 5 then
    -- code
else
    -- code
end if
```

### Repeat Loops

```applescript
-- Fixed count
repeat 5 times
    -- code
end repeat

-- While condition
repeat while condition
    -- code
end repeat

-- Until condition
repeat until condition
    -- code
end repeat

-- With variable
repeat with i from 1 to 10
    log i
end repeat

-- Over list
repeat with item in myList
    log item
end repeat
```

---

## Operators

### Comparison

| Operator | Meaning |
|----------|---------|
| `=`, `is` | Equal |
| `≠`, `is not` | Not equal |
| `>` | Greater than |
| `<` | Less than |
| `≥`, `>=` | Greater or equal |
| `≤`, `<=` | Less or equal |

### Logical

| Operator | Meaning |
|----------|---------|
| `and` | Logical AND |
| `or` | Logical OR |
| `not` | Logical NOT |

### String

| Operator | Meaning |
|----------|---------|
| `&` | Concatenate |
| `contains` | Contains substring |
| `starts with` | Starts with |
| `ends with` | Ends with |

---

## Error Handling

```applescript
try
    -- risky code
    set x to 1 / 0
on error errMsg number errNum
    display dialog "Error " & errNum & ": " & errMsg
end try

-- Throw error
error "Something went wrong" number 500
```

---

## Handlers (Functions)

```applescript
-- Define handler
on sayHello(name)
    return "Hello, " & name
end sayHello

-- Call handler
set greeting to sayHello("World")

-- With multiple parameters
on addNumbers(a, b)
    return a + b
end addNumbers

set result to addNumbers(5, 3)
```

---

## Running Scripts

### Script Editor

1. Open `/Applications/Utilities/Script Editor.app`
2. Write script
3. Press Run (⌘R)

### Command Line

```bash
# Run script file
osascript script.scpt

# Run inline
osascript -e 'display dialog "Hello"'
```

---

## Related Documentation

- [Variables and Properties](./variables-properties.md)
- [Handlers](./handlers.md)
- [Error Handling](./error-handling.md)
