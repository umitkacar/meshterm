# Escape Sequences Reference

> iTerm2 proprietary escape sequences.

---

## Image Display

```
ESC ] 1337 ; File = [args] : base64-data BEL

Arguments:
- name=<filename>
- size=<bytes>
- width=N[px|%]
- height=N[px|%]
- preserveAspectRatio=0|1
- inline=0|1
```

**Example:**
```bash
printf '\e]1337;File=inline=1:%s\a' "$(base64 < image.png)"
```

---

## Shell Integration

```
OSC 133 ; A ST    # Mark prompt start
OSC 133 ; B ST    # Mark command start
OSC 133 ; C ST    # Mark command executed
OSC 133 ; D ST    # Mark command finished
```

---

## Current Directory

```
OSC 1337 ; CurrentDir=/path ST
```

---

## Set User Variable

```
OSC 1337 ; SetUserVar=name=base64value ST
```

---

## Clipboard

```
OSC 1337 ; Copy=:base64text ST
```

---

## Related Documentation

- [Inline Images](../02-features-reference/inline-images.md)
- [Shell Integration](../02-features-reference/shell-integration.md)
