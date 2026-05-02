"""Unit tests for meshterm.connection -- socket paths, frame encoding."""

import json
import os
import struct

from meshterm.connection import (
    Connection,
    default_socket_path,
    default_cookie_path,
    _encode_frame,
    _HEADER_FMT,
    _HEADER_SIZE,
    _MAX_FRAME,
)


# ── Frame encoding ──

class TestFrameEncoding:

    def test_encode_frame_structure(self):
        obj = {"method": "test", "id": 1}
        frame = _encode_frame(obj)
        # First 4 bytes = big-endian length
        (length,) = struct.unpack(_HEADER_FMT, frame[:_HEADER_SIZE])
        payload = frame[_HEADER_SIZE:]
        assert len(payload) == length
        decoded = json.loads(payload)
        assert decoded["method"] == "test"
        assert decoded["id"] == 1

    def test_encode_frame_compact_json(self):
        """Frames should use compact JSON (no extra whitespace)."""
        obj = {"a": 1, "b": "two"}
        frame = _encode_frame(obj)
        payload = frame[_HEADER_SIZE:]
        text = payload.decode("utf-8")
        assert " " not in text  # compact separators, no spaces

    def test_header_size_is_4(self):
        assert _HEADER_SIZE == 4

    def test_max_frame_is_16mb(self):
        assert _MAX_FRAME == 16 * 1024 * 1024


# ── Socket path resolution ──

class TestDefaultSocketPath:

    def test_explicit_env_override(self, monkeypatch):
        monkeypatch.setenv("MESHTERM_SOCKET", "/custom/path.sock")
        path = default_socket_path()
        assert str(path) == "/custom/path.sock"

    def test_xdg_runtime_dir(self, monkeypatch):
        monkeypatch.delenv("MESHTERM_SOCKET", raising=False)
        monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
        path = default_socket_path()
        assert str(path) == "/run/user/1000/meshterm/ipc.sock"

    def test_fallback_tmp(self, monkeypatch):
        monkeypatch.delenv("MESHTERM_SOCKET", raising=False)
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        path = default_socket_path()
        uid = os.getuid()
        assert str(path) == f"/tmp/meshterm-{uid}/ipc.sock"


class TestDefaultCookiePath:

    def test_uses_xdg_config_home(self, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", "/home/test/.config")
        path = default_cookie_path()
        assert str(path) == "/home/test/.config/meshterm/auth_cookie"


# ── Connection basics ──

class TestConnectionInit:

    def test_initial_state(self):
        conn = Connection()
        assert conn.connected is False
        assert conn._request_id == 0
        assert conn._pending == {}
