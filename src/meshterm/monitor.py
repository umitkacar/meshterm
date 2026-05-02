"""Monitor daemon — watches all sessions, detects IDLE/BUSY, triggers on idle.

Linux equivalent of Mac's iTerm2 VariableMonitor.

Detection uses two signals:
  1. Screen hash — SHA-256 of captured screen; no change = idle candidate
  2. Prompt pattern — last non-empty line matches shell/REPL prompt

Both must be true for a session to be IDLE.

When ALL sessions are IDLE for ``idle_threshold`` seconds, the cron trigger fires.

Usage:
    from meshterm.monitor import Monitor, MonitorConfig

    monitor = Monitor(backend)
    monitor.on_trigger(lambda dur, ss: print(f"All idle {dur:.0f}s"))
    monitor.start(blocking=True)
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


# ── Enums / dataclasses ──


class SessionState(Enum):
    """Per-session activity state."""
    IDLE = "IDLE"
    BUSY = "BUSY"
    UNKNOWN = "UNKNOWN"


@dataclass
class SessionStatus:
    """Snapshot of one session's idle state at a point in time."""
    pane_id: str
    name: str
    command: str
    state: SessionState
    idle_seconds: float = 0.0
    last_change: float = 0.0       # monotonic timestamp of last screen change
    screen_hash: str = ""          # hex digest of last screen capture
    screen_preview: str = ""       # last non-empty line (debugging)


@dataclass
class MonitorConfig:
    """Knobs for the monitor daemon."""
    # Regex patterns whose match on the last non-empty line means "prompt visible"
    prompt_patterns: list[str] = field(default_factory=lambda: [
        r"[$#>❯»]\s*$",           # common shell prompts (bash, zsh, fish)
        r">>>\s*$",                # Python REPL
        r"In \[\d+\]:\s*$",       # IPython / Jupyter
        r"\(Pdb\)\s*$",           # Python debugger
        r"^\s*$",                  # empty line (cursor on blank prompt)
    ])
    # Seconds all sessions must be idle before trigger fires
    idle_threshold: float = 900.0  # 15 minutes
    # Seconds between polls
    poll_interval: float = 5.0
    # Consecutive stable polls required before marking IDLE
    min_idle_polls: int = 3


# ── Monitor daemon ──


class Monitor:
    """Watches tmux sessions and fires callbacks when idle threshold is reached.

    Core loop: poll -> hash -> classify -> check threshold -> trigger

    This is the Linux equivalent of Mac iTerm2 VariableMonitor + cron.
    """

    def __init__(self, backend, config: MonitorConfig | None = None):
        self._backend = backend
        self._config = config or MonitorConfig()
        self._prompt_re = re.compile("|".join(self._config.prompt_patterns))

        # Per-pane tracking
        self._last_hashes: dict[str, str] = {}        # pane_id -> sha256 hex
        self._idle_since: dict[str, float] = {}        # pane_id -> monotonic ts
        self._idle_polls: dict[str, int] = {}           # consecutive stable polls
        self._states: dict[str, SessionStatus] = {}

        # Global idle tracking
        self._all_idle_since: float | None = None
        self._trigger_fired: bool = False  # reset when any session goes busy

        # Callbacks
        self._cb_trigger: list[Callable] = []       # (idle_seconds, [SessionStatus])
        self._cb_session_idle: list[Callable] = []   # (SessionStatus,)
        self._cb_session_busy: list[Callable] = []   # (SessionStatus,)

        # Thread control
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    # ── Callback registration ──

    def on_trigger(self, cb: Callable) -> None:
        """Register cron trigger — called when ALL sessions idle past threshold.

        Signature: ``cb(idle_seconds: float, sessions: list[SessionStatus])``
        """
        self._cb_trigger.append(cb)

    def on_session_idle(self, cb: Callable) -> None:
        """Per-session callback when it transitions to IDLE."""
        self._cb_session_idle.append(cb)

    def on_session_busy(self, cb: Callable) -> None:
        """Per-session callback when it transitions to BUSY."""
        self._cb_session_busy.append(cb)

    # ── State query ──

    def get_status(self, pane_id: str) -> SessionStatus | None:
        return self._states.get(pane_id)

    def get_all_statuses(self) -> list[SessionStatus]:
        return list(self._states.values())

    def is_all_idle(self) -> bool:
        if not self._states:
            return False
        return all(s.state == SessionState.IDLE for s in self._states.values())

    def all_idle_duration(self) -> float:
        """Seconds since ALL sessions became idle (0 if any is busy)."""
        if self._all_idle_since is None:
            return 0.0
        return time.monotonic() - self._all_idle_since

    # ── Core detection ──

    @staticmethod
    def _screen_hash(lines: list[str]) -> str:
        """SHA-256 of joined screen lines — fast diff via hash comparison."""
        content = "\n".join(lines).encode("utf-8", errors="replace")
        return hashlib.sha256(content).hexdigest()

    def _last_nonempty_line(self, lines: list[str]) -> str:
        for line in reversed(lines):
            if line.strip():
                return line
        return ""

    def poll_once(self) -> list[SessionStatus]:
        """Run one detection cycle across all sessions.

        Returns list of SessionStatus, one per session.
        """
        now = time.monotonic()
        sessions = self._backend.list_sessions()
        results: list[SessionStatus] = []

        for sess in sessions:
            pid = sess.pane_id
            current_lines = sess._pane.capture_pane()
            current_hash = self._screen_hash(current_lines)
            prev_hash = self._last_hashes.get(pid, "")
            self._last_hashes[pid] = current_hash

            # Signal 1: screen changed?
            screen_changed = current_hash != prev_hash

            # Signal 2: prompt visible?
            last_line = self._last_nonempty_line(current_lines)
            prompt_visible = bool(self._prompt_re.search(last_line))

            # Previous state for transition detection
            prev_state = self._states.get(pid)
            was_idle = prev_state is not None and prev_state.state == SessionState.IDLE

            # Classify
            if screen_changed:
                state = SessionState.BUSY
                self._idle_since.pop(pid, None)
                self._idle_polls[pid] = 0
            else:
                self._idle_polls[pid] = self._idle_polls.get(pid, 0) + 1
                if (prompt_visible
                        and self._idle_polls[pid] >= self._config.min_idle_polls):
                    state = SessionState.IDLE
                    if pid not in self._idle_since:
                        self._idle_since[pid] = now
                else:
                    state = SessionState.BUSY

            idle_secs = (now - self._idle_since[pid]) if pid in self._idle_since else 0.0

            status = SessionStatus(
                pane_id=pid,
                name=sess.name or sess.current_command,
                command=sess.current_command,
                state=state,
                idle_seconds=idle_secs,
                last_change=now if screen_changed else (
                    prev_state.last_change if prev_state else now
                ),
                screen_hash=current_hash[:16],
                screen_preview=last_line[:80],
            )
            self._states[pid] = status
            results.append(status)

            # Transition callbacks
            if state == SessionState.IDLE and not was_idle:
                for cb in self._cb_session_idle:
                    _safe_call(cb, status)
            elif screen_changed and was_idle:
                for cb in self._cb_session_busy:
                    _safe_call(cb, status)

        # Global idle check
        all_idle = len(results) > 0 and all(
            s.state == SessionState.IDLE for s in results
        )

        if all_idle:
            if self._all_idle_since is None:
                self._all_idle_since = now
                self._trigger_fired = False
            idle_duration = now - self._all_idle_since

            if idle_duration >= self._config.idle_threshold and not self._trigger_fired:
                for cb in self._cb_trigger:
                    _safe_call(cb, idle_duration, results)
                self._trigger_fired = True
        else:
            self._all_idle_since = None
            self._trigger_fired = False

        return results

    # ── Daemon loop ──

    def start(
        self,
        interval: float | None = None,
        idle_threshold: float | None = None,
        blocking: bool = False,
    ) -> None:
        """Start the monitor daemon.

        Args:
            interval: Override poll_interval from config.
            idle_threshold: Override idle_threshold from config.
            blocking: If True, blocks the calling thread. If False, spawns daemon thread.
        """
        if interval is not None:
            self._config.poll_interval = interval
        if idle_threshold is not None:
            self._config.idle_threshold = idle_threshold
        self._stop.clear()
        if blocking:
            self._loop()
        else:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop the monitor daemon."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.poll_once()
            except Exception as exc:
                import sys
                print(f"[meshterm-monitor] poll error: {exc}", file=sys.stderr)
            self._stop.wait(self._config.poll_interval)


