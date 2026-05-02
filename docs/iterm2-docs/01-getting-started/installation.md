# iTerm2 Installation Guide

> Complete installation instructions for iTerm2 on macOS with all configuration options.

---

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
- [Post-Installation Setup](#post-installation-setup)
- [Enabling Python API](#enabling-python-api)
- [Shell Integration](#shell-integration)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

| Requirement | Stable (3.6.9) | Legacy (3.5.14) |
|-------------|-----------------|-----------------|
| **macOS** | 12.4+ (Monterey) | 10.15+ (Catalina) |
| **RAM** | 4 GB (8 GB+ recommended) | 4 GB |
| **Disk Space** | 100 MB (500 MB with scripts) | 100 MB |
| **Python** | 3.6+ (3.10+ recommended) | 3.7+ |
| **PyPI iterm2** | v2.14 | v2.10 |

---

## Installation Methods

### Method 1: Homebrew (Recommended)

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install iTerm2
brew install --cask iterm2

# Verify installation
ls -la /Applications/iTerm.app
```

**Advantages:**
- Automatic updates via `brew upgrade --cask`
- Easy version management
- Consistent with other dev tools

### Method 2: Direct Download

1. Visit https://iterm2.com/downloads.html
2. Download the latest stable release
3. Open the `.zip` file
4. Drag `iTerm.app` to `/Applications/`

```bash
# Verify installation
open -a iTerm
```

### Method 3: Nightly Builds (Beta Features)

```bash
# For testing new features
brew install --cask iterm2-beta

# Or download from
open https://iterm2.com/downloads/nightly/
```

**Warning:** Nightly builds may be unstable.

---

## Post-Installation Setup

### 1. Set as Default Terminal

```bash
# Option A: Via System Settings
# System Settings → Desktop & Dock → Default web browser (change to terminal apps)

# Option B: Via iTerm2
# iTerm2 → Make iTerm2 Default Term
```

### 2. Grant Permissions

iTerm2 needs the following permissions:

| Permission | Location | Purpose |
|------------|----------|---------|
| **Full Disk Access** | Privacy & Security → Full Disk Access | Read all files |
| **Accessibility** | Privacy & Security → Accessibility | Keyboard shortcuts |
| **Automation** | Privacy & Security → Automation | AppleScript control |

```bash
# Open System Settings directly
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
```

### 3. Install Shell Integration

```bash
# Automatic installation (recommended)
# iTerm2 → Install Shell Integration

# Manual installation for Zsh
curl -L https://iterm2.com/shell_integration/zsh -o ~/.iterm2_shell_integration.zsh
echo 'source ~/.iterm2_shell_integration.zsh' >> ~/.zshrc

# Manual installation for Bash
curl -L https://iterm2.com/shell_integration/bash -o ~/.iterm2_shell_integration.bash
echo 'source ~/.iterm2_shell_integration.bash' >> ~/.bash_profile

# Manual installation for Fish
curl -L https://iterm2.com/shell_integration/fish -o ~/.iterm2_shell_integration.fish
echo 'source ~/.iterm2_shell_integration.fish' >> ~/.config/fish/config.fish
```

---

## Enabling Python API

### Step 1: Enable in Settings

```
iTerm2 → Settings (⌘,) → General → Magic → Enable Python API ✓
```

### Step 2: Install Python Module

```bash
# Using pip
pip install iterm2

# Using uv (recommended)
uv pip install iterm2

# Verify installation
python -c "import iterm2; print(iterm2.__version__)"
```

### Step 3: Test Connection

Create `test_connection.py`:

```python
#!/usr/bin/env python3
import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    print(f"iTerm2 version: {await app.async_get_variable('effectiveTheme')}")
    print(f"Windows: {len(app.windows)}")
    print("Connection successful!")

iterm2.run_until_complete(main)
```

Run:
```bash
python test_connection.py
```

---

## Shell Integration

### Features Enabled

| Feature | Description |
|---------|-------------|
| **Command History** | Navigate between prompts with ⌘↑/⌘↓ |
| **Current Directory** | Automatic tracking per session |
| **Command Status** | Visual indicator for success/failure |
| **Recent Directories** | Quick access to visited paths |
| **Automatic Profile Switching** | Change profile based on host/path |

### Verification

After installation, you should see these marks in your terminal:

```
┌── Blue triangle: Command start
│   $ echo "Hello"
│   Hello
└── Green/Red triangle: Command end (success/failure)
```

### Utilities Installed

```bash
# These commands become available:
imgcat image.png          # Display images inline
imgls                     # List files with thumbnails
it2attention fireworks    # Trigger attention indicator
it2check                  # Verify shell integration
it2copy                   # Copy to clipboard
it2dl file.txt           # Download file
it2getvar varname        # Get iTerm2 variable
it2setcolor preset       # Set color preset
it2setkeylabel           # Set Touch Bar key labels
it2ul file.txt           # Upload file
it2universion            # Show Unicode version
```

---

## Troubleshooting

### Common Issues

#### Python API Not Connecting

```bash
# Check if iTerm2 is running
pgrep -x iTerm2

# Verify Python API is enabled
# Settings → General → Magic → Enable Python API

# Check Python version
python --version  # Should be 3.7+

# Reinstall iterm2 module
pip uninstall iterm2 && pip install iterm2
```

#### Shell Integration Not Working

```bash
# Verify installation
cat ~/.zshrc | grep iterm2_shell_integration

# Reinstall
curl -L https://iterm2.com/shell_integration/install_shell_integration.sh | bash

# Check for conflicts
# Disable oh-my-zsh themes that override PROMPT
```

#### Permissions Issues

```bash
# Reset Accessibility permissions
tccutil reset Accessibility com.googlecode.iterm2

# Re-grant in System Settings
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
```

#### Slow Startup

```bash
# Disable GPU renderer if issues
defaults write com.googlecode.iterm2 UseMetal -bool NO

# Clear font cache
atsutil databases -remove

# Remove problematic scripts
ls ~/Library/Application\ Support/iTerm2/Scripts/
```

---

## Next Steps

- [First Launch](first-launch.md) - Initial configuration walkthrough
- [Basic Configuration](basic-configuration.md) - Essential settings
- [Features Reference](../02-features-reference/all-features.md) - Complete feature list

---

## Related Documentation

- [iTerm2 Downloads](https://iterm2.com/downloads.html)
- [Python API Documentation](https://iterm2.com/python-api/)
- [Shell Integration](https://iterm2.com/documentation-shell-integration.html)
