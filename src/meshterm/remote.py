"""
remote.py — Remote meshterm control over SSH

Lets Eagle/Poseidon/any peer control Titan's workers (forge/sentinel/weaver)
without running meshterm locally on Titan. Wraps `tmux send-keys` and
`tmux capture-pane` over SSH using paramiko.

Design rationale:
    - meshterm's core IPC is local-only (Unix socket) by design
    - For cross-host control, we use SSH as transport, tmux as backend
    - This matches the LibtmuxSession API 1:1 so the same code works local+remote

Security (Nebula audit 2026-04-12):
    - F1: Host key verification is STRICT by default (RejectPolicy).
          Unknown SSH hosts are REJECTED to prevent MITM attacks.
          Use strict_host_keys=False for explicit opt-in to WarningPolicy.
    - F2: Password authentication is DEPRECATED. Use key_filename for
          SSH key-based auth. Password param emits DeprecationWarning.
    - F6: Session names are validated against [a-zA-Z0-9_.-]+ whitelist
          to prevent tmux argument injection (e.g. names starting with '-').

Usage (recommended — key-based auth):
    from meshterm.remote import RemoteMeshTerm
    rt = RemoteMeshTerm(
        "192.0.2.101",
        username="server",
        key_filename="~/.ssh/id_ed25519",
    )
    rt.send_text("forge", "echo hello", enter=True)
    screen = rt.read_screen("forge", lines=30)
    print(screen)
    rt.close()

Usage (legacy password — DISCOURAGED, emits DeprecationWarning):
    rt = RemoteMeshTerm("192.0.2.101", username="server", password="s")
"""

from __future__ import annotations

import os
import re
import shlex
import time
import warnings
from typing import Optional

try:
    import paramiko  # type: ignore
except ImportError:
    paramiko = None  # Lazy import — only required when RemoteMeshTerm is used


# F6 fix (Nebula audit): session name whitelist to prevent tmux arg injection.
# tmux session names technically accept many characters, but we restrict to
# a safe subset: letters, digits, underscore, dot, dash. Names starting with
# '-' would be parsed as tmux flags; shell metacharacters would be injection
# vectors; empty strings cause ambiguous target resolution.
_SESSION_NAME_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")

# Default timings and limits (Nebula audit R3 item 4: named constants).
# Use these as parameter defaults throughout RemoteMeshTerm so callers can
# override per-instance while the defaults remain documented and test-able.
DEFAULT_SSH_PORT: int = 22
DEFAULT_CONNECT_TIMEOUT: float = 10.0     # seconds to establish SSH channel
DEFAULT_COMMAND_TIMEOUT: float = 15.0     # seconds per remote exec_command
DEFAULT_WAIT_FOR_TIMEOUT: float = 30.0    # seconds for wait_for() pattern poll
DEFAULT_POLL_INTERVAL: float = 1.0        # seconds between wait_for() checks
DEFAULT_READ_LINES: int = 30              # default capture-pane line count
MAX_SESSION_NAME_LENGTH: int = 128        # hard upper bound for whitelist


def _validate_session_name(name: str) -> str:
    """Validate tmux session name against whitelist. Returns the name on success.

    Raises:
        TypeError: name is not a str.
        ValueError: name is empty, too long (>128), or contains invalid chars.
    """
    if not isinstance(name, str):
        raise TypeError(f"Session name must be str, got {type(name).__name__}")
    if not name:
        raise ValueError("Session name must not be empty")
    if len(name) > MAX_SESSION_NAME_LENGTH:
        raise ValueError(
            f"Session name too long: {len(name)} > {MAX_SESSION_NAME_LENGTH}"
        )
    if name.startswith("-"):
        raise ValueError(f"Session name cannot start with '-': {name!r}")
    if not _SESSION_NAME_RE.match(name):
        raise ValueError(
            f"Invalid session name {name!r}: must match [a-zA-Z0-9_.-]+"
        )
    return name


