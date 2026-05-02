# Window Projects (Archive & Restore)

> Organize, archive, and restore terminal windows into named project hierarchies.
>
> **New in:** iTerm2 3.6.x | **Status:** Stable

---

## Overview

Window Projects is iTerm2's new workspace management feature that lets you save window arrangements into named project hierarchies for later restoration. Think of it as "bookmarks for your terminal layouts."

---

## Access

| Action | Location |
|--------|----------|
| **Open Panel** | Window → Projects |
| **Archive Window** | Window → Projects → select project → Archive |
| **Restore Window** | Window → Projects → right-click → Restore |

---

## Features

### Project Hierarchy

Create a tree structure of projects and sub-projects to organize your work:

```
Window Projects
├── Frontend
│   ├── React App (3 windows archived)
│   └── Testing (1 window archived)
├── Backend
│   ├── API Server (2 windows archived)
│   └── Database (1 window archived)
└── DevOps
    └── Monitoring (4 windows archived)
```

### Archive Operations

| Operation | Description |
|-----------|-------------|
| **Archive to Project** | Save current window layout to a selected project |
| **Keep Open** | Archive and keep the window open |
| **Close After** | Archive and close the window |
| **Restore One** | Restore a single archived window |
| **Restore All** | Restore all windows in a project |
| **Remove** | Remove an archived window from project |

### UI Layout

```
┌─────────────────────────────────────────────────┐
│  Window Projects                          [×]    │
├────────────────────┬────────────────────────────┤
│  Project Tree      │  Open Windows              │
│  (NSOutlineView)   │  (NSTableView)             │
│                    │                            │
│  ├── Frontend [3]  │  ├── Terminal 1   [Archive]│
│  │   ├── React     │  ├── Terminal 2   [Archive]│
│  │   └── Test      │  └── SSH Server  [Archive]│
│  └── Backend [2]   │                            │
│      └── API       │                            │
├────────────────────┴────────────────────────────┤
│  [+ New Project]  [+ Sub-Project]  [Restore All]│
└─────────────────────────────────────────────────┘
```

**Hover Previews:** Hovering over archived or open windows shows a preview of the window layout.

---

## Data Storage

| Aspect | Details |
|--------|---------|
| **Format** | JSON |
| **Location** | `~/Library/Application Support/iTerm2/` |
| **Model** | `iTermWindowProject` (hierarchical), `iTermArchivedWindow` (metadata + arrangement) |

### Data Model

```
iTermWindowProject
├── name: String
├── children: [iTermWindowProject]  (nested sub-projects)
└── archivedWindows: [iTermArchivedWindow]
    └── iTermArchivedWindow
        ├── metadata (title, date, session count)
        └── arrangementData (binary-encoded window arrangement)
```

---

## Use Cases

### 1. Context Switching
Switch between different projects without losing window layouts:
- Archive "Frontend" windows → Restore "Backend" windows
- Come back later and restore "Frontend" exactly as it was

### 2. Template Layouts
Save common development layouts as project templates:
- "3-pane dev" with editor + terminal + logs
- "SSH cluster" with 4 server connections

### 3. End-of-Day Archiving
Archive all windows at end of day, restore next morning:
- Preserves window positions, pane splits, running profiles
- No need to manually recreate complex layouts

---

## Comparison with Window Arrangements

| Feature | Window Arrangements | Window Projects |
|---------|-------------------|-----------------|
| **Structure** | Flat list | Hierarchical tree |
| **Organization** | By name only | Projects + sub-projects |
| **Preview** | No | Hover preview |
| **Multiple Windows** | One arrangement per save | Multiple windows per project |
| **UI** | Menu-based | Dedicated panel |
| **Archive/Restore** | Manual | Streamlined workflow |

---

## Related Documentation

- [Window Arrangements](./all-features.md#4-window-arrangements)
- [Session Restoration](./all-features.md#31-session-restoration)
