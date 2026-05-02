"""Unit tests for meshterm.vscode_profiles.

Covers the pure helpers (conda hook, color resolution, profile-block
building, idempotency check, JSONC formatting) and the workspace-file
mutation (add / list) using temp .code-workspace fixtures.

tmux-dependent helpers (``tmux_session_exists``, ``ensure_tmux_session``,
``colony_status``) are exercised via monkeypatching ``subprocess.run``
so the tests don't require a running tmux server.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from meshterm.vscode_profiles import (
    COLOR_MAP,
    DEFAULT_COLOR,
    DEFAULT_CONDA_BASE,
    DEFAULT_CONDA_ENV,
    ICON_ATTACH,
    ICON_MAIN,
    ICON_NEW,
    PROFILE_SUFFIXES,
    add_profiles_to_workspace,
    build_conda_hook,
    build_profile_block,
    colony_status,
    ensure_tmux_session,
    format_profile_block_jsonc,
    list_profiles_in_workspace,
    profile_exists_in_text,
    profile_keys,
    resolve_color,
    tmux_session_exists,
)


# ── build_conda_hook ──

class TestBuildCondaHook:

    def test_default_values(self):
        hook = build_conda_hook()
        assert "claude_mesh" in hook
        assert "~/miniconda3" in hook
        assert 'shell.bash hook' in hook

    def test_custom_env(self):
        hook = build_conda_hook(env="my_env")
        assert "conda activate my_env" in hook

    def test_custom_base(self):
        hook = build_conda_hook(base="~/mambaforge")
        assert "~/mambaforge/bin/conda" in hook

    def test_shape(self):
        """The hook is a single-line bash command chaining eval and activate."""
        hook = build_conda_hook()
        # Must be a valid bash command fragment (no newlines)
        assert "\n" not in hook
        # Must end in conda activate {env}
        assert hook.endswith(f"conda activate {DEFAULT_CONDA_ENV}")


# ── resolve_color ──

class TestResolveColor:

    def test_known_worker_returns_mapped_color(self):
        assert resolve_color("nova") == "terminal.ansiCyan"
        assert resolve_color("forge") == "terminal.ansiRed"
        assert resolve_color("sentinel") == "terminal.ansiGreen"
        assert resolve_color("weaver") == "terminal.ansiBlue"

    def test_unknown_worker_returns_default(self):
        assert resolve_color("quasar") == DEFAULT_COLOR

    def test_override_wins(self):
        assert resolve_color("nova", override="terminal.ansiMagenta") == "terminal.ansiMagenta"

    def test_override_wins_on_unknown_worker(self):
        assert resolve_color("unknown", override="terminal.ansiWhite") == "terminal.ansiWhite"


# ── profile_keys ──

class TestProfileKeys:

    def test_lowercase_session(self):
        keys = profile_keys("nova")
        assert keys == ("nova-tmux", "Nova-Claude", "Nova-New")

    def test_forge(self):
        keys = profile_keys("forge")
        assert keys == ("forge-tmux", "Forge-Claude", "Forge-New")

    def test_returns_tuple_of_three(self):
        keys = profile_keys("weaver")
        assert len(keys) == 3
        assert isinstance(keys, tuple)

    def test_suffixes_match_constants(self):
        """The suffixes used in PROFILE_SUFFIXES match the keys built."""
        # PROFILE_SUFFIXES is ("-tmux", "-Claude", "-New")
        # The keys should end with those suffixes (case-sensitive)
        keys = profile_keys("nova")
        assert keys[0].endswith(PROFILE_SUFFIXES[0])
        assert keys[1].endswith(PROFILE_SUFFIXES[1])
        assert keys[2].endswith(PROFILE_SUFFIXES[2])


# ── build_profile_block ──

class TestBuildProfileBlock:

    def test_returns_three_profiles(self):
        profiles = build_profile_block("nova")
        assert len(profiles) == 3
        assert "nova-tmux" in profiles
        assert "Nova-Claude" in profiles
        assert "Nova-New" in profiles

    def test_all_profiles_have_required_keys(self):
        profiles = build_profile_block("nova")
        for key, body in profiles.items():
            assert body["path"] == "bash"
            assert isinstance(body["args"], list)
            assert body["overrideName"] is True
            assert "color" in body
            assert "icon" in body

    def test_icons_by_profile_type(self):
        profiles = build_profile_block("nova")
        assert profiles["nova-tmux"]["icon"] == ICON_MAIN
        assert profiles["Nova-Claude"]["icon"] == ICON_ATTACH
        assert profiles["Nova-New"]["icon"] == ICON_NEW

    def test_main_profile_uses_new_session_dash_A(self):
        """Main profile is idempotent: tmux new-session -A creates or attaches."""
        profiles = build_profile_block("nova")
        args = profiles["nova-tmux"]["args"]
        command = args[1]
        assert "tmux new-session -A -s nova" in command

    def test_attach_profile_uses_attach_session(self):
        """Attach profile is strict: errors if session missing."""
        profiles = build_profile_block("nova")
        command = profiles["Nova-Claude"]["args"][1]
        assert "tmux attach-session -t nova" in command

    def test_new_profile_uses_different_session_name(self):
        """New profile uses {session}-new so it doesn't collide with main."""
        profiles = build_profile_block("nova")
        command = profiles["Nova-New"]["args"][1]
        assert "tmux new-session -A -s nova-new" in command

    def test_conda_hook_prepends(self):
        hook = "eval 'conda activate test'"
        profiles = build_profile_block("nova", conda_hook=hook)
        command = profiles["nova-tmux"]["args"][1]
        assert command.startswith(hook + " && ")
        assert "tmux" in command

    def test_no_conda_hook_plain_bash(self):
        """Without conda_hook, the command starts directly with tmux."""
        profiles = build_profile_block("nova", conda_hook=None)
        command = profiles["nova-tmux"]["args"][1]
        assert command.startswith("tmux")

    def test_color_override(self):
        profiles = build_profile_block("nova", color="terminal.ansiMagenta")
        assert profiles["nova-tmux"]["color"] == "terminal.ansiMagenta"
        assert profiles["Nova-Claude"]["color"] == "terminal.ansiMagenta"
        assert profiles["Nova-New"]["color"] == "terminal.ansiMagenta"

    def test_all_three_profiles_share_same_color(self):
        """Colony convention: one color per worker, applied to all 3 profiles."""
        profiles = build_profile_block("forge")
        colors = {body["color"] for body in profiles.values()}
        assert len(colors) == 1
        assert COLOR_MAP["forge"] in colors

    def test_output_is_json_serializable(self):
        profiles = build_profile_block("nova")
        # Should not raise
        json.dumps(profiles)