class RemoteMeshTerm:
    """Control a remote host's tmux sessions over SSH.

    API mirrors LibtmuxSession/LibtmuxApp for drop-in compatibility.

    Security: Strict host key verification (F1), deprecated password auth (F2),
    session name whitelist (F6). See module docstring for details.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
        port: int = DEFAULT_SSH_PORT,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        strict_host_keys: bool = True,
        known_hosts_file: Optional[str] = None,
    ):
        """Connect to a remote host over SSH.

        Args:
            host: Remote hostname or IP.
            username: SSH user.
            password: DEPRECATED. Emits DeprecationWarning. Use key_filename.
            key_filename: Path to SSH private key (preferred auth method).
            port: SSH port (default 22).
            connect_timeout: Connection timeout in seconds.
            strict_host_keys: If True (default), reject unknown host keys
                              (paramiko.RejectPolicy). If False, use
                              WarningPolicy — emits warning but connects.
                              System known_hosts is always loaded.
            known_hosts_file: Optional explicit known_hosts path (in addition
                              to system known_hosts).
        """
        if paramiko is None:
            raise RuntimeError(
                "paramiko not installed. Install with: pip install paramiko"
            )

        # F2 fix (Nebula audit): warn on password auth usage
        if password is not None:
            warnings.warn(
                "Password authentication is insecure and deprecated. "
                "Use key_filename='~/.ssh/id_ed25519' instead. "
                "Password auth will be removed in meshterm v0.3.",
                DeprecationWarning,
                stacklevel=2,
            )

        self.host = host
        self.username = username
        self._client = paramiko.SSHClient()

        # F1 fix (Nebula audit): load system known_hosts, reject unknowns by default
        self._client.load_system_host_keys()
        if known_hosts_file is not None:
            self._client.load_host_keys(os.path.expanduser(known_hosts_file))

        if strict_host_keys:
            # Production default: reject ALL unknown host keys (MITM protection)
            self._client.set_missing_host_key_policy(paramiko.RejectPolicy())
        else:
            # Explicit opt-in: warn but still connect (dev/test only)
            warnings.warn(
                "strict_host_keys=False: unknown host keys will be accepted "
                "with a warning. This disables MITM protection. Use only on "
                "trusted LANs.",
                UserWarning,
                stacklevel=2,
            )
            self._client.set_missing_host_key_policy(paramiko.WarningPolicy())

        try:
            self._client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                key_filename=key_filename,
                timeout=connect_timeout,
                look_for_keys=bool(key_filename is None and password is None),
            )
        finally:
            # F2 defense-in-depth: drop local password reference after use
            # (paramiko may still hold its own reference internally)
            if password is not None:
                password = None  # noqa: F841

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass

    def __enter__(self) -> "RemoteMeshTerm":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # ----- low-level ssh exec -----

    def _run(self, cmd: str, timeout: float = DEFAULT_COMMAND_TIMEOUT) -> tuple[int, str, str]:
        """Execute one shell command, return (exit_code, stdout, stderr)."""
        stdin, stdout, stderr = self._client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        rc = stdout.channel.recv_exit_status()
        return rc, out, err

    # ----- session discovery -----

    def list_sessions(self) -> list[dict[str, str]]:
        """List all tmux sessions on the remote host."""
        rc, out, _ = self._run(
            "tmux list-sessions -F '#{session_name}:#{session_windows}:#{session_attached}'"
        )
        if rc != 0:
            return []
        sessions = []
        for line in out.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 2:
                sessions.append(
                    {
                        "name": parts[0],
                        "windows": parts[1],
                        "attached": parts[2] if len(parts) > 2 else "0",
                    }
                )
        return sessions

    def has_session(self, name: str) -> bool:
        q = shlex.quote(_validate_session_name(name))
        rc, _, _ = self._run(f"tmux has-session -t {q} 2>/dev/null")
        return rc == 0

    # ----- send (write) operations -----

    def send_text(
        self, session: str, text: str, enter: bool = False, wait_after: float = 0.0
    ) -> None:
        """Send literal text to tmux session. If enter=True, append Enter."""
        q_text = shlex.quote(text)
        q_name = shlex.quote(_validate_session_name(session))
        self._run(f"tmux send-keys -t {q_name} -l {q_text}")
        if wait_after:
            time.sleep(wait_after)
        if enter:
            self._run(f"tmux send-keys -t {q_name} Enter")

    def send_command(self, session: str, command: str, wait: float = 1.0) -> None:
        """RAMAS SEND-VERIFY-PROCEED: type → wait → Enter."""
        q_name = shlex.quote(_validate_session_name(session))
        self.send_text(session, command, enter=False)
        time.sleep(wait)
        self._run(f"tmux send-keys -t {q_name} Enter")

    def send_key(self, session: str, key: str) -> None:
        """Send a named key: Enter, Escape, C-c (Ctrl+C), C-d, Up, Down, etc."""
        q_name = shlex.quote(_validate_session_name(session))
        self._run(f"tmux send-keys -t {q_name} {shlex.quote(key)}")

    def interrupt(self, session: str) -> None:
        """Send Ctrl+C to the session."""
        self.send_key(session, "C-c")

    def escape(self, session: str) -> None:
        """Send Escape key."""
        self.send_key(session, "Escape")

    # ----- read operations -----

    def read_screen(self, session: str, lines: int = DEFAULT_READ_LINES) -> list[str]:
        """Return the last N lines of the active pane as a list of strings."""
        q_name = shlex.quote(_validate_session_name(session))
        rc, out, _ = self._run(f"tmux capture-pane -t {q_name} -p -S -{int(lines)}")
        if rc != 0:
            return []
        return out.splitlines()

    def read_screen_text(self, session: str, lines: int = DEFAULT_READ_LINES) -> str:
        """Return the last N lines joined as a single string."""
        return "\n".join(self.read_screen(session, lines))

    def current_command(self, session: str) -> str:
        """What command is currently running in the active pane?"""
        q_name = shlex.quote(_validate_session_name(session))
        rc, out, _ = self._run(
            f"tmux display-message -t {q_name} -p '#{{pane_current_command}}'"
        )
        return out.strip() if rc == 0 else ""

    def pane_pid(self, session: str) -> int:
        q_name = shlex.quote(_validate_session_name(session))
        rc, out, _ = self._run(
            f"tmux display-message -t {q_name} -p '#{{pane_pid}}'"
        )
        try:
            return int(out.strip()) if rc == 0 else 0
        except ValueError:
            return 0

    def cwd(self, session: str) -> str:
        q_name = shlex.quote(_validate_session_name(session))
        rc, out, _ = self._run(
            f"tmux display-message -t {q_name} -p '#{{pane_current_path}}'"
        )
        return out.strip() if rc == 0 else ""

    # ----- wait / poll -----

    def wait_for(
        self,
        session: str,
        pattern: str,
        timeout: float = DEFAULT_WAIT_FOR_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ) -> bool:
        """Block until `pattern` appears in the pane output or timeout expires."""
        _validate_session_name(session)  # fail fast before entering poll loop
        deadline = time.time() + timeout
        while time.time() < deadline:
            text = self.read_screen_text(session, lines=100)
            if pattern in text:
                return True
            time.sleep(poll_interval)
        return False

    # ----- lifecycle -----

    def create_session(self, name: str, command: Optional[str] = None) -> None:
        """Create a new tmux session (detached)."""
        q_name = shlex.quote(_validate_session_name(name))
        if command:
            self._run(f"tmux new-session -d -s {q_name} {shlex.quote(command)}")
        else:
            self._run(f"tmux new-session -d -s {q_name}")

    def kill_session(self, name: str) -> None:
        q_name = shlex.quote(_validate_session_name(name))
        self._run(f"tmux kill-session -t {q_name}")
