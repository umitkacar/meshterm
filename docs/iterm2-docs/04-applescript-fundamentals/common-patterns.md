# Common AppleScript Patterns

> Reusable patterns for AppleScript automation.

---

## Application Control

### Launch and Activate

```applescript
tell application "AppName"
    activate
end tell
```

### Check if Running

```applescript
if application "AppName" is running then
    -- do something
end if
```

### Quit Application

```applescript
tell application "AppName"
    quit
end tell
```

---

## File Operations

### Choose File

```applescript
set chosenFile to choose file with prompt "Select a file:"
```

### Read File

```applescript
set fileContent to read file "Macintosh HD:Users:name:file.txt"
```

### Write File

```applescript
set filePath to (path to desktop as text) & "output.txt"
set fileRef to open for access file filePath with write permission
write "Content" to fileRef
close access fileRef
```

---

## User Interaction

### Display Dialog

```applescript
display dialog "Message" buttons {"Cancel", "OK"} default button "OK"
```

### With Text Input

```applescript
set response to display dialog "Enter name:" default answer ""
set userName to text returned of response
```

### Notification

```applescript
display notification "Done!" with title "Script Complete"
```

---

## String Processing

### Split String

```applescript
set oldDelims to AppleScript's text item delimiters
set AppleScript's text item delimiters to ","
set parts to text items of "a,b,c"
set AppleScript's text item delimiters to oldDelims
```

### Join List

```applescript
set oldDelims to AppleScript's text item delimiters
set AppleScript's text item delimiters to "-"
set result to myList as text
set AppleScript's text item delimiters to oldDelims
```

---

## Related Documentation

- [Language Basics](./language-basics.md)
- [Handlers](./handlers.md)
