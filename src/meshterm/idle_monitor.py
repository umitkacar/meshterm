"""Idle detection and cron trigger system for meshterm sessions.

Detects IDLE/BUSY state per session and triggers callbacks when
all sessions (or specific ones) have been idle for a configurable
duration.

Idle detection uses two signals:
  1. Screen diff — no output changes between polls
  2. Prompt pattern — terminal shows a shell/app prompt (configurable)

Both must be true for a session to be considered IDLE.

Usage:
    monitor = IdleMonitor(app)
    monitor.on_idle(lambda sessions: print("All idle!"))
    monitor.start(interval=5.0, idle_threshold=900)  # 15 min
"""

from __future__ import annotations

import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class SessionState(Enum):
    """Session activity state."""
    IDLE = "IDLE"
    BUSY = "BUSY"
    UNKNOWN = "UNKNOWN"


@dataclass
class SessionStatus:
    """Snapshot of a session's idle state."""
    pane_id: str
    name: str
    command: str
    state: SessionState
    idle_seconds: float = 0.0
    last_change: float = 0.0  # monotonic timestamp of last screen change
    screen_preview: str = ""  # last line of screen (for debugging)


@dataclass
class IdleConfig:
    """Configuration for idle detection."""
    # Prompt patterns that indicate IDLE (shell waiting for input)
    prompt_patterns: list[str] = field(default_factory=lambda: [
        r"[$#>❯»]\s*$",           # common shell prompts
        r">>>\s*$",                # Python REPL
        r"In \[\d+\]:\s*$",       # IPython/Jupyter
        r"^\s*$",                  # empty line (cursor at prompt)
    ])
    # How long all sessions must be idle before trigger (seconds)
    idle_threshold: float = 900.0  # 15 minutes default
    # Poll interval (seconds)
    poll_interval: float = 5.0
    # Minimum consecutive idle polls before confirming IDLE
    min_idle_polls: int = 3


