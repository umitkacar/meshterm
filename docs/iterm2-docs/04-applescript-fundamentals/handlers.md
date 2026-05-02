# AppleScript Handlers

> Functions and subroutines in AppleScript.

---

## Basic Handler

```applescript
on myHandler()
    display dialog "Hello"
end myHandler

-- Call it
myHandler()
```

## With Parameters

```applescript
on greet(name)
    return "Hello, " & name
end greet

set result to greet("World")
```

## Multiple Parameters

```applescript
on addNumbers(a, b)
    return a + b
end addNumbers

on formatName(firstName, lastName)
    return lastName & ", " & firstName
end formatName
```

## Labeled Parameters

```applescript
on moveFile from sourcePath to destPath
    -- use sourcePath and destPath
end moveFile

moveFile from "/path/source" to "/path/dest"
```

## Return Values

```applescript
on calculateSum(numbers)
    set total to 0
    repeat with n in numbers
        set total to total + n
    end repeat
    return total
end calculateSum
```

## Script Objects

```applescript
script MyObject
    property name : "Default"

    on sayHello()
        return "Hello, I am " & name
    end sayHello
end script

set MyObject's name to "Test"
MyObject's sayHello()
```

---

## Related Documentation

- [Language Basics](./language-basics.md)
- [Variables and Properties](./variables-properties.md)
