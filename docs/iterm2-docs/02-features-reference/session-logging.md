# Session Logging & Recording

> Record terminal sessions in multiple formats including asciinema for playback.
>
> **Available in:** iTerm2 3.5+ | **Formats:** Raw, Plain Text, HTML, asciinema

---

## Overview

iTerm2 provides comprehensive session logging that records terminal output in four different formats. Combined with Import/Export Recording, this serves as the session recording feature.

---

## Access

| Action | Location |
|--------|----------|
| **Start Logging** | Session → Log → Log to File |
| **Import Recording** | Session → Log → Import Recording |
| **Export Recording** | Session → Log → Export Recording |
| **Auto-log** | Settings → Profiles → Session |

---

## Log Formats

| Format | Content | Best For |
|--------|---------|----------|
| **Raw data** | All input including control sequences | Debugging, replay |
| **Plain text** | Control sequences stripped | Reading, searching |
| **HTML** | Colors and font attributes preserved | Sharing, documentation |
| **asciinema** | Timing + attributes, `.cast` format | Playback, demos |

### asciinema Format (Recommended for Recording)

The asciinema format preserves timing information, making it the closest to a "video recording" of your terminal session.

```bash
# Play back a recording
asciinema play session.cast

# Upload to asciinema.org for sharing
asciinema upload session.cast

# Convert to GIF
# Install: pip install agg (asciinema-agg)
agg session.cast session.gif
```

---

## Configuration

### Automatic Session Logging

```
Settings → Profiles → Session
  ☑ Automatically log session input to files in:
  Folder: ~/terminal-logs/
  Filename: \(session.name)-\(session.creationTimeString)
```

**Interpolated String Variables:**
- `\(session.name)` — Session name
- `\(session.creationTimeString)` — Creation timestamp
- `\(session.hostname)` — Connected hostname
- `\(session.username)` — Current user
- `\(session.path)` — Current directory

### Manual Session Logging

1. Session → Log → Log to File
2. Choose format and destination
3. Session → Log → Log to File (again to stop)

---

## Import/Export Recording

The Import/Export Recording feature allows you to:

| Operation | Description |
|-----------|-------------|
| **Export** | Save current session as a recording file |
| **Import** | Load a previously exported recording for playback |

This is the "Session Recording" / "Archive" capability — it captures and preserves terminal sessions for later review.

### File Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| **iTerm Archive** | `.itermarchive` | Full session archive with state |
| **iTerm Recording** | `.itr` | DVR playback data with timestamps + profile |

**Recording Codec (`.itr`):**
- Supports format versions 1-4
- Contains DVR (Digital Video Recorder) playback data with timestamps
- Includes terminal profile configuration
- Encoding: Extract DVR + profile → Strip sensitive keys → Generate new GUID → NSKeyedArchiver → GZIP compress
- Supports full-session export and time-range segment export
- Loading creates a synthetic session for playback

### Session Archiving (v3.6.7+)

Full-fidelity disk copies of sessions — goes beyond logging.

| Feature | Details |
|---------|---------|
| **Access** | Session → Archive / Recent Archives |
| **Storage** | Up to 10 recent archives in UserDefaults |
| **Restore** | Recent Archives submenu or "Open Archive" file dialog |

---

## Comparison: Instant Replay vs Session Logging

| Feature | Instant Replay | Session Logging |
|---------|---------------|-----------------|
| **Access** | `⌘⌥B` | Session → Log |
| **Persistence** | Memory only (lost on restart) | File-based (permanent) |
| **Format** | Internal buffer | Raw/Text/HTML/asciinema |
| **Shareable** | No | Yes |
| **Playback** | Built-in time travel | asciinema player |
| **Memory Impact** | High (configurable MB/session) | Disk-based |
| **Timing** | Yes | asciinema format only |
| **Auto-start** | Always on | Configurable per profile |

---

## Python API Access

There is no dedicated Session Recording API in the Python module. However, you can:

```python
import iterm2

async def capture_screen(connection):
    app = await iterm2.async_get_app(connection)
    session = app.current_window.current_tab.current_session

    # Read current screen contents
    contents = await session.async_get_screen_contents()
    for line in contents.lines:
        print(line.string)

    # Monitor screen changes in real-time
    async with session.get_screen_streamer() as streamer:
        while True:
            contents = await streamer.async_get()
            # Process screen updates

    # Configure replay memory (via Preferences)
    # PreferenceKey.INSTANT_REPLAY_MEMORY_MB
```

---

## Use Cases

### 1. Documentation
Record terminal workflows for documentation with asciinema format, then embed in web pages.

### 2. Debugging
Log raw output to capture exact terminal state including control sequences for bug reports.

### 3. Training
Create interactive terminal demos that others can replay at their own pace.

### 4. Audit Trail
Auto-log all sessions for compliance or security auditing with plain text format.

---

## Related Documentation

- [Instant Replay](./instant-replay.md)
- [Shell Integration](./shell-integration.md)
