"""VS Code terminal profile management for meshterm workers.

This module powers the ``meshterm vscode-profile`` CLI subgroup. It manages
VS Code ``.code-workspace`` files to add/list/inspect **terminal profiles**
that attach VS Code's integrated terminal to a named tmux session, so users
can pick a worker session from the VS Code terminal dropdown and get a
live view of that worker's pane.

Pattern
-------

The pattern: a ``.code-workspace`` file declares a ``terminal.integrated.profiles``
entry that runs ``tmux attach -t <session-name>`` (or ``tmux new -A``) when the
profile is selected. VS Code's integrated terminal then renders the tmux pane
directly, with full keyboard/mouse interaction.

This module is the distilled form of that pattern, upstreamed into
the meshterm package proper so it's importable as
``from meshterm.vscode_profiles import ...`` and testable from the unit
suite.

Three profiles per worker
-------------------------

For each worker, we add **three** VS Code terminal profiles:

======================= ===================================== ==================
Profile key             tmux command                          Purpose
======================= ===================================== ==================
``{name}-tmux``         ``tmux new-session -A -s {name}``     Main (idempotent)
``{Name}-Claude``       ``tmux attach-session -t {name}``     Strict attach
``{Name}-New``          ``tmux new-session -A -s {name}-new`` Parallel scratch
======================= ===================================== ==================

Why three instead of one? Different tasks need different semantics:

* ``-tmux`` is the safe default — attach if exists, create if not.
* ``-Claude`` errors if the session is missing — catches bugs where a
  worker didn't start.
* ``-New`` opens a second session for throwaway work without touching
  the main pane.

Colony color and icon convention
---------------------------------

* nova → ``terminal.ansiCyan``
* forge → ``terminal.ansiRed``
* sentinel → ``terminal.ansiGreen``
* weaver → ``terminal.ansiBlue``

Icons: ``server-process`` (main), ``hubot`` (attach), ``add`` (new).

All profiles set ``overrideName: true`` so the profile display name stays
as the VS Code tab title (tmux or the shell can't rename it mid-session).

Design notes
------------

* **Idempotent** — adding the same worker twice returns a clear "already
  exists" result without duplicating entries.
* **Atomic write** — writes to a temp file, ``os.replace``'s into place,
  so a crash mid-write leaves the workspace file intact.
* **Backup by default** — a ``.bak`` copy is written before modification.
  Pass ``backup=False`` to disable.
* **Dry-run mode** — ``dry_run=True`` returns the would-be result without
  touching disk.
* **JSONC-friendly** — ``.code-workspace`` files use JSON-with-comments.
  This module uses structural anchoring (regex to find the
  ``terminal.integrated.profiles.linux`` block) instead of full JSON
  parsing, so comments survive the edit.
* **Conda-aware** — activation can be a custom env, a custom base path,
  or fully skipped (``conda_env=None``) for plain-bash hosts.
* **Color override** — callers can supply an explicit color, or fall
  back to the colony convention, or fall back to the default yellow.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Final


# ── Defaults and convention ──

DEFAULT_CONDA_ENV: Final[str] = "claude_mesh"
"""Conda environment activated by generated profiles unless overridden."""

DEFAULT_CONDA_BASE: Final[str] = "~/miniconda3"
"""Conda installation root used to compute the activation hook."""

DEFAULT_COLOR: Final[str] = "terminal.ansiYellow"
"""Fallback color for workers not listed in ``COLOR_MAP``."""

COLOR_MAP: Final[dict[str, str]] = {
    "nova": "terminal.ansiCyan",
    "forge": "terminal.ansiRed",
    "sentinel": "terminal.ansiGreen",
    "weaver": "terminal.ansiBlue",
}
"""Colony-wide color convention (Poseidon, 2026-04-13)."""

ICON_MAIN: Final[str] = "server-process"
ICON_ATTACH: Final[str] = "hubot"
ICON_NEW: Final[str] = "add"

PROFILE_SUFFIXES: Final[tuple[str, str, str]] = ("-tmux", "-Claude", "-New")
"""Suffixes applied to a worker name to form the 3 profile keys."""


# ── Pure helpers (no filesystem, easy to test) ──

def build_conda_hook(
    env: str = DEFAULT_CONDA_ENV,
    base: str = DEFAULT_CONDA_BASE,
) -> str:
    """Return the bash snippet that activates a conda env.

    The result is intended to be prepended to a tmux command inside a
    VS Code terminal profile ``args`` list, e.g.::

        bash -c "<hook> && tmux new-session -A -s nova"

    Args:
        env: Conda environment name to activate.
        base: Conda installation root (e.g. ``~/miniconda3``, ``~/mambaforge``).

    Returns:
        A bash fragment like
        ``eval "$(~/miniconda3/bin/conda shell.bash hook)" && conda activate claude_mesh``.
    """
    return f'eval "$({base}/bin/conda shell.bash hook)" && conda activate {env}'


def resolve_color(session: str, override: str | None = None) -> str:
    """Pick the color for a given worker.

    Precedence: explicit ``override`` > ``COLOR_MAP`` entry > ``DEFAULT_COLOR``.
    """
    if override:
        return override
    return COLOR_MAP.get(session, DEFAULT_COLOR)


def profile_keys(session: str) -> tuple[str, str, str]:
    """Return the 3 profile dict keys for a given worker name.

    Capitalization matches Poseidon's original convention::

        ("nova-tmux", "Nova-Claude", "Nova-New")
    """
    cap = session.capitalize()
    return (f"{session}-tmux", f"{cap}-Claude", f"{cap}-New")


def build_profile_block(
    session: str,
    *,
    conda_hook: str | None = None,
    color: str | None = None,
) -> dict[str, dict[str, object]]:
    """Build the 3 VS Code terminal profile dicts for a given worker.

    Args:
        session: Worker name (e.g. ``"nova"``).
        conda_hook: Optional bash snippet to prepend to each tmux command.
            Pass ``None`` for plain-bash hosts (no conda activation).
        color: Optional explicit color override. Defaults to
            ``COLOR_MAP[session]`` if present, else ``DEFAULT_COLOR``.

    Returns:
        A dict mapping profile key to profile body. Three entries:
        ``{session}-tmux``, ``{Cap}-Claude``, ``{Cap}-New``.
    """
    color_final = resolve_color(session, color)
    prefix = f"{conda_hook} && " if conda_hook else ""
    main_key, attach_key, new_key = profile_keys(session)

    return {
        main_key: {
            "path": "bash",
            "args": ["-c", f"{prefix}tmux new-session -A -s {session}"],
            "icon": ICON_MAIN,
            "color": color_final,
            "overrideName": True,
        },
        attach_key: {
            "path": "bash",
            "args": ["-c", f"{prefix}tmux attach-session -t {session}"],
            "icon": ICON_ATTACH,
            "color": color_final,
            "overrideName": True,
        },
        new_key: {
            "path": "bash",
            "args": ["-c", f"{prefix}tmux new-session -A -s {session}-new"],
            "icon": ICON_NEW,
            "color": color_final,
            "overrideName": True,
        },
    }


def profile_exists_in_text(session: str, workspace_content: str) -> bool:
    """Return True if any of the 3 profile keys for ``session`` already exist.

    Used for idempotency checks. Looks for the literal profile key
    appearing as a JSON object key (``"nova-tmux":``).
    """
    for key in profile_keys(session):
        if re.search(rf'"{re.escape(key)}"\s*:', workspace_content):
            return True
    return False


def format_profile_block_jsonc(
    profiles: dict[str, dict[str, object]],
    indent: int = 6,
) -> str:
    """Render a dict of profiles as JSONC-compatible text.

    The output is designed to be inserted into an existing
    ``terminal.integrated.profiles.linux`` block. Each profile becomes
    a ``"key": { ... },`` entry indented at ``indent`` spaces from the
    left margin, matching VS Code's default code-workspace formatting.
    """
    pad = " " * indent
    lines: list[str] = []
    for key, profile in profiles.items():
        rendered = json.dumps(profile, indent=2).replace("\n", "\n" + pad)
        lines.append(f'{pad}"{key}": {rendered},')
    return "\n".join(lines)


# ── tmux helpers ──

def tmux_session_exists(name: str, timeout: float = 5.0) -> bool:
    """Return True if a tmux session with the given name exists.

    Returns False if tmux is not installed or the command times out.
    """
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", name],
            capture_output=True,
            timeout=timeout,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def ensure_tmux_session(name: str, timeout: float = 5.0) -> bool:
    """Create a tmux session with the given name if it doesn't exist.

    Returns True if the session exists (already-existing or newly created).
    Returns False if tmux is missing, the creation times out, or the
    creation fails.
    """
    if tmux_session_exists(name, timeout=timeout):
        return True
    try:
        result = subprocess.run(
            ["tmux", "new-session", "-d", "-s", name],
            capture_output=True,
            timeout=timeout,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# ── Workspace-file mutation ──

_ANCHOR_PATTERNS: Final[tuple[str, ...]] = (
    # Preferred: insert right before the existing "bash" profile
    r'^(?P<pad>[ \t]+)"bash"\s*:\s*\{',
    # Second: insert before any existing tmux-backed profile
    r'^(?P<pad>[ \t]+)"[A-Za-z0-9_\-]+-tmux"\s*:\s*\{',
    # Last resort: insert just after the opening brace of profiles.linux
    r'"terminal\.integrated\.profiles\.linux"\s*:\s*\{(?P<nl>\s*)',
)


def _find_insertion_point(content: str) -> tuple[int, str] | None:
    """Find the character offset to insert new profiles and the indent to use.

    Returns ``(offset, indent)`` where ``offset`` is the position in
    ``content`` to splice in the new text, and ``indent`` is a string of
    leading whitespace to use for each new profile key.

    Returns ``None`` if no anchor was found.
    """
    for pattern in _ANCHOR_PATTERNS:
        m = re.search(pattern, content, re.MULTILINE)
        if not m:
            continue
        if "profiles.linux" in pattern:
            return m.end(), "      "
        pad = m.group("pad")
        return m.start(), pad
    return None


def add_profiles_to_workspace(
    workspace_path: Path,
    session: str,
    *,
    conda_env: str | None = DEFAULT_CONDA_ENV,
    conda_base: str = DEFAULT_CONDA_BASE,
    color: str | None = None,
    dry_run: bool = False,
    backup: bool = True,
) -> tuple[bool, str]:
    """Add the 3 worker profiles to a VS Code workspace file.

    Idempotent: if any of the 3 keys already exist, returns ``(False,
    "already exists")`` without modifying the file.

    Atomic: writes to a temp file in the same directory and uses
    ``os.replace`` so a crash leaves the original intact. A ``.bak``
    copy is created unless ``backup=False``.

    Args:
        workspace_path: Path to a ``.code-workspace`` file.
        session: Worker name (e.g. ``"nova"``).
        conda_env: Conda env to activate, or ``None`` for no conda.
        conda_base: Conda installation root.
        color: Optional color override.
        dry_run: If True, don't write to disk; return the preview message.
        backup: If True, write ``workspace_path.bak`` before mutation.

    Returns:
        ``(ok, message)`` tuple. ``ok`` is True on successful add (or
        successful dry-run preview); False on idempotency hit or any
        structural failure.
    """
    if not workspace_path.exists():
        return False, f"workspace file not found: {workspace_path}"

    content = workspace_path.read_text()

    if profile_exists_in_text(session, content):
        return False, f"profiles for '{session}' already present in {workspace_path.name}"

    conda_hook = build_conda_hook(conda_env, conda_base) if conda_env else None
    profiles = build_profile_block(session, conda_hook=conda_hook, color=color)

    anchor = _find_insertion_point(content)
    if anchor is None:
        return (
            False,
            "could not find an insertion point; expected a 'bash' profile, "
            "an existing '*-tmux' profile, or a 'terminal.integrated.profiles.linux' "
            "block in the workspace file",
        )

    offset, pad = anchor
    block_text = format_profile_block_jsonc(profiles, indent=len(pad))
    new_content = content[:offset] + block_text + "\n" + content[offset:]

    if dry_run:
        keys = ", ".join(profiles.keys())
        return True, f"DRY RUN: would add 3 profiles ({keys})"

    if backup:
        backup_path = workspace_path.with_suffix(workspace_path.suffix + ".bak")
        shutil.copy2(workspace_path, backup_path)

    tmp_path = workspace_path.with_suffix(workspace_path.suffix + ".tmp")
    tmp_path.write_text(new_content)
    os.replace(tmp_path, workspace_path)

    keys = ", ".join(profiles.keys())
    return True, f"added 3 profiles: {keys}"


def list_profiles_in_workspace(
    workspace_path: Path,
) -> list[tuple[str, str]]:
    """Return ``(name, type)`` tuples for every terminal profile in a workspace.

    ``type`` is ``"tmux"`` if the profile's command mentions tmux,
    otherwise ``"shell"``. Uses regex pattern matching (not full JSON
    parsing) so comments and trailing commas in ``.code-workspace``
    files are tolerated.
    """
    if not workspace_path.exists():
        return []

    content = workspace_path.read_text()
    results: list[tuple[str, str]] = []
    seen: set[str] = set()

    # Match: "profile-name": { ... "path": "...", ... "args": [...] ... }
    pattern = re.compile(
        r'"([A-Za-z0-9_\-]+)"\s*:\s*\{[^{}]*?"path"\s*:\s*"([^"]+)"[^{}]*?\}',
        re.DOTALL,
    )
    for match in pattern.finditer(content):
        name = match.group(1)
        if name in seen:
            continue
        seen.add(name)
        body = match.group(0)
        ptype = "tmux" if "tmux" in body else "shell"
        results.append((name, ptype))

    return results


# ── Status reporting ──

def colony_status(timeout: float = 5.0) -> dict[str, str]:
    """Return a dict summarizing tmux sessions and meshterm CLI availability.

    Keys:
        ``tmux``: ``tmux ls`` output, or ``"no sessions"``, or
            ``"tmux not installed"``.
        ``meshterm``: ``meshterm --version`` output, or ``"not available"``,
            or ``"meshterm not on PATH"``.
    """
    status: dict[str, str] = {}

    try:
        result = subprocess.run(
            ["tmux", "ls"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0 and result.stdout.strip():
            status["tmux"] = result.stdout.strip()
        else:
            status["tmux"] = "no sessions"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        status["tmux"] = "tmux not installed"

    try:
        result = subprocess.run(
            ["meshterm", "--version"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            status["meshterm"] = result.stdout.strip() or "(ok)"
        else:
            status["meshterm"] = "not available"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        status["meshterm"] = "meshterm not on PATH"

    return status