class IdleMonitor:
    """Monitors tmux sessions for idle/busy state.

    Core loop: poll → diff → classify → check threshold → trigger

    Usage:
        from meshterm.libtmux_session import LibtmuxApp
        from meshterm.idle_monitor import IdleMonitor

        app = LibtmuxApp()
        monitor = IdleMonitor(app)
        monitor.on_idle(my_callback)
        monitor.on_session_idle(my_per_session_callback)
        monitor.start()
    """

    def __init__(self, app, config: IdleConfig | None = None):
        self._app = app
        self._config = config or IdleConfig()
        self._prompt_re = re.compile(
            "|".join(self._config.prompt_patterns)
        )

        # Per-pane tracking
        self._last_screens: dict[str, list[str]] = {}
        self._idle_since: dict[str, float] = {}  # pane_id → monotonic time
        self._idle_polls: dict[str, int] = {}     # consecutive idle polls
        self._states: dict[str, SessionStatus] = {}

        # Callbacks
        self._on_all_idle: list[Callable] = []
        self._on_session_idle: list[Callable] = []
        self._on_session_busy: list[Callable] = []
        self._on_trigger: list[Callable] = []  # cron trigger callbacks

        # Thread control
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._all_idle_since: float | None = None

    # ── Callback registration ──

    def on_idle(self, callback: Callable) -> None:
        """Register callback for when ALL sessions are idle past threshold.

        callback(sessions: list[SessionStatus])
        """
        self._on_all_idle.append(callback)

    def on_session_idle(self, callback: Callable) -> None:
        """Register callback for individual session becoming idle.

        callback(status: SessionStatus)
        """
        self._on_session_idle.append(callback)

    def on_session_busy(self, callback: Callable) -> None:
        """Register callback for individual session becoming busy.

        callback(status: SessionStatus)
        """
        self._on_session_busy.append(callback)

    def on_trigger(self, callback: Callable) -> None:
        """Register cron trigger callback — runs when idle threshold hit.

        callback(idle_seconds: float, sessions: list[SessionStatus])
        """
        self._on_trigger.append(callback)

    # ── State query ──

    def get_status(self, pane_id: str) -> SessionStatus | None:
        """Get current status of a specific session."""
        return self._states.get(pane_id)

    def get_all_statuses(self) -> list[SessionStatus]:
        """Get status of all tracked sessions."""
        return list(self._states.values())

    def is_all_idle(self) -> bool:
        """Check if all sessions are currently idle."""
        if not self._states:
            return False
        return all(s.state == SessionState.IDLE for s in self._states.values())

    def all_idle_duration(self) -> float:
        """How long all sessions have been idle (0 if any is busy)."""
        if self._all_idle_since is None:
            return 0.0
        return time.monotonic() - self._all_idle_since

    # ── Core detection ──

    def poll_once(self) -> list[SessionStatus]:
        """Run one poll cycle — detect idle/busy for all sessions."""
        now = time.monotonic()
        sessions = self._app.list_sessions()
        results = []

        for sess in sessions:
            pid = sess.pane_id
            current_lines = sess._pane.capture_pane()
            prev_lines = self._last_screens.get(pid, [])

            # Signal 1: screen changed?
            screen_changed = current_lines != prev_lines
            self._last_screens[pid] = current_lines

            # Signal 2: prompt visible on last non-empty line?
            last_line = ""
            for line in reversed(current_lines):
                if line.strip():
                    last_line = line
                    break
            prompt_visible = bool(self._prompt_re.search(last_line))

            # Classify
            if screen_changed:
                # Screen changed → BUSY, reset idle tracking
                state = SessionState.BUSY
                self._idle_since.pop(pid, None)
                self._idle_polls[pid] = 0
                was_idle = (
                    pid in self._states
                    and self._states[pid].state == SessionState.IDLE
                )
            else:
                # Screen stable
                self._idle_polls[pid] = self._idle_polls.get(pid, 0) + 1

                if (prompt_visible
                        and self._idle_polls[pid] >= self._config.min_idle_polls):
                    state = SessionState.IDLE
                    if pid not in self._idle_since:
                        self._idle_since[pid] = now
                else:
                    state = SessionState.BUSY
                was_idle = False

            idle_secs = now - self._idle_since[pid] if pid in self._idle_since else 0.0

            status = SessionStatus(
                pane_id=pid,
                name=sess.name or sess.current_command,
                command=sess.current_command,
                state=state,
                idle_seconds=idle_secs,
                last_change=now if screen_changed else self._states.get(pid, SessionStatus(pid, "", "", SessionState.UNKNOWN)).last_change or now,
                screen_preview=last_line[:80],
            )
            self._states[pid] = status
            results.append(status)

            # Per-session callbacks
            if state == SessionState.IDLE and not was_idle:
                if self._idle_polls.get(pid, 0) == self._config.min_idle_polls:
                    for cb in self._on_session_idle:
                        _safe_call(cb, status)

            if screen_changed and was_idle:
                for cb in self._on_session_busy:
                    _safe_call(cb, status)

        # Check all-idle state
        all_idle = all(s.state == SessionState.IDLE for s in results) and len(results) > 0

        if all_idle:
            if self._all_idle_since is None:
                self._all_idle_since = now
            idle_duration = now - self._all_idle_since

            # Threshold check for trigger
            if idle_duration >= self._config.idle_threshold:
                for cb in self._on_all_idle:
                    _safe_call(cb, results)
                for cb in self._on_trigger:
                    _safe_call(cb, idle_duration, results)
                # Reset to avoid repeated triggers
                self._all_idle_since = now
        else:
            self._all_idle_since = None

        return results

    # ── Monitor loop ──

    def start(
        self,
        interval: float | None = None,
        idle_threshold: float | None = None,
        blocking: bool = False,
    ) -> None:
        """Start monitoring loop.

        Args:
            interval: Poll interval in seconds (default from config)
            idle_threshold: Override idle threshold in seconds
            blocking: If True, run in foreground (blocks). If False, spawn thread.
        """
        if interval is not None:
            self._config.poll_interval = interval
        if idle_threshold is not None:
            self._config.idle_threshold = idle_threshold

        self._stop_event.clear()

        if blocking:
            self._loop()
        else:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop monitoring loop."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _loop(self) -> None:
        """Internal poll loop."""
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception as e:
                # Log but don't crash the monitor
                import sys
                print(f"[meshterm-monitor] poll error: {e}", file=sys.stderr)
            self._stop_event.wait(self._config.poll_interval)


# ── Cron trigger helpers ──

def make_shell_trigger(command: str) -> Callable:
    """Create a callback that runs a shell command when triggered.

    Usage:
        monitor.on_trigger(make_shell_trigger("ssh Mac 'notify Poseidon idle'"))
    """
    def trigger(idle_seconds: float, sessions: list[SessionStatus]) -> None:
        try:
            subprocess.run(
                command,
                shell=True,
                timeout=30,
                capture_output=True,
            )
        except Exception:
            pass
    return trigger


def make_webhook_trigger(
    url: str,
    method: str = "POST",
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> Callable:
    """Create a callback that sends an HTTP webhook when triggered.

    The JSON payload contains idle_seconds, session count, and per-session
    details (pane_id, name, command, state).

    Usage:
        monitor.on_trigger(make_webhook_trigger("https://hooks.example.com/idle"))
        monitor.on_trigger(make_webhook_trigger(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": "Bearer xoxb-..."},
        ))
    """
    def trigger(idle_seconds: float, sessions: list[SessionStatus]) -> None:
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
    return trigger


def make_log_trigger(log_path: str = "/tmp/meshterm_idle.log") -> Callable:
    """Create a callback that logs idle events to a file."""
    def trigger(idle_seconds: float, sessions: list[SessionStatus]) -> None:
        import datetime
        ts = datetime.datetime.now().isoformat()
        names = ", ".join(s.name for s in sessions)
        with open(log_path, "a") as f:
            f.write(f"[{ts}] ALL IDLE for {idle_seconds:.0f}s — sessions: {names}\n")
    return trigger


# ── Internal ──

def _safe_call(func: Callable, *args) -> None:
    """Call function without propagating exceptions."""
    try:
        func(*args)
    except Exception:
        pass
