# Migration Paths

> How to migrate between terminals and automation approaches.

---

## Terminal Migrations

### Terminal.app → iTerm2

1. Download iTerm2
2. Import colors: Settings → Profiles → Colors → Import
3. Configure preferences
4. Set as default terminal

### iTerm2 → Kitty

1. Export iTerm2 color scheme
2. Install Kitty: `brew install --cask kitty`
3. Convert config to `kitty.conf`
4. Install shell integration

### iTerm2 → Alacritty

1. Install: `brew install --cask alacritty`
2. Create `~/.config/alacritty/alacritty.yml`
3. Install tmux for splits/tabs
4. Configure tmux integration

---

## Scripting Migrations

### AppleScript → Python API

See: [Migration Guide](../03-scripting/migration-guide.md)

**Summary:**
```
tell application "iTerm2"  →  import iterm2
create window             →  Window.async_create()
write text               →  session.async_send_text()
set name to              →  session.async_set_name()
```

### osascript → Python

```bash
# Before
osascript << 'EOF'
tell application "iTerm2"
    create window with default profile
end tell
EOF

# After
python3 << 'EOF'
import iterm2
async def main(c):
    await iterm2.Window.async_create(c)
iterm2.run_until_complete(main)
EOF
```

### Hammerspoon → Python API

For iTerm2-specific automation:
- Extract iTerm2 control logic
- Rewrite with Python API
- Keep Hammerspoon for other apps

---

## Configuration Sync

### iTerm2 Settings

```bash
# Export
cp ~/Library/Preferences/com.googlecode.iterm2.plist ~/backup/

# Or use cloud sync
Settings → General → Preferences → Save to folder
```

### Profile Export

```bash
# Export profile as JSON
Settings → Profiles → Other Actions → Save as JSON
```

---

## Related Documentation

- [Migration Guide](../03-scripting/migration-guide.md)
- [Terminal Emulators](./terminal-emulators.md)
