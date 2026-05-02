# VS Code + tmux Integration Guide

**Tested on:** Linux (Ubuntu) + VS Code Remote SSH

---

## Quick Start

```bash
# 1. Create tmux session
tmux new-session -d -s nova

# 2. Add VS Code terminal profile
python3 meshterm/scripts/vscode_profile_manager.py add nova \
    --workspace /path/to/.code-workspace

# 3. Reload VS Code (Ctrl+Shift+P → Reload Window)

# 4. Click terminal + dropdown → nova-tmux
```

---

## How It Works

VS Code terminal profiles appear in the dropdown next to the + button
in the terminal panel. Each profile defines a shell command that runs
when selected. Our profiles run:

```bash
eval "$(~/miniconda3/bin/conda shell.bash hook)" && \
    conda activate claude_mesh && \
    tmux new-session -A -s nova
```

This:
1. Activates conda `claude_mesh` environment (Python 3.12 + meshterm + claude-mesh)
2. Attaches to `nova` tmux session (creates if absent, `-A` flag)
3. Terminal tab shows as "nova-tmux" with colored icon

---

## Profile Manager Usage

### Add a profile

```bash
python3 vscode_profile_manager.py add nova --workspace ~/project/.code-workspace
# Creates tmux session 'nova' + adds 'nova-tmux' profile to workspace
```

Options:
- `--color red|green|blue|cyan|yellow|magenta|white` — tab color
- `--conda-env ENV` — conda environment (default: claude_mesh)
- `--no-create` — skip tmux session creation

### Add multiple workers

```bash
python3 vscode_profile_manager.py add forge --workspace ~/project/.code-workspace --color red
python3 vscode_profile_manager.py add sentinel --workspace ~/project/.code-workspace --color green
python3 vscode_profile_manager.py add weaver --workspace ~/project/.code-workspace --color blue
```

### List profiles

```bash
python3 vscode_profile_manager.py list --workspace ~/project/.code-workspace
```

### Remove a profile

```bash
python3 vscode_profile_manager.py remove nova --workspace ~/project/.code-workspace
```

### Status

```bash
python3 vscode_profile_manager.py status
# Shows tmux sessions + meshterm status
```

---

## Where Profiles Live

```
.code-workspace file → settings → terminal.integrated.profiles.linux
```

Example in workspace file:
```jsonc
"terminal.integrated.profiles.linux": {
    "nova-tmux": {
        "path": "bash",
        "args": ["-c", "eval ... && conda activate claude_mesh && tmux new-session -A -s nova"],
        "icon": "server-process",
        "color": "terminal.ansiCyan",
        "overrideName": true
    },
    "bash": {
        "path": "bash",
        "icon": "terminal"
    }
}
```

---

## Colony Worker Colors

| Worker | Color | Icon |
|--------|-------|------|
| nova | Cyan | server-process |
| forge | Red | flame |
| sentinel | Green | shield |
| weaver | Blue | git-merge |
| eagle | Yellow | terminal |
| nebula | Magenta | terminal |
| titan | White | terminal |

---

## Troubleshooting

### Profile not showing in dropdown

1. **Reload Window:** Ctrl+Shift+P → "Reload Window"
2. **Check file:** grep for `nova-tmux` in your .code-workspace
3. **JSON validity:** VS Code silently ignores invalid JSONC
4. **Remote SSH:** Profile must be in workspace settings, not Machine settings

### tmux session not found

```bash
# Check existing sessions
tmux ls

# Create manually
tmux new-session -d -s nova

# Verify
tmux has-session -t nova && echo OK
```

### conda activate fails

```bash
# Non-interactive bash needs hook initialization
eval "$(~/miniconda3/bin/conda shell.bash hook)"
conda activate claude_mesh
python3 --version  # Should show 3.11+
```

### Dropdown shows folders, not profiles

The + button dropdown shows WORKING DIRECTORY choices.
The small arrow NEXT TO the + button shows PROFILE choices.
Click the arrow, not the + button itself.

---

## Lessons Learned (2026-04-13 Session)

1. **VS Code Remote SSH reads workspace settings** — Machine settings
   (`~/.vscode-server/data/Machine/settings.json`) may NOT show terminal
   profiles. Put them in the `.code-workspace` file.

2. **conda activate needs eval hook** in non-interactive bash. Plain
   `conda activate` fails silently. Use:
   `eval "$(~/miniconda3/bin/conda shell.bash hook)" && conda activate ENV`

3. **tmux new-session -A** is idempotent — creates if absent, attaches
   if exists. Safer than `attach-session` which fails if session doesn't exist.

4. **NFS mount impossible over WAN** — A peer on a different continent
   cannot NFS-mount across the public internet. Use SCP over SSH tunnel
   for file transfer between geographically distant hosts.

5. **JSONC comments break standard parsers** — VS Code workspace files
   use JSONC (JSON with Comments). Standard `json.loads()` fails on `//` comments.
   Use regex stripping or dedicated JSONC parser.

6. **Profile dropdown vs folder dropdown** — they look similar but are
   different UI elements. Profile is the small arrow next to +, folder
   is the + button itself.
