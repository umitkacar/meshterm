"""Unit tests for meshterm.server -- key map, handler registry, SessionState."""

import asyncio

import pytest

from meshterm.server import MeshTermServer, SessionState


# ── SessionState dataclass ──

class TestSessionState:

    def test_create_with_required_fields(self):
        state = SessionState(
            session_id="abc-123",
            name="main",
            profile="default",
            pid=12345,
            master_fd=5,
            tty="/dev/pts/3",
        )
        assert state.session_id == "abc-123"
        assert state.name == "main"
        assert state.profile == "default"
        assert state.pid == 12345
        assert state.master_fd == 5
        assert state.tty == "/dev/pts/3"

    def test_default_dimensions(self):
        state = SessionState(
            session_id="x", name="", profile="", pid=1, master_fd=0, tty=""
        )
        assert state.rows == 24
        assert state.cols == 80

    def test_user_vars_default_empty(self):
        state = SessionState(
            session_id="x", name="", profile="", pid=1, master_fd=0, tty=""
        )
        assert state.user_vars == {}

    def test_user_vars_independent_per_instance(self):
        """Verify default_factory gives each instance its own dict."""
        s1 = SessionState(session_id="a", name="", profile="", pid=1, master_fd=0, tty="")
        s2 = SessionState(session_id="b", name="", profile="", pid=2, master_fd=0, tty="")
        s1.user_vars["foo"] = "bar"
        assert "foo" not in s2.user_vars


# ── MeshTermServer handler registry ──

class TestServerHandlerRegistry:

    def test_builtin_handlers_registered(self):
        server = MeshTermServer(socket_path="/tmp/test-meshterm.sock", require_auth=False)
        expected_methods = [
            "app.get_state",
            "app.get_variable",
            "session.send_text",
            "session.send_key",
            "session.get_screen_contents",
            "session.get_scrollback",
            "session.set_name",
            "session.activate",
            "session.close",
            "session.split_pane",
            "session.get_variable",
            "session.set_variable",
            "session.set_grid_size",
            "window.create",
            "window.activate",
            "window.close",
            "window.create_tab",
            "window.set_title",
            "window.set_position",
            "window.set_size",
            "window.set_fullscreen",
            "window.set_tabs",
            "tab.activate",
            "tab.close",
            "tab.set_title",
            "tab.split_pane",
            "tab.select_pane_in_direction",
            "subscribe",
        ]
        for method in expected_methods:
            assert method in server._handlers, f"Missing handler: {method}"

    def test_handler_count(self):
        server = MeshTermServer(socket_path="/tmp/test-meshterm.sock", require_auth=False)
        assert len(server._handlers) == 28


# ── Session registration ──

class TestServerSessionRegistration:

    def test_register_and_lookup(self):
        server = MeshTermServer(socket_path="/tmp/test-meshterm.sock", require_auth=False)
        state = SessionState(
            session_id="sess-1", name="test", profile="default",
            pid=999, master_fd=10, tty="/dev/pts/0",
        )
        server.register_session(state)
        assert "sess-1" in server._sessions
        assert server._sessions["sess-1"].pid == 999

    def test_unregister_session(self):
        server = MeshTermServer(socket_path="/tmp/test-meshterm.sock", require_auth=False)
        state = SessionState(
            session_id="sess-2", name="t", profile="default",
            pid=1, master_fd=0, tty="",
        )
        server.register_session(state)
        server.unregister_session("sess-2")
        assert "sess-2" not in server._sessions

    def test_unregister_nonexistent_is_safe(self):
        server = MeshTermServer(socket_path="/tmp/test-meshterm.sock", require_auth=False)
        server.unregister_session("does-not-exist")  # should not raise


# ── Key translation table (send_key handler) ──

class TestKeyTranslationMap:
    """Test the key_map dict inside _h_session_send_key.

    We extract the key map logic by calling the handler with a mock session
    and intercepting the os.write call.
    """

    @pytest.fixture
    def server_with_session(self):
        server = MeshTermServer(socket_path="/tmp/test-meshterm.sock", require_auth=False)
        state = SessionState(
            session_id="key-test", name="keys", profile="default",
            pid=1, master_fd=-1, tty="",  # fd=-1, we'll mock os.write
        )
        server.register_session(state)
        return server

    @pytest.fixture
    def capture_write(self, monkeypatch):
        """Mock os.write to capture what bytes would be sent to the PTY."""
        written = []
        monkeypatch.setattr("os.write", lambda fd, data: written.append(data))
        return written

    @pytest.mark.parametrize("key,expected_bytes", [
        ("Return", b"\r"),
        ("Escape", b"\x1b"),
        ("Tab", b"\t"),
        ("Backspace", b"\x7f"),
        ("Delete", b"\x1b[3~"),
        ("Up", b"\x1b[A"),
        ("Down", b"\x1b[B"),
        ("Right", b"\x1b[C"),
        ("Left", b"\x1b[D"),
        ("Home", b"\x1b[H"),
        ("End", b"\x1b[F"),
        ("PageUp", b"\x1b[5~"),
        ("PageDown", b"\x1b[6~"),
    ])
    async def test_named_keys(self, server_with_session, capture_write, key, expected_bytes):
        await server_with_session._h_session_send_key(
            session_id="key-test", key=key, modifiers=[],
        )
        assert capture_write == [expected_bytes], f"Key {key!r}: expected {expected_bytes!r}, got {capture_write}"

    async def test_ctrl_c(self, server_with_session, capture_write):
        await server_with_session._h_session_send_key(
            session_id="key-test", key="c", modifiers=["ctrl"],
        )
        assert capture_write == [b"\x03"]

    async def test_ctrl_d(self, server_with_session, capture_write):
        await server_with_session._h_session_send_key(
            session_id="key-test", key="d", modifiers=["ctrl"],
        )
        assert capture_write == [b"\x04"]

    async def test_ctrl_z(self, server_with_session, capture_write):
        await server_with_session._h_session_send_key(
            session_id="key-test", key="z", modifiers=["ctrl"],
        )
        assert capture_write == [b"\x1a"]

    async def test_single_char_key(self, server_with_session, capture_write):
        await server_with_session._h_session_send_key(
            session_id="key-test", key="a", modifiers=[],
        )
        assert capture_write == [b"a"]

    async def test_f1_key(self, server_with_session, capture_write):
        await server_with_session._h_session_send_key(
            session_id="key-test", key="F1", modifiers=[],
        )
        assert capture_write == [b"\x1bOP"]

    async def test_f5_key(self, server_with_session, capture_write):
        await server_with_session._h_session_send_key(
            session_id="key-test", key="F5", modifiers=[],
        )
        assert capture_write == [b"\x1b[15~"]