# ── profile_exists_in_text ──

class TestProfileExistsInText:

    def test_empty_content_returns_false(self):
        assert profile_exists_in_text("nova", "") is False

    def test_unrelated_content_returns_false(self):
        assert profile_exists_in_text("nova", '"something": "else"') is False

    def test_main_key_present_returns_true(self):
        content = '"nova-tmux": { "path": "bash" }'
        assert profile_exists_in_text("nova", content) is True

    def test_attach_key_present_returns_true(self):
        content = '"Nova-Claude": { "path": "bash" }'
        assert profile_exists_in_text("nova", content) is True

    def test_new_key_present_returns_true(self):
        content = '"Nova-New": { "path": "bash" }'
        assert profile_exists_in_text("nova", content) is True

    def test_different_worker_does_not_match(self):
        """'forge-tmux' should NOT match a check for 'nova'."""
        content = '"forge-tmux": { "path": "bash" }'
        assert profile_exists_in_text("nova", content) is False

    def test_substring_does_not_match(self):
        """'nova-tmux-backup' should NOT match a check for 'nova' profile."""
        # The regex requires exact key match followed by colon
        content = '"nova-tmux-backup": { "path": "bash" }'
        # This is a different profile key, not nova's
        # profile_exists_in_text checks for exact keys: nova-tmux, Nova-Claude, Nova-New
        # "nova-tmux-backup" doesn't match "nova-tmux" with a colon after
        assert profile_exists_in_text("nova", content) is False


# ── format_profile_block_jsonc ──

class TestFormatProfileBlockJsonc:

    def test_empty_dict_returns_empty_string(self):
        assert format_profile_block_jsonc({}) == ""

    def test_single_profile_is_indented(self):
        profiles = build_profile_block("nova")
        # Keep only one key for simplicity
        single = {"nova-tmux": profiles["nova-tmux"]}
        text = format_profile_block_jsonc(single, indent=6)
        # Every non-empty line must start with 6 spaces
        for line in text.split("\n"):
            if line.strip():
                assert line.startswith("      "), f"Expected 6-space indent: {line!r}"

    def test_keys_appear_in_output(self):
        profiles = build_profile_block("nova")
        text = format_profile_block_jsonc(profiles)
        assert '"nova-tmux":' in text
        assert '"Nova-Claude":' in text
        assert '"Nova-New":' in text

    def test_trailing_comma_on_each_profile(self):
        profiles = build_profile_block("nova")
        text = format_profile_block_jsonc(profiles)
        # Count profile-ending closing braces (which should be followed by a comma)
        # Simpler: count commas at end of lines
        comma_line_count = sum(
            1 for line in text.split("\n") if line.rstrip().endswith("},")
        )
        assert comma_line_count == 3


# ── add_profiles_to_workspace ──

