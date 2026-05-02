"""Unit tests for meshterm.remote — RemoteMeshTerm + security fixes.

These tests do NOT require a real SSH connection. They mock paramiko and
verify:
  - F1: strict_host_keys default, RejectPolicy applied, WarningPolicy opt-in
  - F2: password DeprecationWarning
  - F6: _validate_session_name whitelist + wiring into all public methods

A real SSH integration test would live under tests/integration/ and require
a running SSH server.
"""

from __future__ import annotations

import warnings
from unittest.mock import MagicMock, patch

import pytest

from meshterm.remote import RemoteMeshTerm, _validate_session_name


# ── F6: _validate_session_name unit tests ────────────────────────────────────


class TestValidateSessionName:
    """Whitelist regex + length + type + leading-dash checks."""

    @pytest.mark.parametrize(
        "name",
        [
            "forge",
            "sentinel",
            "weaver",
            "worker-1",
            "worker_1",
            "task.2",
            "a",
            "A_b-c.d",
            "1234567890",
        ],
    )
    def test_valid_names(self, name: str):
        assert _validate_session_name(name) == name

    @pytest.mark.parametrize(
        "name",
        [
            "",
            " ",
            "has space",
            "has;semi",
            "$(rm -rf /)",
            "`cmd`",
            "name|pipe",
            "name&bg",
            "name\nnewline",
            "name\ttab",
            "hash#name",
            "dollar$sign",
            "paren(name)",
        ],
    )
    def test_invalid_characters(self, name: str):
        with pytest.raises(ValueError, match="Invalid|empty"):
            _validate_session_name(name)

    def test_leading_dash_rejected(self):
        with pytest.raises(ValueError, match="start with '-'"):
            _validate_session_name("-flag")

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_session_name("")

    def test_too_long_rejected(self):
        with pytest.raises(ValueError, match="too long"):
            _validate_session_name("a" * 129)

    def test_exactly_max_length_ok(self):
        name = "a" * 128
        assert _validate_session_name(name) == name

    def test_wrong_type_raises(self):
        with pytest.raises(TypeError, match="must be str"):
            _validate_session_name(123)  # type: ignore

    def test_bytes_raises(self):
        with pytest.raises(TypeError, match="must be str"):
            _validate_session_name(b"forge")  # type: ignore


# ── F1 & F2: constructor security defaults ───────────────────────────────────


