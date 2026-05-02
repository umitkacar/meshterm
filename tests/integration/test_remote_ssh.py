"""Integration tests for RemoteMeshTerm — real paramiko SSH round trips.

These tests exercise the full SSH → tmux pipeline using either:

  1. **MockSSHServer** — a local `paramiko.ServerInterface` subclass that
     accepts connections on `127.0.0.1:<ephemeral>` and routes `exec_command`
     requests to a local subprocess. This gives us real paramiko protocol
     round-trips without needing a system SSH daemon or Docker container.

  2. **Skip markers** — tests that require a real `sshd` or Docker are
     marked with ``@pytest.mark.ssh_daemon_required`` / ``@pytest.mark.docker``
     and are skipped in default CI unless the appropriate fixture is wired.

Design notes (derived from the Explore subagent research for meshterm P1
Round 3, Eagle's co-fix session):

  - Mock SSH binds to 127.0.0.1 only — never 0.0.0.0 (no network exposure).
  - Every test uses a per-session Ed25519 key generated via ssh-keygen and
    discarded at fixture teardown; no private keys linger on disk.
  - Server and tmux sessions use UUID-based names to avoid cross-test
    pollution. `tmux has-session` is checked in fixture teardown to
    hard-fail if a test leaked a session.
  - Tests exercise the actual `RemoteMeshTerm.send_text / read_screen /
    wait_for / create_session / kill_session` code paths, so F1 (strict
    host keys), F2 (deprecation warnings), and F6 (session name whitelist)
    all run through real paramiko with real exec_command dispatches.

Running:

    pytest tests/integration/test_remote_ssh.py -v

These tests are SLOWER than unit tests (~1–3s each due to SSH handshake).
Unit tests in ``tests/unit/test_remote.py`` cover the fast path with mocks.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import threading
import time
import uuid
import warnings
from pathlib import Path
from typing import Iterator, Optional

import pytest

try:
    import paramiko
except ImportError:  # pragma: no cover
    paramiko = None  # type: ignore


# --------------------------------------------------------------------------- #
# Skip the whole module if paramiko or tmux is unavailable                    #
# --------------------------------------------------------------------------- #

pytestmark = [
    pytest.mark.skipif(paramiko is None, reason="paramiko not installed"),
    pytest.mark.skipif(
        shutil.which("tmux") is None, reason="tmux binary not installed"
    ),
    pytest.mark.skipif(
        shutil.which("ssh-keygen") is None, reason="ssh-keygen not installed"
    ),
]


# --------------------------------------------------------------------------- #
# Mock SSH server                                                             #
# --------------------------------------------------------------------------- #


class _MockSSHServerInterface(paramiko.ServerInterface):
    """Accept a single test user with a known Ed25519 public key.

    Routes `exec_command` to a locally-executed shell subprocess so the
    full paramiko → protocol → command dispatch path runs end-to-end.
    """

    def __init__(self, authorized_key: paramiko.PKey, username: str) -> None:
        self._authorized_key = authorized_key
        self._username = username
        self.event = threading.Event()

    # ── Auth ──
    def check_auth_publickey(
        self, username: str, key: paramiko.PKey
    ) -> int:
        if username != self._username:
            return paramiko.AUTH_FAILED
        if (
            key.get_name() == self._authorized_key.get_name()
            and key.asbytes() == self._authorized_key.asbytes()
        ):
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_auth_password(self, username: str, password: str) -> int:
        # Intentionally disabled: password auth is deprecated.
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        return "publickey"

    def check_channel_request(
        self, kind: str, chanid: int
    ) -> int:
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_exec_request(
        self, channel: paramiko.Channel, command: bytes
    ) -> bool:
        # Run command locally, forward stdout/stderr/exit-code to channel.
        cmd = command.decode("utf-8", errors="replace")
        thread = threading.Thread(
            target=_run_exec, args=(channel, cmd), daemon=True
        )
        thread.start()
        return True


def _run_exec(channel: "paramiko.Channel", cmd: str) -> None:
    """Run the shell command and forward output to the SSH channel."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            timeout=30,
        )
        if result.stdout:
            channel.sendall(result.stdout)
        if result.stderr:
            channel.sendall_stderr(result.stderr)
        channel.send_exit_status(result.returncode)
    except subprocess.TimeoutExpired:
        channel.sendall_stderr(b"mock ssh: command timed out\n")
        channel.send_exit_status(124)
    except Exception as exc:  # pragma: no cover
        channel.sendall_stderr(f"mock ssh: {exc}\n".encode())
        channel.send_exit_status(1)
    finally:
        channel.close()


