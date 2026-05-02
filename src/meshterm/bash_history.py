"""
bash_history.py — Shell command history reader

Reads ~/.bash_history (or custom path) for pattern searches and recent
command inspection. Complements jsonl_history.py for cross-session
shell-level forensics.

Usage:
    from meshterm import BashHistory
    hist = BashHistory()
    print(f"Total commands: {len(hist)}")
    for cmd in hist.recent(5):
        print(cmd)
    for cmd in hist.search("ssacli"):
        print(cmd)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator, Optional


class BashHistory:
    """Simple reader for ~/.bash_history files.

    Note: bash writes to history file on shell exit (unless histappend is set).
    For real-time access, use the HISTFILE environment variable or rely on
    history -a commits.
    """

    def __init__(self, path: Optional[Path] = None):
        if path is None:
            env_hist = os.environ.get("HISTFILE")
            if env_hist:
                path = Path(env_hist)
            else:
                path = Path.home() / ".bash_history"
        self.path = Path(path)
        self._lines: list[str] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._lines = []
            return
        try:
            content = self.path.read_text(errors="replace")
        except (OSError, PermissionError):
            self._lines = []
            return
        self._lines = [line for line in content.splitlines() if line.strip()]

    def reload(self) -> None:
        self._load()

    def __len__(self) -> int:
        return len(self._lines)

    def __iter__(self) -> Iterator[str]:
        return iter(self._lines)

    def recent(self, n: int = 20) -> list[str]:
        """Return the last N commands."""
        return self._lines[-n:]

    def search(self, pattern: str, case_insensitive: bool = True) -> list[str]:
        """Return commands matching substring `pattern`."""
        if case_insensitive:
            p = pattern.lower()
            return [line for line in self._lines if p in line.lower()]
        return [line for line in self._lines if pattern in line]

    def count_by_command(self, top_n: int = 10) -> list[tuple[str, int]]:
        """Return most-used commands (first word) sorted by frequency."""
        counts: dict[str, int] = {}
        for line in self._lines:
            first = line.split()[:1]
            if first:
                cmd = first[0]
                counts[cmd] = counts.get(cmd, 0) + 1
        return sorted(counts.items(), key=lambda x: -x[1])[:top_n]