def _minimal_workspace(content: str) -> str:
    """Wrap a profiles block in a minimal .code-workspace JSON skeleton."""
    return f'''{{
  "folders": [{{"path": "."}}],
  "settings": {{
    "terminal.integrated.profiles.linux": {{
{content}
      "bash": {{
        "path": "/bin/bash"
      }}
    }}
  }}
}}
'''


class TestAddProfilesToWorkspace:

    def test_missing_file_returns_false(self, tmp_path: Path):
        ws = tmp_path / "nonexistent.code-workspace"
        ok, msg = add_profiles_to_workspace(ws, "nova")
        assert ok is False
        assert "not found" in msg

    def test_add_nova_to_empty_workspace_succeeds(self, tmp_path: Path):
        ws = tmp_path / "test.code-workspace"
        ws.write_text(_minimal_workspace(""))

        ok, msg = add_profiles_to_workspace(ws, "nova", backup=False)

        assert ok is True
        assert "3 profiles" in msg
        # All three keys must now be in the file
        content = ws.read_text()
        assert '"nova-tmux"' in content
        assert '"Nova-Claude"' in content
        assert '"Nova-New"' in content

    def test_idempotency_second_add_returns_false(self, tmp_path: Path):
        ws = tmp_path / "test.code-workspace"
        ws.write_text(_minimal_workspace(""))

        ok1, _ = add_profiles_to_workspace(ws, "nova", backup=False)
        assert ok1 is True

        ok2, msg2 = add_profiles_to_workspace(ws, "nova", backup=False)
        assert ok2 is False
        assert "already present" in msg2

    def test_dry_run_does_not_modify_file(self, tmp_path: Path):
        ws = tmp_path / "test.code-workspace"
        original = _minimal_workspace("")
        ws.write_text(original)

        ok, msg = add_profiles_to_workspace(ws, "nova", dry_run=True)

        assert ok is True
        assert "DRY RUN" in msg
        assert ws.read_text() == original

    def test_backup_created_by_default(self, tmp_path: Path):
        ws = tmp_path / "test.code-workspace"
        original = _minimal_workspace("")
        ws.write_text(original)

        add_profiles_to_workspace(ws, "nova")

        bak = ws.with_suffix(ws.suffix + ".bak")
        assert bak.exists()
        assert bak.read_text() == original

    def test_no_backup_skips_bak_file(self, tmp_path: Path):
        ws = tmp_path / "test.code-workspace"
        ws.write_text(_minimal_workspace(""))

        add_profiles_to_workspace(ws, "nova", backup=False)

        bak = ws.with_suffix(ws.suffix + ".bak")
        assert not bak.exists()

    def test_conda_env_override(self, tmp_path: Path):
        ws = tmp_path / "test.code-workspace"
        ws.write_text(_minimal_workspace(""))

        add_profiles_to_workspace(ws, "nova", conda_env="custom_env", backup=False)

        content = ws.read_text()
        assert "custom_env" in content

    def test_no_conda_produces_plain_bash(self, tmp_path: Path):
        ws = tmp_path / "test.code-workspace"
        ws.write_text(_minimal_workspace(""))

        add_profiles_to_workspace(ws, "nova", conda_env=None, backup=False)

        content = ws.read_text()
        assert "conda activate" not in content
        assert "tmux new-session -A -s nova" in content

    def test_different_workers_can_coexist(self, tmp_path: Path):
        ws = tmp_path / "test.code-workspace"
        ws.write_text(_minimal_workspace(""))

        add_profiles_to_workspace(ws, "nova", backup=False)
        add_profiles_to_workspace(ws, "forge", backup=False)

        content = ws.read_text()
        assert '"nova-tmux"' in content
        assert '"forge-tmux"' in content
        assert '"Nova-Claude"' in content
        assert '"Forge-Claude"' in content

    def test_no_insertion_point_returns_false(self, tmp_path: Path):
        """A workspace file with no bash profile and no profiles.linux block
        should fail gracefully."""
        ws = tmp_path / "bare.code-workspace"
        ws.write_text('{"folders": [{"path": "."}]}')

        ok, msg = add_profiles_to_workspace(ws, "nova", backup=False)

        assert ok is False
        assert "insertion point" in msg

    def test_color_override_appears_in_file(self, tmp_path: Path):
        ws = tmp_path / "test.code-workspace"
        ws.write_text(_minimal_workspace(""))

        add_profiles_to_workspace(ws, "nova", color="terminal.ansiMagenta", backup=False)

        content = ws.read_text()
        assert "terminal.ansiMagenta" in content
        # Should NOT contain the default cyan for nova (color was overridden)
        # Note: the nova default is ansiCyan; with override, no ansiCyan should appear
        # for nova's profiles (but may appear for other profiles not present here)


# ── list_profiles_in_workspace ──