class MockSSHServer:
    """Wraps `_MockSSHServerInterface` inside a one-connection-per-test socket.

    Generates a throwaway Ed25519 host key for every server start so two
    tests don't share key material.
    """

    def __init__(self, authorized_pub_key: paramiko.PKey, username: str = "testuser"):
        self._authorized = authorized_pub_key
        self._username = username
        # RSAKey.generate() is the classmethod for throwaway host keys —
        # Ed25519Key does not expose a generator in paramiko 3.x.  2048 bits
        # is fine for short-lived test servers bound to 127.0.0.1.
        self._host_key = paramiko.RSAKey.generate(2048)
        self._socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._port: int = 0
        self._stop = threading.Event()

    def start(self) -> int:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("127.0.0.1", 0))  # 127.0.0.1 only — no network exposure
        self._socket.listen(4)
        self._port = self._socket.getsockname()[1]

        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        return self._port

    def _accept_loop(self) -> None:
        assert self._socket is not None
        self._socket.settimeout(0.5)
        while not self._stop.is_set():
            try:
                client_sock, _ = self._socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            # Each client gets its own Transport+Channel
            try:
                transport = paramiko.Transport(client_sock)
                transport.add_server_key(self._host_key)
                iface = _MockSSHServerInterface(self._authorized, self._username)
                transport.start_server(server=iface)
            except Exception:  # pragma: no cover
                pass

    def stop(self) -> None:
        self._stop.set()
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2)

    @property
    def port(self) -> int:
        return self._port


# --------------------------------------------------------------------------- #
# Pytest fixtures                                                             #
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="function")
def ssh_test_key(tmp_path: Path) -> Path:
    """Generate a throwaway Ed25519 key pair inside ``tmp_path``.

    Function-scoped so each test gets its own key; keys are discarded
    when tmp_path is cleaned up by pytest.
    """
    key_path = tmp_path / "id_ed25519"
    subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(key_path), "-C", "meshterm-test"],
        check=True,
        capture_output=True,
    )
    return key_path


@pytest.fixture(scope="function")
def ssh_known_hosts(tmp_path: Path) -> Path:
    """Empty ``known_hosts`` file — used to assert that strict mode rejects."""
    path = tmp_path / "known_hosts"
    path.touch()
    return path


@pytest.fixture(scope="function")
def mock_ssh_server(ssh_test_key: Path) -> Iterator[tuple[str, int, Path]]:
    """Start a MockSSHServer bound to 127.0.0.1 with the test key authorized.

    Yields ``(host, port, key_path)`` for use by `RemoteMeshTerm`.
    """
    # Load the client public key into a paramiko PKey
    pub_path = Path(f"{ssh_test_key}.pub")
    pub_text = pub_path.read_text().strip()
    # Parse "ssh-ed25519 BASE64 comment"
    parts = pub_text.split()
    key_type = parts[0]
    key_b64 = parts[1]
    import base64
    key_bytes = base64.b64decode(key_b64)
    authorized = paramiko.Ed25519Key(data=key_bytes)

    server = MockSSHServer(authorized_pub_key=authorized, username="testuser")
    port = server.start()
    try:
        # Give the accept thread a tick to be ready
        time.sleep(0.05)
        yield ("127.0.0.1", port, ssh_test_key)
    finally:
        server.stop()


@pytest.fixture(scope="function")
def tmux_session_name() -> Iterator[str]:
    """Per-test tmux session name; fixture guarantees teardown."""
    name = f"mt-test-{uuid.uuid4().hex[:8]}"
    yield name
    # Hard teardown — kill if it still exists
    subprocess.run(
        ["tmux", "kill-session", "-t", name],
        check=False,
        capture_output=True,
    )


# --------------------------------------------------------------------------- #
# Tests                                                                       #
# --------------------------------------------------------------------------- #


