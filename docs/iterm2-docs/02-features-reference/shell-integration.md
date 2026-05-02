# Shell Integration

> Enhanced shell features for command tracking, navigation, and automation.

---

## Overview

Shell Integration adds intelligence to your terminal by understanding command boundaries, tracking directories, and enabling powerful navigation features.

---

## Installation

### Automatic Installation

```
iTerm2 → Install Shell Integration
```

### Manual Installation

#### Zsh
```bash
curl -L https://iterm2.com/shell_integration/zsh \
    -o ~/.iterm2_shell_integration.zsh
echo 'source ~/.iterm2_shell_integration.zsh' >> ~/.zshrc
```

#### Bash
```bash
curl -L https://iterm2.com/shell_integration/bash \
    -o ~/.iterm2_shell_integration.bash
echo 'source ~/.iterm2_shell_integration.bash' >> ~/.bash_profile
```

### Verification

```bash
it2check
```

---

## Features Enabled

### 1. Command Navigation

| Action | Shortcut |
|--------|----------|
| **Previous Command** | `⌘⇧↑` |
| **Next Command** | `⌘⇧↓` |

### 2. Command Status Indication

| Mark Color | Meaning |
|------------|---------|
| **Blue Triangle** | Command start |
| **Green Triangle** | Exit code 0 (success) |
| **Red Triangle** | Non-zero exit code (failure) |

### 3. Current Directory Tracking

iTerm2 knows your current directory automatically for:
- Tab title display
- Recent Directories menu (`⌘⌥/`)
- Semantic history

### 4. Utilities Installed

| Command | Purpose |
|---------|---------|
| `imgcat` | Display images inline |
| `imgls` | List with thumbnails |
| `it2copy` | Copy to clipboard |
| `it2dl` | Download file |
| `it2ul` | Upload file |
| `it2attention` | Trigger attention |
| `it2check` | Verify integration |

---

## Automatic Profile Switching

Change profiles based on context:

| Trigger | Example |
|---------|---------|
| Username | root → Red profile |
| Hostname | production → Orange profile |
| Directory | /project → Project profile |

---

## Python API Integration

```python
import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    session = app.current_window.current_tab.current_session

    # Get current directory (requires shell integration)
    path = await session.async_get_variable("path")
    print(f"Current directory: {path}")

iterm2.run_until_complete(main)
```

---

## Related Documentation

- [Automatic Profile Switching](./profiles.md)
- [Triggers](./triggers.md)
