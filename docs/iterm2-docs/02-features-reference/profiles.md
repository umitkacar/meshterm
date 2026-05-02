# Profiles

> Manage appearance, behavior, and settings per-session.

---

## Overview

Profiles store all settings for a terminal session: colors, fonts, key bindings, triggers, and more. You can create multiple profiles for different use cases.

---

## Profile Management

### Create Profile

```
Settings → Profiles → + (bottom left)
```

### Duplicate Profile

```
Settings → Profiles → Other Actions → Duplicate Profile
```

### Set as Default

```
Settings → Profiles → Other Actions → Set as Default
```

### Export/Import

```
Settings → Profiles → Other Actions → Save Profile as JSON
Settings → Profiles → Other Actions → Import from JSON
```

---

## Profile Settings Categories

| Category | Settings |
|----------|----------|
| **General** | Name, badge, command, directory |
| **Colors** | Color scheme, presets |
| **Text** | Font, cursor, text rendering |
| **Window** | Size, style, background |
| **Terminal** | Scrollback, notifications |
| **Session** | Status bar, logging |
| **Keys** | Key mappings |
| **Advanced** | Triggers, semantic history |

---

## Dynamic Profiles

JSON-based profiles for programmatic management.

### Location

```
~/Library/Application Support/iTerm2/DynamicProfiles/
```

### Example

```json
{
  "Profiles": [
    {
      "Name": "Remote Production",
      "Guid": "production-server-profile",
      "Dynamic Profile Parent Name": "Default",
      "Badge Text": "PROD",
      "Background Color": {
        "Red Component": 0.2,
        "Green Component": 0.0,
        "Blue Component": 0.0
      }
    }
  ]
}
```

---

## Automatic Profile Switching

Change profile based on context (requires Shell Integration):

```
Settings → Profiles → Advanced → Automatic Profile Switching
```

| Trigger Type | Example |
|--------------|---------|
| Username | `root` → "Root Profile" |
| Hostname | `prod-*` → "Production" |
| Path | `/home/*/work` → "Work" |

---

## Tagged Profiles

Organize profiles with tags:

```
Settings → Profiles → Tags
```

Search profiles in Open Quickly: `⌘⇧O`

---

## Python API

```python
import iterm2

async def create_profile(connection):
    # Get default profile
    default = await iterm2.Profile.async_get_default(connection)

    # Create new profile based on default
    new_profile = iterm2.LocalWriteOnlyProfile()
    new_profile.set_name("My Profile")
    new_profile.set_badge_text("\\(user)@\\(hostname)")

    await new_profile.async_create(connection)

iterm2.run_until_complete(create_profile)
```

---

## Related Documentation

- [Triggers](./triggers.md)
- [Shell Integration](./shell-integration.md)
- [Python API Reference](../03-scripting/python-api-reference.md)
