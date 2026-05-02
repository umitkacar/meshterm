# Smart Selection

> Automatically recognize and select URLs, paths, emails, and more.

---

## Overview

Smart Selection intelligently identifies common patterns in terminal output, making it easy to select and act on URLs, file paths, email addresses, and other structured text.

---

## How to Use

| Action | Method |
|--------|--------|
| **Select Smart** | Quadruple-click |
| **Open/Act** | ⌘-click |
| **Copy** | Select → ⌘C |

---

## Default Patterns

| Pattern Type | Example |
|--------------|---------|
| **URLs** | `https://example.com/path` |
| **File Paths** | `/Users/name/file.txt` |
| **Email** | `user@example.com` |
| **IPv4** | `203.0.113.1` |
| **IPv6** | `::1` |
| **Git Hashes** | `a1b2c3d4e5f6` |
| **UUID** | `550e8400-e29b-41d4-a716-446655440000` |

---

## Custom Patterns

Add custom patterns:

```
Settings → Profiles → Advanced → Smart Selection → Edit
```

### Example: Jira Ticket

```
Regex: [A-Z]+-\d+
Actions: Open URL
URL: https://jira.company.com/browse/\0
```

### Example: Docker Container ID

```
Regex: [a-f0-9]{12}
Actions: Copy
```

---

## Actions

| Action | Description |
|--------|-------------|
| **Open URL** | Open in browser |
| **Copy** | Copy to clipboard |
| **Run Command** | Execute with selection |
| **Open with...** | Open in specific app |

---

## Related Documentation

- [Shell Integration](./shell-integration.md)
- [Triggers](./triggers.md)
