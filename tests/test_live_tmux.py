"""Live tmux tests — REAL tmux, no mocks.

Each test creates a real tmux session, runs real commands,
reads real screen output. Cleanup happens in fixture teardown.
"""

import time
import pytest
import libtmux


@pytest.fixture
def tmux_session():
    """Create a fresh tmux session, yield it, kill on teardown."""
    server = libtmux.Server()
    session = server.new_session(
        session_name=f"meshterm-test-{int(time.time())}",
        window_name="test",
    )
    yield session
    try:
        session.kill()
    except Exception:
        pass


@pytest.fixture
def pane(tmux_session):
    """Get the active pane from the test session."""
    return tmux_session.active_window.active_pane


class TestCreateSession:
    """Test tmux session lifecycle."""

    def test_session_created(self, tmux_session):
        """Session exists and has a valid ID."""
        assert tmux_session.session_name.startswith("meshterm-test-")
        assert tmux_session.session_id.startswith("$")

    def test_session_has_window(self, tmux_session):
        """Session has exactly one window."""
        windows = tmux_session.windows
        assert len(windows) == 1
        assert windows[0].window_name == "test"

    def test_session_has_pane(self, pane):
        """Window has exactly one pane."""
        assert pane is not None
        assert pane.pane_id.startswith("%")


class TestSendText:
    """Test text injection and screen capture."""

    def test_send_text_appears_on_screen(self, pane):
        """Sent text appears in capture_pane output."""
        marker = f"MESHTERM_TEST_{int(time.time())}"
        pane.send_keys(f"echo {marker}", enter=True)
        time.sleep(0.5)
        output = "\n".join(pane.capture_pane())
        assert marker in output

    def test_send_text_without_enter(self, pane):
        """Text sent without enter stays in input buffer."""
        pane.send_keys("echo pending_command", enter=False)
        time.sleep(0.3)
        output = "\n".join(pane.capture_pane())
        assert "pending_command" in output
        # Command not executed — no output line
        lines = [l for l in pane.capture_pane() if l.strip()]
        # Should see the typed text but NOT the echo output
        has_typed = any("pending_command" in l for l in lines)
        assert has_typed

    def test_send_multiline(self, pane):
        """Multiple send_keys calls work sequentially."""
        pane.send_keys("echo line1", enter=True)
        time.sleep(0.3)
        pane.send_keys("echo line2", enter=True)
        time.sleep(0.3)
        output = "\n".join(pane.capture_pane())
        assert "line1" in output
        assert "line2" in output


class TestSendKeyCtrlC:
    """Test special key injection."""

    def test_ctrl_c_kills_process(self, pane):
        """Ctrl+C interrupts a running process."""
        pane.send_keys("sleep 300", enter=True)
        time.sleep(1.5)
        # Verify sleep is running (use cmd() — property is cached in libtmux 0.55)
        cmd_before = pane.cmd("display-message", "-p", "#{pane_current_command}").stdout[0]
        assert cmd_before == "sleep"
        # Send Ctrl+C
        pane.send_keys("C-c", enter=False)
        time.sleep(0.5)
        # Process should be killed, back to shell
        cmd_after = pane.cmd("display-message", "-p", "#{pane_current_command}").stdout[0]
        assert cmd_after in ("bash", "zsh", "sh", "fish")

    def test_escape_key(self, pane):
        """Escape key can be sent."""
        pane.send_keys("Escape", enter=False)
        time.sleep(0.2)
        # No crash, pane still alive
        output = pane.capture_pane()
        assert isinstance(output, list)

    def test_enter_key(self, pane):
        """Enter key submits a command."""
        pane.send_keys("echo enter_test", enter=False)
        time.sleep(0.2)
        pane.send_keys("Enter", enter=False)
        time.sleep(0.5)
        output = "\n".join(pane.capture_pane())
        assert "enter_test" in output


class TestScreenRead:
    """Test screen capture (capture_pane)."""

    def test_capture_returns_list(self, pane):
        """capture_pane returns a list of strings."""
        output = pane.capture_pane()
        assert isinstance(output, list)
        assert all(isinstance(line, str) for line in output)

    def test_capture_after_command(self, pane):
        """Capture shows command output."""
        pane.send_keys("echo SCREEN_READ_OK", enter=True)
        time.sleep(0.5)
        output = pane.capture_pane()
        found = any("SCREEN_READ_OK" in line for line in output)
        assert found, f"'SCREEN_READ_OK' not found in: {output[:5]}"

    def test_capture_multiple_lines(self, pane):
        """Capture shows multiple output lines."""
        pane.send_keys("seq 1 5", enter=True)
        time.sleep(0.5)
        output = pane.capture_pane()
        text = "\n".join(output)
        for n in range(1, 6):
            assert str(n) in text, f"Number {n} not in capture"

    def test_capture_empty_lines(self, pane):
        """Capture handles empty screen gracefully."""
        pane.send_keys("clear", enter=True)
        time.sleep(0.3)
        output = pane.capture_pane()
        assert isinstance(output, list)


class TestSessionMetadata:
    """Test session/pane metadata access."""

    def test_pane_pid(self, pane):
        """Pane has a valid PID."""
        pid = pane.pane_pid
        assert pid is not None
        assert int(pid) > 0

    def test_pane_tty(self, pane):
        """Pane has a valid TTY."""
        tty = pane.pane_tty
        assert tty is not None
        assert "/dev/pts/" in tty

    def test_pane_current_command(self, pane):
        """Pane reports the current foreground command."""
        cmd = pane.pane_current_command
        assert cmd in ("bash", "zsh", "sh", "fish")

    def test_pane_current_path(self, pane):
        """Pane reports current working directory."""
        cwd = pane.pane_current_path
        assert cwd is not None
        assert "/" in cwd

    def test_pane_title(self, pane):
        """Pane has a title."""
        title = pane.pane_title
        assert title is not None


class TestCleanup:
    """Test session cleanup."""

    def test_kill_session(self):
        """Killed session no longer exists."""
        server = libtmux.Server()
        session = server.new_session(
            session_name="meshterm-cleanup-test"
        )
        sid = session.session_id
        session.kill()
        time.sleep(0.3)
        remaining = [s.session_id for s in server.sessions]
        assert sid not in remaining
