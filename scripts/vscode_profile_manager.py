#!/usr/bin/env python3
"""
meshterm VS Code Terminal Profile Manager v2.0

Manages VS Code terminal profiles for meshterm/tmux colony sessions.
Creates tmux sessions + injects terminal profiles into VS Code workspace files.

Usage (standalone):
    python3 vscode_profile_manager.py add nova --workspace /path/to/.code-workspace
    python3 vscode_profile_manager.py add forge --workspace /path/to/.code-workspace --color red
    python3 vscode_profile_manager.py list --workspace /path/to/.code-workspace
    python3 vscode_profile_manager.py remove nova --workspace /path/to/.code-workspace
    python3 vscode_profile_manager.py status

Usage (meshterm CLI — after Eagle integrates):
    meshterm vscode-profile add nova --workspace /path/to/.code-workspace
    meshterm vscode-profile list --workspace /path/to/.code-workspace

Based on: Colony session 2026-04-13 (Dr. Umit + Nebula + Poseidon)

Lessons learned:
  - VS Code Remote SSH reads profiles from workspace settings
  - Profile must be in terminal.integrated.profiles.linux inside .code-workspace
  - tmux new-session -A is idempotent (create or attach)
  - conda activate needs eval hook in non-interactive bash
  - Profile dropdown is separate from folder dropdown (+ button arrow)
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


# ── Configuration ──

COLOR_MAP: dict[str, str] = {
    "nova": "terminal.ansiCyan",
    "forge": "terminal.ansiRed",
    "sentinel": "terminal.ansiGreen",
    "weaver": "terminal.ansiBlue",
    "eagle": "terminal.ansiYellow",
    "nebula": "terminal.ansiMagenta",
    "titan": "terminal.ansiWhite",
}

ICON_MAP: dict[str, str] = {
    "nova": "server-process",
    "forge": "flame",
    "sentinel": "shield",
    "weaver": "git-merge",
    "default": "terminal",
}


# ── tmux Operations ──

def tmux_session_exists(name: str) -> bool:
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", name],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def create_tmux_session(name: str) -> bool:
    if tmux_session_exists(name):
        print(f"  tmux '{name}' already exists")
        return True
    try:
        result = subprocess.run(
            ["tmux", "new-session", "-d", "-s", name],
            capture_output=True, timeout=5
        )
        ok = result.returncode == 0
        print(f"  tmux '{name}' {'created' if ok else 'FAILED'}")
        return ok
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  tmux '{name}' FAILED: {e}")
        return False


def list_tmux_sessions() -> list[str]:
    try:
        result = subprocess.run(
            ["tmux", "ls"], capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip().splitlines() if result.returncode == 0 else []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


# ── Workspace File Operations ──

def build_profile_block(
    session_name: str,
    color: Optional[str] = None,
    conda_env: str = "claude_mesh",
) -> str:
    """Build VS Code terminal profile JSON block for workspace insertion."""
    color = color or COLOR_MAP.get(session_name, "terminal.ansiYellow")
    icon = ICON_MAP.get(session_name, ICON_MAP["default"])

    conda_hook = (
        'eval \\"$(~/miniconda3/bin/conda shell.bash hook)\\" '
        f'&& conda activate {conda_env}'
    )
    tmux_cmd = f'tmux new-session -A -s {session_name}'

    lines = [
        f'      "{session_name}-tmux": {{',
        f'        "path": "bash",',
        f'        "args": ["-c", "{conda_hook} && {tmux_cmd}"],',
        f'        "icon": "{icon}",',
        f'        "color": "{color}",',
        f'        "overrideName": true',
        f'      }},',
    ]
    return "\n".join(lines)


def profile_exists(content: str, session_name: str) -> bool:
    return f'"{session_name}-tmux"' in content


def add_profile(
    session_name: str,
    workspace_path: str,
    color: Optional[str] = None,
    conda_env: str = "claude_mesh",
) -> bool:
    """Add terminal profile to VS Code workspace file."""
    content = Path(workspace_path).read_text(encoding="utf-8")

    if profile_exists(content, session_name):
        print(f"  Profile '{session_name}-tmux' already exists — skipping")
        return True

    # Insert before "bash" profile (anchor point)
    match = re.search(r'      "bash":\s*\{', content)
    if not match:
        print("  ERROR: No 'bash' profile found as insertion anchor")
        print("  Ensure terminal.integrated.profiles.linux has a 'bash' entry")
        return False

    block = build_profile_block(session_name, color, conda_env)
    content = content[:match.start()] + block + "\n" + content[match.start():]

    Path(workspace_path).write_text(content, encoding="utf-8")
    print(f"  Profile '{session_name}-tmux' added")
    return True


def remove_profile(session_name: str, workspace_path: str) -> bool:
    """Remove terminal profile from workspace file."""
    content = Path(workspace_path).read_text(encoding="utf-8")
    key = f'"{session_name}-tmux"'

    if key not in content:
        print(f"  Profile '{session_name}-tmux' not found")
        return False

    pattern = rf'      {re.escape(key)}:\s*\{{[^}}]*\}},?\n?'
    new_content = re.sub(pattern, '', content)

    if new_content == content:
        print(f"  WARNING: Regex removal failed — manual edit needed")
        return False

    Path(workspace_path).write_text(new_content, encoding="utf-8")
    print(f"  Profile '{session_name}-tmux' removed")
    return True


def list_profiles(workspace_path: str) -> list[dict[str, str]]:
    """List all terminal profiles in workspace."""
    content = Path(workspace_path).read_text(encoding="utf-8")
    profiles = []
    in_section = False

    for line in content.splitlines():
        if "terminal.integrated.profiles.linux" in line:
            in_section = True
            continue
        if in_section:
            match = re.match(r'\s+"([^"]+)":\s*\{', line)
            if match:
                name = match.group(1)
                is_tmux = "tmux" in name or "tmux" in content[content.index(line):content.index(line) + 200]
                profiles.append({"name": name, "type": "tmux" if is_tmux else "bash"})
            # Detect section end
            if re.match(r'\s+\},?\s*$', line) and profiles:
                next_lines = content[content.index(line) + len(line):]
                if not re.match(r'\s+"[^"]+"\s*:', next_lines.lstrip()):
                    break
    return profiles


def show_status() -> None:
    print("\n=== tmux sessions ===")
    sessions = list_tmux_sessions()
    for s in sessions:
        print(f"  {s}")
    if not sessions:
        print("  No sessions")

    print("\n=== meshterm ===")
    try:
        result = subprocess.run(
            ["meshterm", "status"], capture_output=True, text=True, timeout=5
        )
        print(result.stdout.strip() if result.returncode == 0 else "  Not available")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("  meshterm CLI not in PATH")


# ── CLI Entrypoint ──

def run_cli(args: Optional[list[str]] = None) -> None:
    """CLI entrypoint — used standalone or by meshterm CLI integration."""
    parser = argparse.ArgumentParser(
        prog="meshterm vscode-profile",
        description="VS Code Terminal Profile Manager for meshterm/tmux sessions",
    )
    sub = parser.add_subparsers(dest="cmd")

    add_p = sub.add_parser("add", help="Add tmux terminal profile to workspace")
    add_p.add_argument("session", help="Session name (nova, forge, sentinel, weaver)")
    add_p.add_argument("--workspace", "-w", required=True,
                       help=".code-workspace file path")
    add_p.add_argument("--color", "-c", default=None,
                       choices=["red", "green", "blue", "cyan", "yellow", "magenta", "white"])
    add_p.add_argument("--conda-env", default="claude_mesh")
    add_p.add_argument("--no-create", action="store_true",
                       help="Don't create tmux session, only add profile")

    rm_p = sub.add_parser("remove", help="Remove terminal profile")
    rm_p.add_argument("session")
    rm_p.add_argument("--workspace", "-w", required=True)

    ls_p = sub.add_parser("list", help="List profiles in workspace")
    ls_p.add_argument("--workspace", "-w", required=True)

    sub.add_parser("status", help="Show tmux + meshterm status")

    parsed = parser.parse_args(args)

    if parsed.cmd == "add":
        color_val = f"terminal.ansi{parsed.color.capitalize()}" if parsed.color else None
        print(f"[meshterm] Adding '{parsed.session}' profile...")
        if not parsed.no_create:
            create_tmux_session(parsed.session)
        if add_profile(parsed.session, parsed.workspace, color_val, parsed.conda_env):
            print(f"[meshterm] Reload VS Code → dropdown → '{parsed.session}-tmux'")
    elif parsed.cmd == "remove":
        remove_profile(parsed.session, parsed.workspace)
    elif parsed.cmd == "list":
        profiles = list_profiles(parsed.workspace)
        print(f"\nProfiles in {parsed.workspace}:")
        for p in profiles:
            marker = " (tmux)" if p["type"] == "tmux" else ""
            print(f"  {p['name']}{marker}")
        if not profiles:
            print("  (none)")
    elif parsed.cmd == "status":
        show_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    run_cli()
