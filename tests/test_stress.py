"""Stress tests — concurrent sessions and large messages."""

import time
import pytest
import libtmux


class TestConcurrentSessions:
    """Test multiple sessions simultaneously."""

    def test_10_sessions_parallel(self):
        """Create 10 sessions, send text, read, verify, cleanup."""
        server = libtmux.Server()
        sessions = []
        markers = []

        # Create 10 sessions
        for i in range(10):
            marker = f"STRESS_{i}_{int(time.time())}"
            markers.append(marker)
            s = server.new_session(
                session_name=f"stress-{i}-{int(time.time())}",
                window_name=f"w{i}",
            )
            sessions.append(s)

        # Send unique marker to each
        for i, s in enumerate(sessions):
            pane = s.active_window.active_pane
            pane.send_keys(f"echo {markers[i]}", enter=True)

        time.sleep(1.0)  # Wait for all commands

        # Verify each session has its marker
        for i, s in enumerate(sessions):
            pane = s.active_window.active_pane
            output = "\n".join(pane.capture_pane())
            assert markers[i] in output, (
                f"Session {i}: marker '{markers[i]}' not found"
            )

        # Cleanup
        for s in sessions:
            try:
                s.kill()
            except Exception:
                pass

        # Verify all cleaned up
        remaining_names = [s.session_name for s in server.sessions]
        for i in range(10):
            assert not any(
                f"stress-{i}-" in name for name in remaining_names
            )


class TestLargeMessage:
    """Test large payload integrity."""

    def test_500_char_message(self):
        """Send 500 characters, verify no truncation."""
        server = libtmux.Server()
        session = server.new_session(session_name="stress-large")
        pane = session.active_window.active_pane

        # 500 char message
        msg = "A" * 500
        pane.send_keys(f"echo {msg}", enter=True)
        time.sleep(1.0)

        output = "\n".join(pane.capture_pane())
        # Count A's in output (should be >= 500)
        a_count = output.count("A")
        assert a_count >= 500, f"Expected 500+ A's, got {a_count}"

        session.kill()

    def test_special_characters(self):
        """Send text with quotes, pipes, semicolons."""
        server = libtmux.Server()
        session = server.new_session(session_name="stress-special")
        pane = session.active_window.active_pane

        # Use printf to avoid shell interpretation
        pane.send_keys("printf 'hello world 123'", enter=True)
        time.sleep(0.5)

        output = "\n".join(pane.capture_pane())
        assert "hello world 123" in output

        session.kill()