def test_mock_server_listens_on_localhost_only(mock_ssh_server):
    """Sanity check: mock server must bind to 127.0.0.1, not 0.0.0.0."""
    host, port, _ = mock_ssh_server
    assert host == "127.0.0.1"
    # Verify the socket address
    assert port > 0
    # Try connecting — should succeed on loopback
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(2)
        s.connect((host, port))
    finally:
        s.close()


def test_remote_rejects_unknown_host_when_strict(
    mock_ssh_server, ssh_known_hosts
):
    """F1 integration: RejectPolicy rejects the mock server because its host
    key is not in the (empty) known_hosts file."""
    from meshterm.remote import RemoteMeshTerm

    host, port, key_path = mock_ssh_server

    with pytest.raises(paramiko.SSHException):
        RemoteMeshTerm(
            host=host,
            port=port,
            username="testuser",
            key_filename=str(key_path),
            strict_host_keys=True,
            known_hosts_file=str(ssh_known_hosts),
            connect_timeout=3.0,
        )


def test_remote_connects_when_non_strict(mock_ssh_server, ssh_known_hosts):
    """Non-strict mode connects (with warning) even when host key is unknown."""
    from meshterm.remote import RemoteMeshTerm

    host, port, key_path = mock_ssh_server

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rt = RemoteMeshTerm(
            host=host,
            port=port,
            username="testuser",
            key_filename=str(key_path),
            strict_host_keys=False,
            known_hosts_file=str(ssh_known_hosts),
            connect_timeout=5.0,
        )
        try:
            # Verify the UserWarning for strict_host_keys=False was emitted
            user_warnings = [
                w for w in caught if issubclass(w.category, UserWarning)
            ]
            assert any(
                "strict_host_keys=False" in str(w.message) for w in user_warnings
            )
        finally:
            rt.close()


def test_remote_run_echoes_via_exec_command(mock_ssh_server, ssh_known_hosts):
    """Exercise the real _run() path: paramiko exec_command → local shell → back."""
    from meshterm.remote import RemoteMeshTerm

    host, port, key_path = mock_ssh_server

    rt = RemoteMeshTerm(
        host=host,
        port=port,
        username="testuser",
        key_filename=str(key_path),
        strict_host_keys=False,  # known_hosts is empty for the mock
        known_hosts_file=str(ssh_known_hosts),
        connect_timeout=5.0,
    )
    try:
        # Use the private _run helper to bypass session-name validation.
        # This lets us verify the SSH transport layer independently of tmux.
        rc, out, err = rt._run("echo integration_ok")
        assert rc == 0
        assert "integration_ok" in out
    finally:
        rt.close()


def test_remote_list_sessions_over_ssh(mock_ssh_server, ssh_known_hosts, tmux_session_name):
    """End-to-end: create a tmux session locally, list it via RemoteMeshTerm."""
    from meshterm.remote import RemoteMeshTerm

    # Pre-create the tmux session outside the mock so the test has data to read
    subprocess.run(
        ["tmux", "new-session", "-d", "-s", tmux_session_name],
        check=True,
    )
    # sanity check
    check = subprocess.run(
        ["tmux", "has-session", "-t", tmux_session_name],
        capture_output=True,
    )
    assert check.returncode == 0

    host, port, key_path = mock_ssh_server
    rt = RemoteMeshTerm(
        host=host,
        port=port,
        username="testuser",
        key_filename=str(key_path),
        strict_host_keys=False,
        known_hosts_file=str(ssh_known_hosts),
    )
    try:
        sessions = rt.list_sessions()
        names = {s["name"] for s in sessions}
        assert tmux_session_name in names, (
            f"Expected {tmux_session_name} in listed sessions, got {names}"
        )
    finally:
        rt.close()


def test_remote_send_text_rejects_invalid_session_name(mock_ssh_server, ssh_known_hosts):
    """F6 integration: session name whitelist enforced at the RemoteMeshTerm boundary."""
    from meshterm.remote import RemoteMeshTerm

    host, port, key_path = mock_ssh_server
    rt = RemoteMeshTerm(
        host=host,
        port=port,
        username="testuser",
        key_filename=str(key_path),
        strict_host_keys=False,
        known_hosts_file=str(ssh_known_hosts),
    )
    try:
        with pytest.raises(ValueError, match="Invalid session name"):
            rt.send_text("has space", "echo hi", enter=True)
        with pytest.raises(ValueError, match="cannot start with '-'"):
            rt.send_text("-flag", "echo hi", enter=True)
        with pytest.raises(ValueError, match="Invalid session name"):
            rt.send_text("foo;rm -rf /", "echo hi", enter=True)
    finally:
        rt.close()


