"""Per-session idle checker using screen hash + prompt pattern.

Lower-level building block for idle detection. Each IdleChecker tracks
one session's state via two signals:

  1. Screen hash (SHA-256) — unchanged hash across polls = screen stable
  2. Prompt pattern — regex match on last non-empty line = shell waiting

Both signals must be true for `min_stable_polls` consecutive polls
before a session is classified as IDLE.

Usage:
    checker = IdleChecker()
    result = checker.check(screen_lines)
    if result.state == IdleState.IDLE:
        print(f"Idle for {result.idle_seconds:.0f}s")
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from enum import Enum


class IdleState(Enum):
    """Session activity state."""
    IDLE = "IDLE"
    BUSY = "BUSY"
    UNKNOWN = "UNKNOWN"


@dataclass
class IdleResult:
    """Result of a single idle check."""
    state: IdleState
    idle_seconds: float = 0.0
    screen_hash: str = ""
    prompt_matched: bool = False
    consecutive_stable_polls: int = 0


@dataclass
class IdleCheckerConfig:
    """Configuration for idle checking."""
    # Prompt patterns that indicate shell is waiting for input
    prompt_patterns: list[str] = field(default_factory=lambda: [
        r"[$#>❯»]\s*$",           # common shell prompts
        r">>>\s*$",                # Python REPL
        r"In \[\d+\]:\s*$",       # IPython/Jupyter
        r"^\s*$",                  # empty line (cursor at prompt)
    ])
    # How long idle must persist before is_timed_out() returns True
    idle_timeout: float = 900.0    # 15 minutes default
    # Consecutive stable+prompt polls required to confirm IDLE
    min_stable_polls: int = 3


class IdleChecker:
    """Per-session idle checker using screen hash + prompt pattern.

    Tracks one session. Create one IdleChecker per pane/session.

    Detection algorithm:
      1. Hash current screen content (SHA-256)
      2. Compare with previous hash → screen_changed?
      3. Check last non-empty line against prompt patterns
      4. If screen stable + prompt visible for N consecutive polls → IDLE
      5. If screen changed → immediate BUSY, reset counters

    Example:
        checker = IdleChecker()

        # First check — always UNKNOWN (no baseline)
        r = checker.check(["$ "])
        assert r.state == IdleState.UNKNOWN

        # Subsequent stable checks → eventually IDLE
        for _ in range(3):
            r = checker.check(["$ "])
        assert r.state == IdleState.IDLE
    """

    def __init__(self, config: IdleCheckerConfig | None = None):
        self._config = config or IdleCheckerConfig()
        self._prompt_re = re.compile("|".join(self._config.prompt_patterns))
        self._prev_hash: str | None = None
        self._stable_polls: int = 0
        self._idle_since: float | None = None

    @property
    def config(self) -> IdleCheckerConfig:
        """Current configuration."""
        return self._config

    @property
    def idle_seconds(self) -> float:
        """Seconds since idle started (0 if not idle)."""
        if self._idle_since is None:
            return 0.0
        return time.monotonic() - self._idle_since

    @property
    def consecutive_stable_polls(self) -> int:
        """Number of consecutive polls with unchanged screen."""
        return self._stable_polls

    # ── Core API ──

    @staticmethod
    def screen_hash(lines: list[str]) -> str:
        """Compute SHA-256 hash of screen content.

        Joins lines with newline and hashes the UTF-8 bytes.
        Deterministic: same content always produces same hash.
        """
        content = "\n".join(lines)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def detect_prompt(self, lines: list[str]) -> bool:
        """Check if the last non-empty line matches a prompt pattern.

        Scans from bottom of screen upward, finds first non-blank
        line, and tests against configured prompt patterns.

        Returns False if all lines are empty.
        """
        for line in reversed(lines):
            stripped = line.strip()
            if stripped:
                return bool(self._prompt_re.search(line))
        # All empty — matches the r"^\\s*$" pattern
        return bool(self._prompt_re.search(""))

    def check(self, lines: list[str]) -> IdleResult:
        """Check idle state from current screen lines.

        Call this once per poll interval with the latest screen capture.

        Returns:
            IdleResult with current state, idle duration, hash, etc.
        """
        now = time.monotonic()
        current_hash = self.screen_hash(lines)
        prompt_matched = self.detect_prompt(lines)

        first_check = self._prev_hash is None
        screen_changed = (not first_check and current_hash != self._prev_hash)
        self._prev_hash = current_hash

        if first_check:
            # First check — need baseline, can't determine state yet
            state = IdleState.UNKNOWN
            self._stable_polls = 0
            self._idle_since = None
        elif screen_changed:
            # Screen content changed → BUSY, reset all counters
            state = IdleState.BUSY
            self._stable_polls = 0
            self._idle_since = None
        else:
            # Screen is stable (hash unchanged)
            self._stable_polls += 1

            if (prompt_matched
                    and self._stable_polls >= self._config.min_stable_polls):
                state = IdleState.IDLE
                if self._idle_since is None:
                    self._idle_since = now
            else:
                state = IdleState.BUSY

        idle_secs = now - self._idle_since if self._idle_since else 0.0

        return IdleResult(
            state=state,
            idle_seconds=idle_secs,
            screen_hash=current_hash,
            prompt_matched=prompt_matched,
            consecutive_stable_polls=self._stable_polls,
        )

    def is_timed_out(self) -> bool:
        """Check if idle duration exceeds configured timeout.

        Returns True only when:
          1. Session is currently IDLE
          2. Has been idle for >= idle_timeout seconds
        """
        if self._idle_since is None:
            return False
        return (time.monotonic() - self._idle_since) >= self._config.idle_timeout

    def reset(self) -> None:
        """Reset all internal state.

        Next check() call will return UNKNOWN (no baseline).
        """
        self._prev_hash = None
        self._stable_polls = 0
        self._idle_since = None
