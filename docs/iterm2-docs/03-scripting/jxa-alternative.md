# JavaScript for Automation (JXA) Alternative

> Using JavaScript instead of AppleScript for iTerm2 automation.

---

## Overview

JXA (JavaScript for Automation) is Apple's JavaScript-based alternative to AppleScript, available since OS X 10.10. It can control iTerm2 using the same object model as AppleScript.

---

## When to Use JXA

| Use Case | Recommendation |
|----------|----------------|
| New automation | Python API (best) |
| JavaScript preference | JXA (acceptable) |
| Shortcuts.app integration | JXA or AppleScript |
| Cross-app automation | JXA or AppleScript |
| Complex iTerm2 control | Python API |

---

## Basic Syntax

### AppleScript vs JXA

```applescript
-- AppleScript
tell application "iTerm2"
    create window with default profile
end tell
```

```javascript
// JXA
const iTerm = Application("iTerm2");
iTerm.createWindow();
```

---

## Common Operations

### Create Window

```javascript
#!/usr/bin/env osascript -l JavaScript

function run() {
    const iTerm = Application("iTerm2");
    iTerm.activate();

    const window = iTerm.createWindow();
    return "Window created";
}
```

### Access Current Session

```javascript
function run() {
    const iTerm = Application("iTerm2");
    const window = iTerm.currentWindow();
    const tab = window.currentTab();
    const session = tab.currentSession();

    return session.id();
}
```

### Write Text

```javascript
function run() {
    const iTerm = Application("iTerm2");
    const session = iTerm.currentWindow()
                         .currentTab()
                         .currentSession();

    session.write({ text: "ls -la" });
    return "Command sent";
}
```

### Set Session Name

```javascript
function run() {
    const iTerm = Application("iTerm2");
    const session = iTerm.currentWindow()
                         .currentTab()
                         .currentSession();

    session.name = "My Session";
    return "Name set";
}
```

### Split Pane

```javascript
function run() {
    const iTerm = Application("iTerm2");
    const session = iTerm.currentWindow()
                         .currentTab()
                         .currentSession();

    session.splitVertically({ profile: "Default" });
    return "Split created";
}
```

---

## Full Example: Dev Layout

```javascript
#!/usr/bin/env osascript -l JavaScript

function run() {
    const iTerm = Application("iTerm2");
    iTerm.activate();

    // Create window
    const window = iTerm.createWindow();
    const tab = window.currentTab();
    const leftSession = tab.currentSession();

    // Configure left pane
    leftSession.name = "Editor";
    leftSession.write({ text: "vim ." });

    // Split and configure right pane
    leftSession.splitVertically({ profile: "Default" });

    // Get all sessions in tab
    const sessions = tab.sessions();
    const rightSession = sessions[1];

    rightSession.name = "Terminal";
    rightSession.write({ text: "npm run dev" });

    return "Dev layout created";
}
```

---

## Running JXA Scripts

### Command Line

```bash
osascript -l JavaScript script.js
```

### With Shebang

```javascript
#!/usr/bin/env osascript -l JavaScript
// ... script content
```

```bash
chmod +x script.js
./script.js
```

### From Bash

```bash
osascript -l JavaScript << 'EOF'
function run() {
    const iTerm = Application("iTerm2");
    iTerm.createWindow();
    return "Done";
}
EOF
```

---

## Error Handling

```javascript
function run() {
    try {
        const iTerm = Application("iTerm2");
        const session = iTerm.currentWindow()
                             .currentTab()
                             .currentSession();
        session.write({ text: "ls" });
        return "Success";
    } catch (error) {
        return "Error: " + error.message;
    }
}
```

---

## Comparison with Python API

| Feature | JXA | Python API |
|---------|-----|------------|
| Event subscription | ❌ | ✅ |
| Async operations | ❌ | ✅ |
| Status bar components | ❌ | ✅ |
| Variable monitoring | ❌ | ✅ |
| Modern syntax | ✅ | ✅ |
| Documentation | Limited | Extensive |
| Shortcuts.app | ✅ | ❌ |

---

## Recommendation

For iTerm2-specific automation:
- **Use Python API** - Full features, best documentation

For cross-app automation (Finder + iTerm2 + Mail, etc.):
- **Use JXA** - Better than AppleScript syntax

---

## Related Documentation

- [Python API Guide](./python-api-guide.md)
- [AppleScript Legacy](./applescript-legacy.md)
- [Workflow Overview](./workflow-overview.md)
