# Inline Images

> Display images directly in your terminal.

---

## Overview

iTerm2 can display images, animated GIFs, and even PDFs inline in your terminal using a proprietary escape sequence protocol.

---

## Basic Usage

### Using imgcat

```bash
# Display image
imgcat photo.jpg

# With width constraint
imgcat -W 80 image.png

# Preserve aspect ratio with height
imgcat -H 20 diagram.svg
```

### Using imgls

```bash
# List directory with image thumbnails
imgls

# Same as ls but with previews for images
```

---

## Supported Formats

| Format | Support |
|--------|---------|
| PNG | Full |
| JPEG | Full |
| GIF | Animated! |
| WebP | Full |
| TIFF | Full |
| BMP | Full |
| PDF | Rendered |
| SVG | Rendered |

---

## Installation

imgcat is installed with Shell Integration:

```bash
# Check if available
which imgcat

# Manual install
curl -L https://iterm2.com/utilities/imgcat -o /usr/local/bin/imgcat
chmod +x /usr/local/bin/imgcat
```

---

## Escape Sequence Protocol

For custom implementations:

```
ESC ] 1337 ; File = [arguments] : base64-data ST
```

Arguments:
- `name=filename` - Filename
- `size=N` - File size in bytes
- `width=N` - Display width (cells or %)
- `height=N` - Display height
- `preserveAspectRatio=1` - Keep ratio
- `inline=1` - Display inline (vs download)

---

## Python API

```python
import iterm2
import base64

async def display_image(connection, path):
    app = await iterm2.async_get_app(connection)
    session = app.current_window.current_tab.current_session

    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()

    # Send image escape sequence
    await session.async_send_text(
        f"\033]1337;File=inline=1:{data}\a"
    )

iterm2.run_until_complete(lambda c: display_image(c, "image.png"))
```

---

## Related Documentation

- [Shell Integration](./shell-integration.md)
- [Escape Sequences](../08-reference/escape-sequences.md)