class TestRemoteMeshTermInit:
    """Verify F1 (host key policy) and F2 (password deprecation)."""

    @pytest.fixture
    def mock_paramiko(self):
        """Patch paramiko used inside meshterm.remote."""
        with patch("meshterm.remote.paramiko") as mock_pm:
            mock_client = MagicMock()
            mock_pm.SSHClient.return_value = mock_client
            mock_pm.RejectPolicy = MagicMock(name="RejectPolicy")
            mock_pm.WarningPolicy = MagicMock(name="WarningPolicy")
            mock_pm.AutoAddPolicy = MagicMock(name="AutoAddPolicy")
            yield mock_pm, mock_client

    def test_strict_host_keys_default_true(self, mock_paramiko):
        """F1: by default, strict mode is active and RejectPolicy is used."""
        mock_pm, mock_client = mock_paramiko
        rt = RemoteMeshTerm(
            host="1.2.3.4",
            username="user",
            key_filename="/fake/key",
        )
        # load_system_host_keys must be called
        assert mock_client.load_system_host_keys.called
        # RejectPolicy used, NOT AutoAddPolicy
        mock_client.set_missing_host_key_policy.assert_called_once()
        arg = mock_client.set_missing_host_key_policy.call_args[0][0]
        assert arg is mock_pm.RejectPolicy.return_value
        # AutoAddPolicy must NOT be used by default
        assert not mock_pm.AutoAddPolicy.called

    def test_strict_false_uses_warning_policy(self, mock_paramiko):
        """F1: explicit opt-out uses WarningPolicy + emits UserWarning."""
        mock_pm, mock_client = mock_paramiko
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rt = RemoteMeshTerm(
                host="1.2.3.4",
                username="user",
                key_filename="/fake/key",
                strict_host_keys=False,
            )
        # WarningPolicy used
        arg = mock_client.set_missing_host_key_policy.call_args[0][0]
        assert arg is mock_pm.WarningPolicy.return_value
        # UserWarning emitted
        assert any(issubclass(x.category, UserWarning) for x in w)
        assert any("MITM protection" in str(x.message) for x in w)

    def test_password_emits_deprecation_warning(self, mock_paramiko):
        """F2: password parameter triggers DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rt = RemoteMeshTerm(
                host="1.2.3.4",
                username="user",
                password="insecure",
            )
        dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep_warnings) >= 1
        assert "key_filename" in str(dep_warnings[0].message)

    def test_key_filename_no_deprecation(self, mock_paramiko):
        """F2: key_filename usage does NOT trigger deprecation."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rt = RemoteMeshTerm(
                host="1.2.3.4",
                username="user",
                key_filename="/fake/key",
            )
        dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep_warnings) == 0

    def test_known_hosts_file_loaded(self, mock_paramiko, tmp_path):
        """Optional known_hosts_file param loads additional host keys."""
        mock_pm, mock_client = mock_paramiko
        khf = tmp_path / "known_hosts"
        khf.write_text("")
        rt = RemoteMeshTerm(
            host="1.2.3.4",
            username="user",
            key_filename="/fake/key",
            known_hosts_file=str(khf),
        )
        mock_client.load_host_keys.assert_called_once()

    def test_paramiko_missing_raises(self):
        """If paramiko is not installed, constructor must raise RuntimeError."""
        with patch("meshterm.remote.paramiko", None):
            with pytest.raises(RuntimeError, match="paramiko not installed"):
                RemoteMeshTerm(host="x", username="u", key_filename="/k")


# ── F6: validator wired into public methods ──────────────────────────────────


class TestMethodValidation:
    """Every public method must reject invalid session names."""

    @pytest.fixture
    def rt(self):
        """Build a RemoteMeshTerm with paramiko mocked."""
        with patch("meshterm.remote.paramiko") as mock_pm:
            mock_client = MagicMock()
            mock_pm.SSHClient.return_value = mock_client
            mock_pm.RejectPolicy = MagicMock()
            rt = RemoteMeshTerm(host="1.2.3.4", username="u", key_filename="/k")
            # Stub _run so methods don't blow up after validation passes
            rt._run = MagicMock(return_value=(0, "", ""))
            yield rt

    @pytest.mark.parametrize(
        "method,args",
        [
            ("has_session", ("bad;name",)),
            ("send_text", ("bad;name", "hello")),
            ("send_command", ("bad;name", "echo x")),
            ("send_key", ("bad;name", "Enter")),
            ("interrupt", ("bad;name",)),
            ("escape", ("bad;name",)),
            ("read_screen", ("bad;name",)),
            ("read_screen_text", ("bad;name",)),
            ("current_command", ("bad;name",)),
            ("pane_pid", ("bad;name",)),
            ("cwd", ("bad;name",)),
            ("create_session", ("bad;name",)),
            ("kill_session", ("bad;name",)),
            ("wait_for", ("bad;name", "pattern")),
        ],
    )
    def test_invalid_name_raises(self, rt, method, args):
        """Every session-taking method must reject injection attempts."""
        with pytest.raises(ValueError, match="Invalid"):
            getattr(rt, method)(*args)

    @pytest.mark.parametrize(
        "method,args",
        [
            ("has_session", ("-flag",)),
            ("send_text", ("-flag", "hello")),
            ("create_session", ("-flag",)),
            ("kill_session", ("-flag",)),
        ],
    )
    def test_leading_dash_rejected(self, rt, method, args):
        with pytest.raises(ValueError, match="start with"):
            getattr(rt, method)(*args)

    def test_valid_session_passes(self, rt):
        """Valid names actually invoke _run (not blocked by validator)."""
        rt.has_session("forge")
        assert rt._run.called
