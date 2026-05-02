# iTerm2 Complete Features Reference

> Comprehensive catalog of all 39+ iTerm2 features with descriptions, shortcuts, and use cases.
>
> **Updated:** 2026-03-23 | **Version:** 3.6.9 | **Python API:** 2.14

---

## Table of Contents

- [Window Management](#window-management)
- [Navigation & Search](#navigation--search)
- [Productivity Features](#productivity-features)
- [Visual & Display](#visual--display)
- [Automation & Scripting](#automation--scripting)
- [Integration Features](#integration-features)
- [AI Features](#ai-features) (NEW)
- [Advanced Features](#advanced-features)
- [New in 3.6.x](#new-in-36x)

---

## Features Overview

| Category | Count | Key Features |
|----------|-------|--------------|
| Window Management | 5 | Split Panes, Tabs, Hotkey Window, Arrangements, **Window Projects** |
| Navigation | 5 | Search, Shell Integration, Smart Selection, Marks, **Open Quickly** |
| Productivity | 6 | Autocomplete, Copy Mode, Paste History, Instant Replay, Command History, **Composer** |
| Visual | 7 | 24-bit Color, Inline Images, Badges, Status Bar, Timestamps, Themes, **Blocks** |
| Automation | 4 | Python API (30 modules), Triggers (26 actions), Coprocesses, AppleScript |
| Integration | 4 | tmux, Password Manager, Shell Integration, **Web Browser** |
| AI | 3 | **AI Chat**, **Codecierge**, **AI Command Suggestions** |
| Advanced | 6 | Captured Output, Annotations, Buried Sessions, **Session Logging**, Session Restoration, **Dynamic Profiles** |

---

## Window Management

### 1. Split Panes

Divide a single tab into multiple terminal sessions.

| Aspect | Details |
|--------|---------|
| **Shortcuts** | `⌘D` (vertical), `⌘⇧D` (horizontal) |
| **Navigation** | `⌘⌥↑↓←→` |
| **Maximize** | `⌘⇧↩` toggle |
| **Close** | `⌘W` |

```
┌──────────────────────────────────┐
│        Session 1 (vim)          │
├────────────────┬─────────────────┤
│  Session 2     │   Session 3     │
│  (terminal)    │   (logs)        │
└────────────────┴─────────────────┘
```

**Use Cases:**
- Editor + terminal side by side
- Logs monitoring while developing
- Multiple SSH sessions

**Python API:**
```python
left_session = tab.current_session
right_session = await left_session.async_split_pane(vertical=True)
```

---

### 2. Tabs

Multiple terminal sessions in a single window.

| Aspect | Details |
|--------|---------|
| **New Tab** | `⌘T` |
| **Close Tab** | `⌘W` |
| **Navigate** | `⌘1-9`, `⌘←→`, `⌘⇧[]` |
| **Move Tab** | `⌘⇧←→` |

**Features:**
- Tab titles show running command
- Tab colors indicate activity
- Drag to reorder
- Right-click for context menu

---

### 3. Hotkey Window

System-wide instant access terminal.

| Aspect | Details |
|--------|---------|
| **Setup** | Settings → Keys → Hotkey |
| **Trigger** | Custom (e.g., Double-tap ⌥) |
| **Style** | Dropdown, floating, full-screen |

**Configuration:**
```
☑ Show/hide all windows with a system-wide hotkey
Or create dedicated hotkey window with profile
```

**Use Cases:**
- Quick command execution
- Note taking
- Calculator/conversions
- Quick SSH connections

---

### 4. Window Arrangements

Save and restore window layouts.

| Aspect | Details |
|--------|---------|
| **Save** | Window → Save Window Arrangement |
| **Restore** | Window → Restore Window Arrangement |
| **Default** | Settings → Arrangements → Set Default |

**Python API:**
```python
arrangement = await iterm2.Arrangement.async_list(connection)
await iterm2.Arrangement.async_restore(connection, "My Layout")
```

---

## Navigation & Search

### 5. Search

Find text in terminal output.

| Aspect | Details |
|--------|---------|
| **Open** | `⌘F` |
| **Next** | `⌘G` or `↩` |
| **Previous** | `⌘⇧G` |
| **Regex** | Toggle in search bar |

**Features:**
- Regular expression support
- Case sensitive toggle
- Highlights all matches
- Search across all panes

---

### 6. Shell Integration

Enhanced shell features with command awareness.

| Aspect | Details |
|--------|---------|
| **Install** | iTerm2 → Install Shell Integration |
| **Shells** | bash, zsh, fish, tcsh |
| **Navigate** | `⌘⇧↑↓` between prompts |

**Enabled Features:**
- Command history navigation
- Current directory tracking
- Command success/failure indication
- Recent directories menu
- Automatic profile switching

**Visual Indicators:**
```
┌── Blue mark: Command start
│   $ ls -la
│   [output...]
└── Green/Red mark: Command end (success/fail)
```

---

### 7. Smart Selection

Automatically recognize and select special text.

| Aspect | Details |
|--------|---------|
| **Trigger** | Quadruple-click or ⌘-click |
| **Recognized** | URLs, paths, emails, IPs, UUIDs |

**Default Patterns:**
- URLs: `https://example.com`
- Paths: `/Users/name/file.txt`
- Emails: `user@example.com`
- Git hashes: `a1b2c3d4`

**Custom Patterns:**
Settings → Profiles → Advanced → Smart Selection

---

### 8. Marks and Navigation

Navigate between shell prompts and marks.

| Aspect | Details |
|--------|---------|
| **Next Mark** | `⌘⇧↓` |
| **Previous Mark** | `⌘⇧↑` |
| **Set Mark** | `⌘⇧M` |
| **Jump to Mark** | `⌘⇧J` |

---

## Productivity Features

### 9. Autocomplete

Command completion from terminal history.

| Aspect | Details |
|--------|---------|
| **Trigger** | `⌘;` |
| **Navigate** | Arrow keys |
| **Select** | `↩` |

**Sources:**
- Command history
- Current session output
- File paths
- Hostnames

---

### 10. Copy Mode

Vim-like text selection without mouse.

| Aspect | Details |
|--------|---------|
| **Enter** | `⌘⇧C` |
| **Exit** | `Esc` or `q` |
| **Select** | `v` (char), `V` (line) |
| **Copy** | `y` |

**Navigation:**
- `h/j/k/l` - Character movement
- `w/b` - Word movement
- `0/$` - Line start/end
- `gg/G` - Document start/end
- `/` - Search

---

### 11. Paste History

Access previously copied text.

| Aspect | Details |
|--------|---------|
| **Open** | `⌘⇧H` |
| **Navigate** | Arrow keys or type to filter |
| **Paste** | `↩` |
| **Persistence** | Settings → General → Save paste history |

---

### 12. Instant Replay

Travel back in terminal time.

| Aspect | Details |
|--------|---------|
| **Enter** | `⌘⌥B` |
| **Navigate** | Arrow keys, scroll |
| **Exit** | `Esc` |

**Use Cases:**
- Recover cleared output
- Review long-running command output
- Debug what happened

---

### 13. Command History

Search and reuse previous commands.

| Aspect | Details |
|--------|---------|
| **Open** | `⌘⇧;` |
| **Filter** | Type to search |
| **Execute** | Select and `↩` |

---

## Visual & Display

### 14. 24-bit True Color

Full RGB color support (16 million colors).

| Aspect | Details |
|--------|---------|
| **Support** | Automatic for compatible apps |
| **Apps** | Vim, Neovim, tmux, bat |

**Test:**
```bash
# Display color gradient
awk 'BEGIN{
    for(r=0;r<256;r+=8)
        printf "\033[48;2;%d;%d;%dm \033[0m",r,128,255-r
}'
```

---

### 15. Inline Images

Display images directly in terminal.

| Aspect | Details |
|--------|---------|
| **Command** | `imgcat image.png` |
| **Thumbnails** | `imgls` |
| **Protocol** | Proprietary escape codes |

**Supported Formats:**
- PNG, JPEG, GIF (animated!)
- PDF
- SVG (rendered)

**Python API:**
```python
await session.async_send_text(iterm2.util.image_to_base64(image_path))
```

---

### 16. Badges

Display text overlay on terminal.

| Aspect | Details |
|--------|---------|
| **Setup** | Settings → Profiles → General → Badge |
| **Variables** | `\(session.name)`, `\(user)`, `\(hostname)` |
| **Position** | Right side of terminal |

**Common Badges:**
```
\(user)@\(hostname)
\(session.path)
\(git.branch)
```

---

### 17. Status Bar

Customizable information bar.

| Aspect | Details |
|--------|---------|
| **Enable** | Settings → Profiles → Session → Status bar |
| **Configure** | Drag components to layout |
| **Position** | Top or bottom |

**Available Components:**
- Current Directory
- Git State
- CPU/Memory Utilization
- Clock
- Search
- User-defined

---

### 18. Timestamps

Show when each line was output.

| Aspect | Details |
|--------|---------|
| **Toggle** | View → Show Timestamps |
| **Format** | Settings → Profiles → Terminal |

---

## Automation & Scripting

### 19. Python API (Modern - Recommended)

Modern scripting with 30 modules (PyPI v2.14, Feb 2026).

| Aspect | Details |
|--------|---------|
| **Enable** | Settings → General → Magic → Enable Python API |
| **Install** | `pip install iterm2` (v2.14) |
| **Docs** | https://iterm2.com/python-api/ |
| **Python** | 3.6+ (3.14 compatible) |

**Modules (30):**
```
Alert, App, Arrangement, Binding*, Broadcast, Color,
ColorPresets, Connection, CustomControl, FilePanel*,
Focus, Keyboard, LifeCycle, MainMenu, Preferences,
Profile, Prompt, Registration, Screen, Selection,
Session, StatusBar, Tab, Tmux, Tool, Transaction,
Triggers*, Utilities, Variables, Window
```
*\* New modules — Binding (key bindings), FilePanel (Open/Save dialogs), Triggers (26 trigger actions)*

**New in v2.12+:**
- `PolyModalAlert` — Rich dialogs with checkboxes, comboboxes, text fields
- `async_list_prompts()` — Retrieve prompt history
- 4 new trigger types: `FoldTrigger`, `SGRTrigger`, `BufferInputTrigger`, `SetNamedMarkTrigger`

**Example:**
```python
import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = await iterm2.Window.async_create(connection)
    session = window.current_tab.current_session
    await session.async_send_text("echo 'Hello World'\n")

iterm2.run_until_complete(main)
```

---

### 20. Triggers

Regex-based automatic actions.

| Aspect | Details |
|--------|---------|
| **Setup** | Settings → Profiles → Advanced → Triggers |
| **Regex** | Standard regex patterns |
| **Actions** | Highlight, Alert, Run Command, etc. |

**Available Actions:**
- Highlight Text
- Show Alert
- Send Text
- Run Command
- Set Title
- Stop Processing
- Send Growl/Notification
- Report Directory/Host/User

**Example Triggers:**
| Pattern | Action |
|---------|--------|
| `error:.*` | Highlight red |
| `password:` | Send password |
| `BUILD SUCCESS` | Show alert |

---

### 21. Coprocesses

Run scripts that interact with terminal I/O.

| Aspect | Details |
|--------|---------|
| **Start** | Session → Run Coprocess |
| **Purpose** | Filter/modify terminal output |
| **Language** | Any executable script |

---

### 22. AppleScript (Legacy - Deprecated)

Traditional macOS scripting.

| Aspect | Details |
|--------|---------|
| **Status** | ⚠️ Deprecated |
| **Alternative** | Use Python API |
| **Bridge** | `osascript -e '...'` |

**Basic Example:**
```applescript
tell application "iTerm2"
    create window with default profile
    tell current session of current tab of current window
        write text "echo 'Hello'"
    end tell
end tell
```

---

## Integration Features

### 23. tmux Integration

Native tmux support without prefix keys.

| Aspect | Details |
|--------|---------|
| **Connect** | `tmux -CC` |
| **Attach** | `tmux -CC attach` |
| **Features** | Native tabs/splits for tmux |

**Benefits:**
- No prefix key needed
- Native copy/paste
- Use iTerm2 shortcuts
- Split panes become iTerm splits

---

### 24. Password Manager

Secure credential storage.

| Aspect | Details |
|--------|---------|
| **Open** | `⌘⌥F` |
| **Storage** | macOS Keychain |
| **Fill** | Select and paste |

---

### 25. Shell Integration Utilities

Commands installed with shell integration.

| Command | Purpose |
|---------|---------|
| `imgcat` | Display images |
| `imgls` | List with thumbnails |
| `it2copy` | Copy to clipboard |
| `it2dl` | Download file |
| `it2ul` | Upload file |
| `it2attention` | Trigger attention |
| `it2check` | Verify integration |
| `it2getvar` | Get iTerm2 variable |

---

## Advanced Features

### 26. Captured Output

Extract structured output (like IDE errors).

| Aspect | Details |
|--------|---------|
| **View** | Toolbelt → Captured Output |
| **Click** | Navigate to location |
| **Setup** | Capture output triggers |

---

### 27. Annotations

Add notes to terminal output.

| Aspect | Details |
|--------|---------|
| **Add** | Select text, View → Annotations → Add |
| **View** | View → Show Annotations |

---

### 28. Buried Sessions

Hide sessions without closing.

| Aspect | Details |
|--------|---------|
| **Bury** | Session → Bury Session |
| **Restore** | Session → Restore Buried Session |
| **Use Case** | Long-running background tasks |

---

### 29. AI Chat (Major New Feature)

Full AI assistant integrated into iTerm2 with session awareness.

| Aspect | Details |
|--------|---------|
| **Access** | Window → AI Chat, Session → Open AI Chat |
| **Explain** | Edit → Explain Output with AI |
| **Settings** | Settings → General → AI |
| **Linked Sessions** | Chats can be linked to terminal sessions for context |

**7 Permission Categories (per chat, cycled Never/Ask/Always):**

| Permission | Purpose |
|------------|---------|
| Check Terminal State | Directory, shell type, command history, SSH host |
| Run Commands | Execute terminal commands on user's behalf |
| Type for You | Send keystrokes to terminal |
| View History | Access command history from linked session |
| View Manpages | Access man pages (including remote via SSH) |
| Write to Clipboard | Modify clipboard contents |
| Act in Web Browser | View/interact with web pages |

**Additional:**
- Model selection toolbar (supports custom endpoints/API)
- Web search capability (globe icon)
- Reasoning mode (lightbulb icon)
- Message editing (right-click to edit/copy/fork)

---

### 30. Codecierge

AI-powered code assistant in the Toolbelt.

| Aspect | Details |
|--------|---------|
| **Access** | View → Toolbelt → Codecierge |
| **Purpose** | Intelligent code assistance integrated with terminal context |

---

### 31. Session Restoration

Recover sessions after crashes or restarts.

| Aspect | Details |
|--------|---------|
| **Enable** | Settings → General → Startup |
| **Scope** | Window positions, running commands |

---

### 32. Window Projects (NEW - Archive Feature)

Organize, archive, and restore terminal windows into named project hierarchies.

| Aspect | Details |
|--------|---------|
| **Access** | Window → Projects |
| **Storage** | JSON persistence in Application Support |
| **Features** | Hierarchical project tree, hover previews |

**Capabilities:**
- Create root projects and nested sub-projects
- Archive open windows to selected project (keep open or close)
- Restore individual windows or all windows in a project
- Rename/delete projects via context menu
- Preserves window arrangements using existing serialization

**UI Layout:**
```
┌───────────────────────────────────────────┐
│  Window Projects Panel                     │
├──────────────────┬────────────────────────┤
│  Project Tree    │  Open Windows          │
│  ├── Frontend    │  ├── Terminal 1  [+]   │
│  │   ├── (3)     │  ├── Terminal 2  [+]   │
│  └── Backend     │  └── Terminal 3  [+]   │
│      └── (5)     │                        │
├──────────────────┴────────────────────────┤
│  [New Project] [Restore All] [Archive →]  │
└───────────────────────────────────────────┘
```

---

### 33. Session Logging

Record terminal sessions in multiple formats.

| Aspect | Details |
|--------|---------|
| **Access** | Session → Log → Log to File |
| **Import/Export** | Session → Log → Import/Export Recording |
| **Auto-log** | Settings → Profiles → Session → Automatic Session Logging |

**Log Formats:**

| Format | Extension | Content |
|--------|-----------|---------|
| **Raw data** | `.log` | All input including control sequences |
| **Plain text** | `.txt` | Control sequences removed, CLI-readable |
| **HTML** | `.html` | Colors and font attributes preserved |
| **asciinema** | `.cast` | Timing + font attributes, playable with asciinema |

**Configuration (Settings → Profiles → Session):**
- Toggle automatic session logging
- Custom folder (supports interpolated strings)
- Custom filename (supports interpolated strings)

---

### 34. Composer / Auto Composer

Native macOS text view replacing traditional shell prompt for command editing.

| Aspect | Details |
|--------|---------|
| **Show** | View → Show Composer |
| **Auto** | View → Auto Composer |
| **Status Bar** | Available as a status bar component |
| **AI** | "Offer AI command suggestion in Composer" option |

---

### 35. Open Quickly

Fast session search and navigation.

| Aspect | Details |
|--------|---------|
| **Shortcut** | `⌘⇧O` |
| **Search by** | Title, command, host, user, profile, directory |

---

### 36. Web Browser

Built-in web browsing capability.

| Aspect | Details |
|--------|---------|
| **Access** | Web → Open Location |
| **Navigation** | Back, Forward, Reload, History |
| **AI** | AI can "Act in Web Browser" with permission |

---

### 37. Blocks & Buttons (v3.6.9+)

Escape sequence-based UI elements in the terminal.

| Element | Details |
|---------|---------|
| **Blocks** | Code block regions with fold/unfold support (UpdateBlock) |
| **Buttons** | Clickable copy and custom buttons via escape sequences |

---

### 38. Dynamic Profiles

JSON/XML/plist-based profile definitions with inheritance.

| Aspect | Details |
|--------|---------|
| **Location** | `~/Library/Application Support/iTerm2/DynamicProfiles/` |
| **Format** | JSON, XML, or plist |
| **Features** | Parent inheritance, rewritable, auto-reload |

---

### 39. Advanced Paste

Enhanced paste with transformation options.

| Aspect | Details |
|--------|---------|
| **Access** | Edit → Paste Special → Advanced Paste |
| **Features** | Edit before pasting, base64 conversion, character transforms |

---

## Feature Matrix

| Feature | Shortcut | Python API | AppleScript |
|---------|----------|------------|-------------|
| Split Pane | `⌘D` | ✅ | ✅ |
| New Tab | `⌘T` | ✅ | ✅ |
| Search | `⌘F` | ❌ | ❌ |
| Autocomplete | `⌘;` | ❌ | ❌ |
| Copy Mode | `⌘⇧C` | ❌ | ❌ |
| Paste History | `⌘⇧H` | ❌ | ❌ |
| Instant Replay | `⌘⌥B` | ❌ | ❌ |
| Triggers | Settings | ❌ | ❌ |
| Send Text | N/A | ✅ | ✅ |
| Set Title | N/A | ✅ | ✅ |
| Create Window | N/A | ✅ | ✅ |

---

## New in 3.6.x

| Feature | Version | Description |
|---------|---------|-------------|
| **Window Projects** | 3.6.x | Archive/restore window arrangements in project hierarchy |
| **Session Logging** | 3.6.x | Multi-format recording (raw, text, HTML, asciinema) |
| **AI Chat** | 3.5+ | Full AI assistant with 7 permission categories |
| **Codecierge** | 3.5+ | AI code assistant in Toolbelt |
| **Composer** | 3.5+ | Native command editor replacing shell prompt |
| **Web Browser** | 3.5+ | Built-in web browsing |
| **Blocks** | 3.6.9 | Foldable code block regions via escape sequences |
| **Buttons** | 3.6.9 | Clickable buttons via escape sequences |
| **Open Quickly** | 3.5+ | Fast session search (`⌘⇧O`) |
| **Advanced Paste** | 3.5+ | Enhanced paste with transforms |
| **PolyModalAlert** | API 2.12+ | Rich Python API dialogs |
| **4 New Triggers** | API 2.10+ | Fold, SGR, BufferInput, SetNamedMark |

---

## Related Documentation

- [Individual Feature Docs](./split-panes.md)
- [Python API Guide](../03-scripting/python-api-guide.md)
- [Triggers](./triggers.md)
- [Shell Integration](./shell-integration.md)
- [Session Logging](./session-logging.md)
- [Window Projects](./window-projects.md)
