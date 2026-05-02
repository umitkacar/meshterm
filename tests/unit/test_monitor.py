"""Tests for meshterm.monitor — idle detection daemon.

Uses mock backend (no real tmux needed).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from meshterm.monitor import (
    Monitor,
    MonitorConfig,
    SessionState,
    SessionStatus,
    make_log_trigger,
    make_shell_trigger,
    make_webhook_trigger,
)


# ── Fake backend ──


@dataclass
class FakePane:
    """Minimal pane mock for capture_pane()."""
    pane_id: str = "%0"
    _lines: list[str] | None = None

    def capture_pane(self) -> list[str]:
        return list(self._lines or ["~ $"])


class FakeSession:
    """Minimal session mock matching LibtmuxSession interface."""

    def __init__(self, pane_id: str = "%0", lines: list[str] | None = None,
                 name: str = "bash", command: str = "bash"):
        self._pane = FakePane(pane_id=pane_id, _lines=lines or ["~ $"])
        self._name = name
        self._command = command

    @property
    def pane_id(self) -> str:
        return self._pane.pane_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def current_command(self) -> str:
        return self._command


class FakeBackend:
    """Minimal backend mock matching LibtmuxApp interface."""

    def __init__(self, sessions: list[FakeSession] | None = None):
        self._sessions = sessions or []

    def list_sessions(self) -> list[FakeSession]:
        return self._sessions


# ── Fixtures ──


@pytest.fixture
def idle_session():
    """Session showing a shell prompt (idle)."""
    return FakeSession(pane_id="%0", lines=["last login", "~ $"])


@pytest.fixture
def busy_session():
    """Session showing running output (busy)."""
    return FakeSession(
        pane_id="%1",
        lines=["Compiling...", "Building module 3/10"],
        command="make",
    )


@pytest.fixture
def fast_config():
    """Config with minimal delays for testing."""
    return MonitorConfig(
        poll_interval=0.01,
        idle_threshold=0.05,
        min_idle_polls=2,
    )


# ── Tests: screen hash ──


class TestScreenHash:
    def test_same_content_same_hash(self):
        lines = ["hello", "world"]
        h1 = Monitor._screen_hash(lines)
        h2 = Monitor._screen_hash(lines)
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = Monitor._screen_hash(["hello"])
        h2 = Monitor._screen_hash(["world"])
        assert h1 != h2

    def test_hash_is_hex_string(self):
        h = Monitor._screen_hash(["test"])
        assert len(h) == 64  # SHA-256 hex
        assert all(c in "0123456789abcdef" for c in h)

    def test_empty_lines(self):
        h = Monitor._screen_hash([])
        assert isinstance(h, str)
        assert len(h) == 64


# ── Tests: idle detection ──


class TestIdleDetection:
    def test_first_poll_is_busy(self, idle_session, fast_config):
        """First poll always BUSY (no baseline to compare)."""
        backend = FakeBackend([idle_session])
        mon = Monitor(backend, config=fast_config)
        results = mon.poll_once()
        assert len(results) == 1
        # First poll: hash differs from empty -> BUSY
        assert results[0].state == SessionState.BUSY

    def test_stable_prompt_becomes_idle(self, idle_session, fast_config):
        """After min_idle_polls stable polls with prompt, session is IDLE."""
        backend = FakeBackend([idle_session])
        mon = Monitor(backend, config=fast_config)

        # Poll enough times to pass min_idle_polls
        for _ in range(fast_config.min_idle_polls + 1):
            results = mon.poll_once()

        assert results[0].state == SessionState.IDLE
        assert results[0].idle_seconds >= 0

    def test_changing_screen_stays_busy(self, fast_config):
        """Screen that changes every poll stays BUSY."""
        session = FakeSession(pane_id="%0", lines=["line 1"])
        backend = FakeBackend([session])
        mon = Monitor(backend, config=fast_config)

        mon.poll_once()
        session._pane._lines = ["line 2"]
        results = mon.poll_once()
        assert results[0].state == SessionState.BUSY

        session._pane._lines = ["line 3"]
        results = mon.poll_once()
        assert results[0].state == SessionState.BUSY

    def test_no_prompt_stays_busy(self, fast_config):
        """Stable screen without prompt pattern stays BUSY."""
        session = FakeSession(
            pane_id="%0",
            lines=["Processing data..."],
        )
        backend = FakeBackend([session])
        mon = Monitor(backend, config=fast_config)

        for _ in range(fast_config.min_idle_polls + 2):
            results = mon.poll_once()

        # No prompt -> stays BUSY even if stable
        assert results[0].state == SessionState.BUSY

    def test_multiple_sessions_mixed(self, idle_session, busy_session, fast_config):
        """Two sessions: one idle, one busy."""
        backend = FakeBackend([idle_session, busy_session])
        mon = Monitor(backend, config=fast_config)

        for _ in range(fast_config.min_idle_polls + 1):
            results = mon.poll_once()

        states = {r.pane_id: r.state for r in results}
        assert states["%0"] == SessionState.IDLE
        # %1 has no prompt pattern -> BUSY
        assert states["%1"] == SessionState.BUSY
        assert not mon.is_all_idle()


# ── Tests: prompt patterns ──


class TestPromptPatterns:
    @pytest.mark.parametrize("line,expected", [
        ("~ $ ", True),        # bash
        ("user@host:~# ", True),  # root
        (">>> ", True),         # Python REPL
        ("In [5]: ", True),     # IPython
        ("(Pdb) ", True),       # debugger
        ("❯ ", True),           # starship/custom
        ("Compiling...", False),
        ("make[1]: Entering", False),
        ("100%|████████|", False),
    ])
    def test_prompt_detection(self, line, expected):
        config = MonitorConfig()
        prompt_re = __import__("re").compile("|".join(config.prompt_patterns))
        assert bool(prompt_re.search(line)) == expected


# ── Tests: global idle + cron trigger ──


class TestCronTrigger:
    def test_all_idle_triggers_callback(self, fast_config):
        """When all sessions idle past threshold, trigger fires."""
        session = FakeSession(pane_id="%0", lines=["~ $"])
        backend = FakeBackend([session])
        mon = Monitor(backend, config=fast_config)

        triggered = []
        mon.on_trigger(lambda dur, ss: triggered.append((dur, len(ss))))

        # Poll until idle + threshold
        for _ in range(fast_config.min_idle_polls + 1):
            mon.poll_once()

        # Wait for threshold
        time.sleep(fast_config.idle_threshold + 0.02)
        mon.poll_once()

        assert len(triggered) == 1
        assert triggered[0][1] == 1  # 1 session

    def test_trigger_fires_once(self, fast_config):
        """Trigger fires only once per idle period (not every poll)."""
        session = FakeSession(pane_id="%0", lines=["~ $"])
        backend = FakeBackend([session])
        mon = Monitor(backend, config=fast_config)

        triggered = []
        mon.on_trigger(lambda dur, ss: triggered.append(1))

        # Become idle
        for _ in range(fast_config.min_idle_polls + 1):
            mon.poll_once()
        time.sleep(fast_config.idle_threshold + 0.02)

        # Poll many times after threshold
        for _ in range(5):
            mon.poll_once()

        assert len(triggered) == 1

    def test_trigger_resets_on_busy(self, fast_config):
        """After trigger fires, going busy + idle again fires trigger again."""
        session = FakeSession(pane_id="%0", lines=["~ $"])
        backend = FakeBackend([session])
        mon = Monitor(backend, config=fast_config)

        triggered = []
        mon.on_trigger(lambda dur, ss: triggered.append(1))

        # First idle cycle
        for _ in range(fast_config.min_idle_polls + 1):
            mon.poll_once()
        time.sleep(fast_config.idle_threshold + 0.02)
        mon.poll_once()
        assert len(triggered) == 1

        # Go busy
        session._pane._lines = ["working..."]
        mon.poll_once()

        # Go idle again
        session._pane._lines = ["~ $"]
        for _ in range(fast_config.min_idle_polls + 1):
            mon.poll_once()
        time.sleep(fast_config.idle_threshold + 0.02)
        mon.poll_once()
        assert len(triggered) == 2

    def test_no_trigger_when_mixed(self, fast_config):
        """Trigger does NOT fire if one session is busy."""
        idle_sess = FakeSession(pane_id="%0", lines=["~ $"])
        busy_sess = FakeSession(pane_id="%1", lines=["Building..."])
        backend = FakeBackend([idle_sess, busy_sess])
        mon = Monitor(backend, config=fast_config)

        triggered = []
        mon.on_trigger(lambda dur, ss: triggered.append(1))

        for _ in range(fast_config.min_idle_polls + 2):
            mon.poll_once()
        time.sleep(fast_config.idle_threshold + 0.02)
        mon.poll_once()

        assert len(triggered) == 0

    def test_no_sessions_no_trigger(self, fast_config):
        """Empty backend should not trigger."""
        backend = FakeBackend([])
        mon = Monitor(backend, config=fast_config)

        triggered = []
        mon.on_trigger(lambda dur, ss: triggered.append(1))

        for _ in range(10):
            mon.poll_once()
        assert len(triggered) == 0


# ── Tests: session transition callbacks ──


class TestSessionCallbacks:
    def test_session_idle_callback(self, fast_config):
        session = FakeSession(pane_id="%0", lines=["~ $"])
        backend = FakeBackend([session])
        mon = Monitor(backend, config=fast_config)

        idle_events = []
        mon.on_session_idle(lambda s: idle_events.append(s.pane_id))

        for _ in range(fast_config.min_idle_polls + 1):
            mon.poll_once()

        assert "%0" in idle_events

    def test_session_busy_callback(self, fast_config):
        session = FakeSession(pane_id="%0", lines=["~ $"])
        backend = FakeBackend([session])
        mon = Monitor(backend, config=fast_config)

        busy_events = []
        mon.on_session_busy(lambda s: busy_events.append(s.pane_id))

        # Become idle
        for _ in range(fast_config.min_idle_polls + 1):
            mon.poll_once()

        # Go busy
        session._pane._lines = ["compiling..."]
        mon.poll_once()

        assert "%0" in busy_events


# ── Tests: daemon thread ──


class TestDaemonThread:
    def test_start_stop(self, fast_config):
        session = FakeSession(pane_id="%0", lines=["~ $"])
        backend = FakeBackend([session])
        mon = Monitor(backend, config=fast_config)

        mon.start(blocking=False)
        assert mon.is_running
        time.sleep(0.05)
        mon.stop()
        assert not mon.is_running

    def test_poll_runs_in_background(self, fast_config):
        session = FakeSession(pane_id="%0", lines=["~ $"])
        backend = FakeBackend([session])
        mon = Monitor(backend, config=fast_config)

        mon.start(blocking=False)
        time.sleep(0.1)  # let a few polls run
        mon.stop()

        # Should have tracked the session
        statuses = mon.get_all_statuses()
        assert len(statuses) == 1


# ── Tests: trigger helpers ──


class TestTriggerHelpers:
    def test_make_shell_trigger_returns_callable(self):
        trigger = make_shell_trigger("echo test")
        assert callable(trigger)

    def test_make_log_trigger_writes_file(self, tmp_path):
        log_file = str(tmp_path / "idle.log")
        trigger = make_log_trigger(log_file)
        trigger(60.0, [SessionStatus("%0", "bash", "bash", SessionState.IDLE)])

        content = open(log_file).read()
        assert "ALL IDLE" in content
        assert "60s" in content

    def test_make_shell_trigger_runs_command(self, tmp_path):
        marker = tmp_path / "triggered.txt"
        trigger = make_shell_trigger(f"touch {marker}")
        trigger(60.0, [])
        assert marker.exists()

    def test_make_webhook_trigger_returns_callable(self):
        trigger = make_webhook_trigger("http://localhost:9999/hook")
        assert callable(trigger)

    def test_webhook_trigger_sends_post(self):
        """Webhook trigger sends JSON POST to local HTTP server."""
        import json
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading

        received = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                received.append(body)
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):
                pass  # suppress stderr

        server = HTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        t = threading.Thread(target=server.handle_request, daemon=True)
        t.start()

        trigger = make_webhook_trigger(f"http://127.0.0.1:{port}/hook")
        sessions = [SessionStatus("%0", "bash", "bash", SessionState.IDLE, idle_seconds=120.0)]
        trigger(120.0, sessions)
        t.join(timeout=5)
        server.server_close()

        assert len(received) == 1
        payload = received[0]
        assert payload["event"] == "meshterm.all_idle"
        assert payload["idle_seconds"] == 120.0
        assert payload["session_count"] == 1
        assert payload["sessions"][0]["pane_id"] == "%0"
        assert payload["sessions"][0]["state"] == "IDLE"
        assert "timestamp" in payload

    def test_webhook_trigger_silent_on_failure(self):
        """Webhook trigger does not raise on connection failure."""
        trigger = make_webhook_trigger("http://127.0.0.1:1/nonexistent")
        # Should not raise
        trigger(60.0, [])


# ── Tests: status query ──


class TestStatusQuery:
    def test_get_status_unknown_pane(self, fast_config):
        backend = FakeBackend([])
        mon = Monitor(backend, config=fast_config)
        assert mon.get_status("%99") is None

    def test_all_idle_duration_zero_when_busy(self, fast_config):
        session = FakeSession(pane_id="%0", lines=["working..."])
        backend = FakeBackend([session])
        mon = Monitor(backend, config=fast_config)
        mon.poll_once()
        assert mon.all_idle_duration() == 0.0

    def test_screen_hash_in_status(self, fast_config):
        session = FakeSession(pane_id="%0", lines=["~ $"])
        backend = FakeBackend([session])
        mon = Monitor(backend, config=fast_config)
        results = mon.poll_once()
        assert len(results[0].screen_hash) == 16  # truncated hex