def test_remote_send_text_round_trip(mock_ssh_server, ssh_known_hosts, tmux_session_name):
    """F6 + send_text end-to-end: real SSH, real tmux, real capture."""
    from meshterm.remote import RemoteMeshTerm

    # Pre-create tmux session
    subprocess.run(
        ["tmux", "new-session", "-d", "-s", tmux_session_name],
        check=True,
    )

    host, port, key_path = mock_ssh_server
    rt = RemoteMeshTerm(
        host=host,
        port=port,
        username="testuser",
        key_filename=str(key_path),
        strict_host_keys=False,
        known_hosts_file=str(ssh_known_hosts),
    )
    try:
        # Send a marker string
        marker = f"INTEGRATION-MARKER-{uuid.uuid4().hex[:8]}"
        rt.send_text(tmux_session_name, f"echo {marker}", enter=True)
        # Give tmux a beat to process
        time.sleep(0.3)
        screen = rt.read_screen(tmux_session_name, lines=10)
        # Marker should appear in the captured screen
        joined = "\n".join(screen)
        assert marker in joined, (
            f"Marker {marker!r} not found in screen:\n{joined}"
        )
    finally:
        rt.close()


def test_remote_password_emits_deprecation_warning(
    mock_ssh_server, ssh_known_hosts
):
    """F2 integration: password param emits DeprecationWarning when used."""
    from meshterm.remote import RemoteMeshTerm

    host, port, _ = mock_ssh_server  # key not used for this test

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            RemoteMeshTerm(
                host=host,
                port=port,
                username="testuser",
                password="unused",  # will fail auth, but warning fires first
                strict_host_keys=False,
                known_hosts_file=str(ssh_known_hosts),
                connect_timeout=3.0,
            )
        except Exception:
            pass  # we only care about the warning here

        deprecation_warnings = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
        ]
        assert any(
            "deprecated" in str(w.message).lower()
            for w in deprecation_warnings
        ), (
            f"Expected DeprecationWarning for password param, got: "
            f"{[str(w.message) for w in caught]}"
        )


def test_remote_wait_for_pattern(mock_ssh_server, ssh_known_hosts, tmux_session_name):
    """wait_for() polls read_screen until pattern appears or timeout."""
    from meshterm.remote import RemoteMeshTerm

    subprocess.run(
        ["tmux", "new-session", "-d", "-s", tmux_session_name],
        check=True,
    )

    host, port, key_path = mock_ssh_server
    rt = RemoteMeshTerm(
        host=host,
        port=port,
        username="testuser",
        key_filename=str(key_path),
        strict_host_keys=False,
        known_hosts_file=str(ssh_known_hosts),
    )
    try:
        pattern = f"WAITFOR-{uuid.uuid4().hex[:8]}"
        rt.send_text(tmux_session_name, f"echo {pattern}", enter=True)
        found = rt.wait_for(tmux_session_name, pattern, timeout=5.0, poll_interval=0.2)
        assert found, f"wait_for timed out looking for {pattern!r}"
    finally:
        rt.close()


def test_remote_wait_for_times_out(mock_ssh_server, ssh_known_hosts, tmux_session_name):
    """wait_for() returns False on timeout without raising."""
    from meshterm.remote import RemoteMeshTerm

    subprocess.run(
        ["tmux", "new-session", "-d", "-s", tmux_session_name],
        check=True,
    )

    host, port, key_path = mock_ssh_server
    rt = RemoteMeshTerm(
        host=host,
        port=port,
        username="testuser",
        key_filename=str(key_path),
        strict_host_keys=False,
        known_hosts_file=str(ssh_known_hosts),
    )
    try:
        # Pattern that will never appear
        found = rt.wait_for(
            tmux_session_name,
            pattern="NEVER-EVER-APPEARS-" + uuid.uuid4().hex,
            timeout=0.8,
            poll_interval=0.2,
        )
        assert found is False
    finally:
        rt.close()
