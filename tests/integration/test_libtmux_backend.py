"""TDD tests for meshterm libtmux backend.

Written BEFORE implementation (test-first).
Tests define the expected API; backend implements to make these pass.

Requires: tmux running, libtmux installed.
"""

from __future__ import annotations

import asyncio
import subprocess
import time

import pytest

# Backend will be at: meshterm.backends.libtmux_backend
# Import will fail until backend is written — expected for TDD
try:
    from meshterm.backends.libtmux_backend import LibtmuxBackend
    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False

TEST_SESSION = "meshterm-libtmux-test"


@pytest.fixture(autouse=True)
def tmux_test_session():
    """Create a test tmux session, clean up after."""
    subprocess.run(["tmux", "kill-session", "-t", TEST_SESSION], capture_output=True)
    subprocess.run(["tmux", "new-session", "-d", "-s", TEST_SESSION], check=True)
    time.sleep(0.3)
    yield TEST_SESSION
    subprocess.run(["tmux", "kill-session", "-t", TEST_SESSION], capture_output=True)


@pytest.fixture
def backend():
    if not BACKEND_AVAILABLE:
        pytest.skip("libtmux_backend not yet implemented")
    return LibtmuxBackend()


# --- 7 Required Feature Tests ---


class TestTextInjection:
    """Requirement 1: send_text — inject text into session."""

    async def test_send_text_basic(self, backend):
        await backend.send_text(TEST_SESSION, "echo hello-libtmux")
        time.sleep(0.3)
        screen = await backend.read_screen(TEST_SESSION)
        assert "echo hello-libtmux" in "\n".join(screen)

    async def test_send_text_special_chars(self, backend):
        await backend.send_text(TEST_SESSION, "echo 'quotes & pipes | here'")
        time.sleep(0.3)
        screen = await backend.read_screen(TEST_SESSION)
        assert "quotes" in "\n".join(screen)

    async def test_send_text_nonexistent_session(self, backend):
        with pytest.raises(Exception):
            await backend.send_text("nonexistent-xyz-999", "hello")


class TestKeyInjection:
    """Requirement 2: send_key — inject special keys (CR, ESC, Ctrl+C)."""

    async def test_send_enter(self, backend):
        await backend.send_text(TEST_SESSION, "echo key-test")
        await backend.send_key(TEST_SESSION, "Enter")
        time.sleep(0.5)
        screen = await backend.read_screen(TEST_SESSION)
        assert "key-test" in "\n".join(screen)

    async def test_send_escape(self, backend):
        result = await backend.send_key(TEST_SESSION, "Escape")
        assert result is True

    async def test_send_ctrl_c(self, backend):
        # Start a long-running process
        await backend.send_text(TEST_SESSION, "sleep 300")
        await backend.send_key(TEST_SESSION, "Enter")
        time.sleep(0.3)
        # Interrupt it
        await backend.send_key(TEST_SESSION, "C-c")
        time.sleep(0.5)
        screen = await backend.read_screen(TEST_SESSION)
        # Should see prompt again (sleep was interrupted)
        assert "$" in "\n".join(screen) or ">" in "\n".join(screen)


class TestScreenReading:
    """Requirement 3: read_screen — read visible terminal content."""

    async def test_read_screen_basic(self, backend):
        await backend.send_text(TEST_SESSION, "echo screen-read-test")
        await backend.send_key(TEST_SESSION, "Enter")
        time.sleep(0.5)
        screen = await backend.read_screen(TEST_SESSION)
        assert isinstance(screen, list)
        assert any("screen-read-test" in line for line in screen)

    async def test_read_screen_with_scrollback(self, backend):
        # Generate enough output for scrollback
        for i in range(5):
            await backend.send_text(TEST_SESSION, f"echo line-{i}")
            await backend.send_key(TEST_SESSION, "Enter")
            time.sleep(0.2)
        screen = await backend.read_screen(TEST_SESSION, lines=50)
        text = "\n".join(screen)
        assert "line-0" in text
        assert "line-4" in text

    async def test_read_nonexistent_session(self, backend):
        with pytest.raises(Exception):
            await backend.read_screen("nonexistent-xyz-999")