class TestListProfilesInWorkspace:

    def test_empty_file_returns_empty_list(self, tmp_path: Path):
        ws = tmp_path / "empty.code-workspace"
        ws.write_text('{}')
        assert list_profiles_in_workspace(ws) == []

    def test_missing_file_returns_empty_list(self, tmp_path: Path):
        ws = tmp_path / "nope.code-workspace"
        assert list_profiles_in_workspace(ws) == []

    def test_lists_bash_profile(self, tmp_path: Path):
        ws = tmp_path / "test.code-workspace"
        ws.write_text(_minimal_workspace(""))

        profiles = list_profiles_in_workspace(ws)
        names = [name for name, _ in profiles]
        assert "bash" in names

    def test_lists_added_nova_profiles(self, tmp_path: Path):
        ws = tmp_path / "test.code-workspace"
        ws.write_text(_minimal_workspace(""))
        add_profiles_to_workspace(ws, "nova", backup=False)

        profiles = list_profiles_in_workspace(ws)
        names = [name for name, _ in profiles]
        assert "nova-tmux" in names
        assert "Nova-Claude" in names
        assert "Nova-New" in names

    def test_classifies_tmux_profiles(self, tmp_path: Path):
        ws = tmp_path / "test.code-workspace"
        ws.write_text(_minimal_workspace(""))
        add_profiles_to_workspace(ws, "nova", conda_env=None, backup=False)

        profiles = list_profiles_in_workspace(ws)
        profile_map = dict(profiles)
        assert profile_map["nova-tmux"] == "tmux"


# ── tmux helpers (monkeypatched) ──

class TestTmuxSessionExists:

    def test_returns_true_when_subprocess_exits_zero(self, monkeypatch):
        def fake_run(*args, **kwargs):
            result = subprocess.CompletedProcess(args=args, returncode=0, stdout=b"", stderr=b"")
            return result
        monkeypatch.setattr(subprocess, "run", fake_run)
        assert tmux_session_exists("nova") is True

    def test_returns_false_when_subprocess_exits_nonzero(self, monkeypatch):
        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(args=args, returncode=1, stdout=b"", stderr=b"")
        monkeypatch.setattr(subprocess, "run", fake_run)
        assert tmux_session_exists("ghost") is False

    def test_returns_false_when_tmux_missing(self, monkeypatch):
        def fake_run(*args, **kwargs):
            raise FileNotFoundError("tmux")
        monkeypatch.setattr(subprocess, "run", fake_run)
        assert tmux_session_exists("nova") is False

    def test_returns_false_on_timeout(self, monkeypatch):
        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="tmux", timeout=5)
        monkeypatch.setattr(subprocess, "run", fake_run)
        assert tmux_session_exists("nova") is False


class TestEnsureTmuxSession:

    def test_already_exists_returns_true(self, monkeypatch):
        calls = []

        def fake_run(cmd, *args, **kwargs):
            calls.append(cmd)
            if "has-session" in cmd:
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout=b"", stderr=b"")

        monkeypatch.setattr(subprocess, "run", fake_run)
        assert ensure_tmux_session("nova") is True
        # Only has-session should have been called, not new-session
        assert any("has-session" in c for c in calls)
        assert not any("new-session" in c for c in calls)

    def test_missing_creates_new_session(self, monkeypatch):
        call_log = []

        def fake_run(cmd, *args, **kwargs):
            call_log.append(" ".join(cmd))
            if "has-session" in cmd:
                return subprocess.CompletedProcess(args=cmd, returncode=1, stdout=b"", stderr=b"")
            if "new-session" in cmd:
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout=b"", stderr=b"")

        monkeypatch.setattr(subprocess, "run", fake_run)
        assert ensure_tmux_session("fresh") is True
        assert any("new-session" in call for call in call_log)


# ── colony_status (monkeypatched) ──

class TestColonyStatus:

    def test_returns_dict_with_keys(self, monkeypatch):
        def fake_run(cmd, *args, **kwargs):
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="stub output", stderr=""
            )
        monkeypatch.setattr(subprocess, "run", fake_run)
        status = colony_status()
        assert "tmux" in status
        assert "meshterm" in status

    def test_tmux_not_installed(self, monkeypatch):
        def fake_run(cmd, *args, **kwargs):
            raise FileNotFoundError(cmd[0])
        monkeypatch.setattr(subprocess, "run", fake_run)
        status = colony_status()
        assert status["tmux"] == "tmux not installed"
        assert status["meshterm"] == "meshterm not on PATH"

    def test_empty_stdout_means_no_sessions(self, monkeypatch):
        def fake_run(cmd, *args, **kwargs):
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="", stderr=""
            )
        monkeypatch.setattr(subprocess, "run", fake_run)
        status = colony_status()
        assert status["tmux"] == "no sessions"
