# When to Use What

> Decision guide for terminal and automation choices.

---

## Terminal Decision Tree

```
Need a terminal emulator?
         │
    ┌────┴────┐
    │         │
 macOS?    Other OS?
    │         │
    ▼         ▼
 ┌──────┐  ┌──────────┐
 │Need  │  │Alacritty │
 │max   │  │Kitty     │
 │feat? │  │WezTerm   │
 └──┬───┘  └──────────┘
    │
 ┌──┴──┐
 │     │
Yes    No
 │      │
 ▼      ▼
iTerm2  Speed priority?
         │
      ┌──┴──┐
      │     │
     Yes    No
      │     │
      ▼     ▼
  Alacritty Kitty
```

---

## Scripting Decision Matrix

| Your Need | Use This |
|-----------|----------|
| Control iTerm2 windows/sessions | Python API |
| Quick command from bash | osascript heredoc |
| Status bar customization | Python API |
| Event-driven automation | Python API |
| Shortcuts.app integration | AppleScript |
| Control multiple apps | Hammerspoon |
| Existing AppleScript code | Keep or migrate |

---

## Quick Reference

### For New Projects

**Always use Python API:**
- Full async support
- Event subscription
- Better error handling
- Active development

### For Legacy Code

**Evaluate migration cost:**
- Simple scripts → Keep with fixes
- Complex scripts → Migrate to Python
- Breaking issues → Migrate immediately

### For Cross-App Automation

**Consider alternatives:**
- Hammerspoon (Lua)
- Keyboard Maestro (GUI)
- Shortcuts.app (Simple)

---

## Related Documentation

- [Terminal Emulators](./terminal-emulators.md)
- [Migration Guide](../03-scripting/migration-guide.md)
