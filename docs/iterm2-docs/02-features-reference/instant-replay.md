# Instant Replay

> Travel back in terminal time to recover cleared output.
>
> **See also:** [Session Logging](./session-logging.md) for persistent, file-based recording

---

## Overview

Instant Replay records your terminal session in memory, allowing you to scroll back through time and recover text that was cleared or scrolled away. For persistent recording, see [Session Logging](./session-logging.md).

---

## Usage

| Action | Shortcut |
|--------|----------|
| **Enter Replay** | `⌘⌥B` |
| **Exit Replay** | `Esc` |
| **Navigate** | Arrow keys, scroll |
| **Search** | `⌘F` |

---

## Use Cases

1. **Recover Cleared Output**
   - Accidentally ran `clear`
   - Output scrolled off screen
   - Need to see what happened

2. **Debug Sessions**
   - Review what commands ran
   - See output sequence
   - Capture for documentation

3. **Learning**
   - Watch what happened step by step
   - Review tutorial output

---

## Configuration

```
Settings → Profiles → Terminal
☑ Unlimited scrollback (for more replay history)
```

**Memory allocation:** Configurable via `INSTANT_REPLAY_MEMORY_MB` preference key (default: 4 MB per session).

```python
# Python API: Configure via Preferences module
# PreferenceKey.INSTANT_REPLAY_MEMORY_MB
```

---

## Limitations

- High memory usage with long sessions
- Not persistent across restarts (use Session Logging for persistence)
- Cannot modify past output

---

## Instant Replay vs Session Logging

| Feature | Instant Replay | Session Logging |
|---------|---------------|-----------------|
| **Storage** | Memory (RAM) | File (disk) |
| **Persistence** | Lost on restart | Permanent |
| **Shareable** | No | Yes (asciinema, HTML) |
| **Timing data** | Yes | asciinema only |
| **Auto-start** | Always on | Configurable |
| **Access** | `⌘⌥B` | Session → Log |

For persistent session recording with playback capability, use **Session Logging** with the **asciinema** format.

---

## Related Documentation

- [Session Logging](./session-logging.md) — Persistent file-based recording
- [Paste History](./all-features.md#paste-history)
- [Shell Integration](./shell-integration.md)
