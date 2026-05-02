# Triggers

> Regex-based automatic actions that respond to terminal output.
>
> **Updated:** 2026-03-23 | **Actions:** 26 | **Python API:** Triggers module (v2.10+)

---

## Overview

Triggers watch terminal output and perform actions when patterns match. They enable automation without scripting. As of v3.6.x, there are **26 trigger actions** and **5 event-based match types**.

---

## Configuration

```
Settings → Profiles → Advanced → Triggers → Edit
```

Each trigger has:
- **Regular Expression**: Pattern to match
- **Action**: What to do when matched
- **Parameters**: Action-specific settings
- **Instant**: Run immediately vs. on newline

---

## Available Actions (26 Total)

| # | Action | Description | Parameters |
|---|--------|-------------|------------|
| 1 | **Annotate** | Add annotation to matched text | Note text |
| 2 | **Bounce Dock Icon** | Bounce app icon in Dock | None |
| 3 | **Capture Output** | Capture for Toolbelt | Pattern groups |
| 4 | **Change Style** | Modify text style | Style options |
| 5 | **Fold to Named Mark** | Fold content to named mark | Mark name (NEW) |
| 6 | **Highlight Line** | Highlight entire line | Color |
| 7 | **Highlight Text** | Change text appearance | Color, underline, bold |
| 8 | **Inject Data** | Inject data into terminal | Data |
| 9 | **Invoke Script Function** | Call Python API function | Function name |
| 10 | **Make Hyperlink** | Create clickable link | URL template |
| 11 | **Open Password Manager** | Show password manager | None |
| 12 | **Post Notification** | macOS notification | Title, message |
| 13 | **Prompt Detected** | Report prompt detection | None |
| 14 | **Report Directory** | Report current directory | Path |
| 15 | **Report User & Host** | Report user and hostname | User@Host |
| 16 | **Ring Bell** | Terminal bell | None |
| 17 | **Run Command** | Execute shell command | Command |
| 18 | **Run Coprocess** | Start coprocess | Script path |
| 19 | **Run Silent Coprocess** | Background script | Script path |
| 20 | **Send Text** | Type text automatically | Text to send |
| 21 | **Set Mark** | Set a mark at matched position | None |
| 22 | **Set Named Mark** | Create named scroll marker | Mark name (NEW) |
| 23 | **Set Title** | Change session title | Title text |
| 24 | **Set User Variable** | Set a user variable | Variable=Value |
| 25 | **Show Alert** | Display alert dialog | Message |
| 26 | **Stop Processing** | Skip remaining triggers | None |

### Event-Based Match Types (NEW in v2.10+)

| Event Type | When Triggered |
|------------|----------------|
| `EVENT_LONG_RUNNING_COMMAND` | Command runs longer than threshold |
| `EVENT_CUSTOM_ESCAPE_SEQUENCE` | Custom escape sequence received |
| `EVENT_SESSION_ENDED` | Session terminates |
| `EVENT_ACTIVITY_AFTER_IDLE` | Output after period of inactivity |
| `EVENT_BELL_RECEIVED` | Terminal bell character received |

### New Trigger Types (2025-2026)

| Trigger | Added | Description |
|---------|-------|-------------|
| `SetNamedMarkTrigger` | Jan 2025 | Create named scroll markers |
| `FoldTrigger` | Jan 2025 | Code folding markers |
| `SGRTrigger` | Mar 2025 | Terminal graphics attributes |
| `BufferInputTrigger` | Dec 2025 | Input buffering control |

---

## Common Examples

### Highlight Errors

| Setting | Value |
|---------|-------|
| Regex | `(?i)error\|fail\|exception` |
| Action | Highlight Text |
| Color | Red background |

### Password Auto-fill

| Setting | Value |
|---------|-------|
| Regex | `[Pp]assword:` |
| Action | Send Text |
| Text | `\(user.password)\n` |
| Instant | Yes |

### Build Success Notification

| Setting | Value |
|---------|-------|
| Regex | `BUILD SUCCESS` |
| Action | Send Notification |
| Title | Build Complete |

### SSH Host Detection

| Setting | Value |
|---------|-------|
| Regex | `(\w+)@([\w.-]+):` |
| Action | Set Host |
| Hostname | `\2` |

---

## Regex Tips

| Pattern | Matches |
|---------|---------|
| `error` | Literal "error" |
| `(?i)error` | Case-insensitive |
| `error\|fail` | "error" or "fail" |
| `\d+` | One or more digits |
| `^error` | "error" at line start |
| `error$` | "error" at line end |

---

## Python API

Triggers are profile settings, configured via Profile API:

```python
import iterm2

async def add_trigger(connection):
    all_profiles = await iterm2.PartialProfile.async_get(connection)
    for profile in all_profiles:
        full = await profile.async_get_full_profile()
        triggers = full.triggers or []
        triggers.append({
            "regex": "error",
            "action": "HighlightTextTrigger",
            "parameter": "red"
        })
        await full.async_set_triggers(triggers)

iterm2.run_until_complete(add_trigger)
```

---

## Python API: Triggers Module (v2.10+)

The dedicated Triggers module provides programmatic trigger management:

```python
import iterm2

# 20+ trigger types available:
# HighlightTrigger, SendTextTrigger, RunCommandTrigger,
# AlertTrigger, RPCTrigger, FoldTrigger, SGRTrigger,
# BufferInputTrigger, SetNamedMarkTrigger, AnnotateTrigger,
# BounceDockIconTrigger, CaptureOutputTrigger, ...
```

See [Python API Reference](../03-scripting/python-api-reference.md#triggers-module) for full details.

---

## Related Documentation

- [Profiles](./profiles.md)
- [Shell Integration](./shell-integration.md)
- [Python API Reference](../03-scripting/python-api-reference.md)
