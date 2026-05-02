# Variables and Properties

> Storing and managing data in AppleScript.

---

## Variables

### Local Variables (set)

```applescript
set myVar to "Hello"
set myNumber to 42
set myList to {1, 2, 3}
```

### Global Variables

```applescript
global sharedVar
set sharedVar to "Accessible everywhere"
```

---

## Properties

Script-level persistent variables:

```applescript
property myProperty : "Default Value"

on run
    display dialog myProperty
    set myProperty to "New Value"  -- Persists between runs!
end run
```

---

## Scope

| Type | Scope | Persistence |
|------|-------|-------------|
| `set` | Local to handler | None |
| `global` | Entire script | Per run |
| `property` | Script object | Saved to file |

---

## Coercion

```applescript
set num to "42" as number
set str to 42 as text
set lst to "abc" as list  -- {"a", "b", "c"}
```

---

## Related Documentation

- [Language Basics](./language-basics.md)
- [Handlers](./handlers.md)