class TestSessionEnumeration:
    """Requirement 4: discover — list all sessions."""

    async def test_discover_finds_test_session(self, backend):
        sessions = await backend.discover()
        names = [s["name"] for s in sessions]
        assert TEST_SESSION in names

    async def test_discover_returns_list(self, backend):
        sessions = await backend.discover()
        assert isinstance(sessions, list)
        assert len(sessions) >= 1


class TestSessionUUID:
    """Requirement 5: UUID — unique identifier per session."""

    async def test_set_and_get_uuid(self, backend):
        test_uuid = "550e8400-e29b-41d4-a716-446655440000"
        await backend.set_uuid(TEST_SESSION, test_uuid)
        retrieved = await backend.get_uuid(TEST_SESSION)
        assert retrieved == test_uuid

    async def test_uuid_persists(self, backend):
        test_uuid = "test-uuid-persist-123"
        await backend.set_uuid(TEST_SESSION, test_uuid)
        # Read it twice — should be same
        uuid1 = await backend.get_uuid(TEST_SESSION)
        uuid2 = await backend.get_uuid(TEST_SESSION)
        assert uuid1 == uuid2 == test_uuid


class TestSessionMetadata:
    """Requirement 6: metadata — name, command, pid, cwd."""

    async def test_get_metadata(self, backend):
        meta = await backend.get_metadata(TEST_SESSION)
        assert "name" in meta
        assert meta["name"] == TEST_SESSION
        assert "pid" in meta
        assert isinstance(meta["pid"], int)
        assert meta["pid"] > 0

    async def test_metadata_has_command(self, backend):
        meta = await backend.get_metadata(TEST_SESSION)
        assert "command" in meta
        # Should be bash or zsh or similar
        assert meta["command"] in ("bash", "zsh", "sh", "fish")

    async def test_metadata_has_cwd(self, backend):
        meta = await backend.get_metadata(TEST_SESSION)
        assert "cwd" in meta
        assert "/" in meta["cwd"]  # Should be an absolute path


class TestHeadlessIPC:
    """Requirement 7: headless — works without GUI."""

    async def test_no_display_needed(self, backend):
        """Backend should work even without DISPLAY env var."""
        import os
        old_display = os.environ.pop("DISPLAY", None)
        try:
            sessions = await backend.discover()
            assert isinstance(sessions, list)
        finally:
            if old_display:
                os.environ["DISPLAY"] = old_display


class TestWaitFor:
    """Bonus: wait_for pattern — meshterm's key differentiator."""

    async def test_wait_for_pattern(self, backend):
        # Send a command that takes a moment
        await backend.send_text(TEST_SESSION, "sleep 0.5 && echo DONE-MARKER")
        await backend.send_key(TEST_SESSION, "Enter")
        # Wait for the output
        found = await backend.wait_for(TEST_SESSION, "DONE-MARKER", timeout=5.0)
        assert found is True

    async def test_wait_for_timeout(self, backend):
        found = await backend.wait_for(TEST_SESSION, "NEVER-APPEARS", timeout=1.0)
        assert found is False


class TestSessionLifecycle:
    """Session create and destroy."""

    async def test_create_session(self, backend):
        new_name = "meshterm-lifecycle-test"
        try:
            await backend.create_session(new_name)
            sessions = await backend.discover()
            names = [s["name"] for s in sessions]
            assert new_name in names
        finally:
            subprocess.run(["tmux", "kill-session", "-t", new_name], capture_output=True)

    async def test_kill_session(self, backend):
        temp_name = "meshterm-kill-test"
        subprocess.run(["tmux", "new-session", "-d", "-s", temp_name], check=True)
        await backend.kill_session(temp_name)
        time.sleep(0.3)
        sessions = await backend.discover()
        names = [s["name"] for s in sessions]
        assert temp_name not in names