# ── Cron trigger helpers ──


def make_shell_trigger(command: str) -> Callable:
    """Create a trigger callback that runs a shell command.

    Usage:
        monitor.on_trigger(make_shell_trigger("notify-send 'All IDLE'"))
    """
    def _trigger(idle_seconds: float, sessions: list[SessionStatus]) -> None:
        subprocess.run(command, shell=True, timeout=30, capture_output=True)
    return _trigger


def make_webhook_trigger(
    url: str,
    method: str = "POST",
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> Callable:
    """Create a trigger callback that sends an HTTP webhook when fired.

    JSON payload includes idle_seconds, session count, and per-session details.

    Usage:
        monitor.on_trigger(make_webhook_trigger("https://hooks.example.com/idle"))
        monitor.on_trigger(make_webhook_trigger(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": "Bearer xoxb-..."},
        ))
    """
    def _trigger(idle_seconds: float, sessions: list[SessionStatus]) -> None:
        import json
        import datetime
        from urllib.request import Request, urlopen
        from urllib.error import URLError

        payload = {
            "event": "meshterm.all_idle",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "idle_seconds": round(idle_seconds, 1),
            "session_count": len(sessions),
            "sessions": [
                {
                    "pane_id": s.pane_id,
                    "name": s.name,
                    "command": s.command,
                    "state": s.state.value,
                    "idle_seconds": round(s.idle_seconds, 1),
                }
                for s in sessions
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        hdrs = {"Content-Type": "application/json", **(headers or {})}
        req = Request(url, data=body, headers=hdrs, method=method)
        try:
            urlopen(req, timeout=timeout)
        except (URLError, OSError):
            pass
    return _trigger


def make_log_trigger(log_path: str = "/tmp/meshterm_idle.log") -> Callable:
    """Create a trigger callback that appends to a log file."""
    def _trigger(idle_seconds: float, sessions: list[SessionStatus]) -> None:
        import datetime
        ts = datetime.datetime.now().isoformat()
        names = ", ".join(s.name for s in sessions)
        with open(log_path, "a") as f:
            f.write(f"[{ts}] ALL IDLE for {idle_seconds:.0f}s — {names}\n")
    return _trigger


# ── Internal ──


def _safe_call(func: Callable, *args) -> None:
    """Call without propagating exceptions."""
    try:
        func(*args)
    except Exception:
        pass
