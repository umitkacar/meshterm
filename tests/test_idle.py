"""Unit tests for meshterm.idle — IdleChecker, IdleState, IdleResult."""

import time

from meshterm.idle import (
    IdleChecker,
    IdleCheckerConfig,
    IdleResult,
    IdleState,
)


# ── IdleState ──

class TestIdleState:

    def test_values(self):
        assert IdleState.IDLE.value == "IDLE"
        assert IdleState.BUSY.value == "BUSY"
        assert IdleState.UNKNOWN.value == "UNKNOWN"

    def test_members(self):
        assert len(IdleState) == 3


# ── IdleResult ──

class TestIdleResult:

    def test_defaults(self):
        r = IdleResult(state=IdleState.UNKNOWN)
        assert r.idle_seconds == 0.0
        assert r.screen_hash == ""
        assert r.prompt_matched is False
        assert r.consecutive_stable_polls == 0

    def test_all_fields(self):
        r = IdleResult(
            state=IdleState.IDLE,
            idle_seconds=42.0,
            screen_hash="abc123",
            prompt_matched=True,
            consecutive_stable_polls=5,
        )
        assert r.state == IdleState.IDLE
        assert r.idle_seconds == 42.0
        assert r.screen_hash == "abc123"


# ── IdleCheckerConfig ──

class TestIdleCheckerConfig:

    def test_defaults(self):
        cfg = IdleCheckerConfig()
        assert cfg.idle_timeout == 900.0
        assert cfg.min_stable_polls == 3
        assert len(cfg.prompt_patterns) == 4

    def test_custom_config(self):
        cfg = IdleCheckerConfig(
            prompt_patterns=[r">>> $"],
            idle_timeout=60.0,
            min_stable_polls=2,
        )
        assert cfg.idle_timeout == 60.0
        assert cfg.min_stable_polls == 2
        assert len(cfg.prompt_patterns) == 1


# ── IdleChecker.screen_hash ──

class TestScreenHash:

    def test_deterministic(self):
        lines = ["hello", "world"]
        h1 = IdleChecker.screen_hash(lines)
        h2 = IdleChecker.screen_hash(lines)
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = IdleChecker.screen_hash(["hello"])
        h2 = IdleChecker.screen_hash(["world"])
        assert h1 != h2

    def test_empty_lines(self):
        h = IdleChecker.screen_hash([])
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex digest length

    def test_whitespace_matters(self):
        h1 = IdleChecker.screen_hash(["hello "])
        h2 = IdleChecker.screen_hash(["hello"])
        assert h1 != h2

    def test_line_order_matters(self):
        h1 = IdleChecker.screen_hash(["a", "b"])
        h2 = IdleChecker.screen_hash(["b", "a"])
        assert h1 != h2

    def test_sha256_format(self):
        h = IdleChecker.screen_hash(["test"])
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ── IdleChecker.detect_prompt ──

class TestDetectPrompt:

    def setup_method(self):
        self.checker = IdleChecker()

    def test_dollar_prompt(self):
        assert self.checker.detect_prompt(["user@host:~$ "])

    def test_hash_prompt(self):
        assert self.checker.detect_prompt(["root@host:~# "])

    def test_arrow_prompt(self):
        assert self.checker.detect_prompt(["❯ "])

    def test_python_repl(self):
        assert self.checker.detect_prompt([">>> "])

    def test_ipython_prompt(self):
        assert self.checker.detect_prompt(["In [1]: "])

    def test_no_prompt(self):
        assert not self.checker.detect_prompt(["running some process..."])

    def test_empty_screen(self):
        # All empty lines — the empty pattern should match
        result = self.checker.detect_prompt(["", "", ""])
        assert result is True

    def test_prompt_on_last_nonempty_line(self):
        # Prompt is on a non-last line, but it's the last non-empty one
        lines = ["some output", "user@host:~$ ", "", ""]
        assert self.checker.detect_prompt(lines)

    def test_busy_output_above_prompt_ignored(self):
        lines = ["compiling...", "linking...", "user@host:~$ "]
        assert self.checker.detect_prompt(lines)

    def test_custom_patterns(self):
        cfg = IdleCheckerConfig(prompt_patterns=[r"mysh>"])
        checker = IdleChecker(config=cfg)
        assert checker.detect_prompt(["mysh>"])
        assert not checker.detect_prompt(["$ "])

    def test_gt_prompt(self):
        assert self.checker.detect_prompt(["some-app> "])


# ── IdleChecker.check — state machine ──

class TestCheckStateMachine:

    def test_first_check_is_unknown(self):
        checker = IdleChecker()
        r = checker.check(["$ "])
        assert r.state == IdleState.UNKNOWN

    def test_second_same_screen_not_yet_idle(self):
        """Need min_stable_polls (default=3) before IDLE."""
        checker = IdleChecker()
        checker.check(["$ "])  # baseline
        r = checker.check(["$ "])  # poll 1 stable
        # Only 1 stable poll, need 3
        assert r.state == IdleState.BUSY
        assert r.consecutive_stable_polls == 1

    def test_becomes_idle_after_min_polls(self):
        cfg = IdleCheckerConfig(min_stable_polls=3)
        checker = IdleChecker(config=cfg)
        lines = ["user@host:~$ "]

        checker.check(lines)  # baseline (UNKNOWN)
        checker.check(lines)  # stable 1
        checker.check(lines)  # stable 2
        r = checker.check(lines)  # stable 3 → IDLE!
        assert r.state == IdleState.IDLE
        assert r.prompt_matched is True
        assert r.consecutive_stable_polls == 3

    def test_becomes_idle_min_polls_2(self):
        cfg = IdleCheckerConfig(min_stable_polls=2)
        checker = IdleChecker(config=cfg)
        lines = ["$ "]

        checker.check(lines)  # baseline
        checker.check(lines)  # stable 1
        r = checker.check(lines)  # stable 2 → IDLE
        assert r.state == IdleState.IDLE

    def test_screen_change_resets_to_busy(self):
        cfg = IdleCheckerConfig(min_stable_polls=2)
        checker = IdleChecker(config=cfg)

        # Become idle
        for _ in range(4):
            checker.check(["$ "])
        assert checker.check(["$ "]).state == IdleState.IDLE

        # Screen changes → immediate BUSY
        r = checker.check(["$ ls\nfile1  file2"])
        assert r.state == IdleState.BUSY
        assert r.consecutive_stable_polls == 0

    def test_no_prompt_stays_busy(self):
        """Screen stable but no prompt → still BUSY."""
        cfg = IdleCheckerConfig(min_stable_polls=2)
        checker = IdleChecker(config=cfg)
        lines = ["running long process..."]

        checker.check(lines)
        for _ in range(5):
            r = checker.check(lines)
        assert r.state == IdleState.BUSY

    def test_idle_seconds_increase(self):
        cfg = IdleCheckerConfig(min_stable_polls=1)
        checker = IdleChecker(config=cfg)
        lines = ["$ "]

        checker.check(lines)  # baseline
        checker.check(lines)  # stable 1 → IDLE, starts timer

        time.sleep(0.05)
        r = checker.check(lines)
        assert r.state == IdleState.IDLE
        assert r.idle_seconds >= 0.04  # some time passed

    def test_screen_hash_in_result(self):
        checker = IdleChecker()
        lines = ["hello"]
        r = checker.check(lines)
        expected = IdleChecker.screen_hash(lines)
        assert r.screen_hash == expected

    def test_busy_has_zero_idle_seconds(self):
        checker = IdleChecker()
        checker.check(["$ "])  # baseline
        r = checker.check(["different"])  # changed screen
        assert r.idle_seconds == 0.0

    def test_reset_returns_to_unknown(self):
        cfg = IdleCheckerConfig(min_stable_polls=1)
        checker = IdleChecker(config=cfg)
        lines = ["$ "]

        checker.check(lines)
        checker.check(lines)  # IDLE

        checker.reset()
        r = checker.check(lines)
        assert r.state == IdleState.UNKNOWN


# ── IdleChecker.is_timed_out ──

class TestIsTimedOut:

    def test_not_timed_out_when_busy(self):
        checker = IdleChecker()
        checker.check(["some output"])
        assert checker.is_timed_out() is False

    def test_not_timed_out_before_threshold(self):
        cfg = IdleCheckerConfig(idle_timeout=1000.0, min_stable_polls=1)
        checker = IdleChecker(config=cfg)
        lines = ["$ "]
        checker.check(lines)
        checker.check(lines)  # IDLE starts
        assert checker.is_timed_out() is False

    def test_timed_out_after_threshold(self):
        cfg = IdleCheckerConfig(idle_timeout=0.01, min_stable_polls=1)
        checker = IdleChecker(config=cfg)
        lines = ["$ "]
        checker.check(lines)
        checker.check(lines)  # IDLE starts
        time.sleep(0.02)
        assert checker.is_timed_out() is True

    def test_timeout_resets_on_busy(self):
        cfg = IdleCheckerConfig(idle_timeout=0.01, min_stable_polls=1)
        checker = IdleChecker(config=cfg)
        lines = ["$ "]

        checker.check(lines)
        checker.check(lines)
        time.sleep(0.02)
        assert checker.is_timed_out() is True

        # Screen changes → no longer timed out
        checker.check(["busy output"])
        assert checker.is_timed_out() is False


# ── IdleChecker.reset ──

class TestReset:

    def test_reset_clears_all_state(self):
        cfg = IdleCheckerConfig(min_stable_polls=1)
        checker = IdleChecker(config=cfg)
        lines = ["$ "]

        checker.check(lines)
        checker.check(lines)
        assert checker.idle_seconds > 0 or checker.consecutive_stable_polls > 0

        checker.reset()
        assert checker.idle_seconds == 0.0
        assert checker.consecutive_stable_polls == 0

    def test_reset_makes_next_check_unknown(self):
        checker = IdleChecker()
        checker.check(["$ "])
        checker.reset()
        r = checker.check(["$ "])
        assert r.state == IdleState.UNKNOWN


# ── IdleChecker properties ──

class TestProperties:

    def test_config_property(self):
        cfg = IdleCheckerConfig(idle_timeout=42.0)
        checker = IdleChecker(config=cfg)
        assert checker.config.idle_timeout == 42.0

    def test_idle_seconds_zero_initially(self):
        checker = IdleChecker()
        assert checker.idle_seconds == 0.0

    def test_consecutive_stable_polls_tracks(self):
        checker = IdleChecker()
        lines = ["$ "]
        checker.check(lines)
        assert checker.consecutive_stable_polls == 0
        checker.check(lines)
        assert checker.consecutive_stable_polls == 1
        checker.check(lines)
        assert checker.consecutive_stable_polls == 2


# ── Edge cases ──

class TestEdgeCases:

    def test_unicode_content(self):
        checker = IdleChecker()
        lines = ["🚀 deploy complete", "user@host:~$ "]
        r = checker.check(lines)
        assert r.state == IdleState.UNKNOWN  # first check
        assert r.screen_hash  # hash should work with unicode

    def test_very_long_lines(self):
        checker = IdleChecker()
        lines = ["x" * 10000, "$ "]
        r = checker.check(lines)
        assert isinstance(r.screen_hash, str)

    def test_many_empty_lines(self):
        checker = IdleChecker()
        lines = [""] * 100
        r = checker.check(lines)
        assert r.state == IdleState.UNKNOWN

    def test_single_empty_screen(self):
        checker = IdleChecker()
        r = checker.check([])
        assert r.state == IdleState.UNKNOWN
        assert len(r.screen_hash) == 64

    def test_alternating_screens(self):
        """Rapidly alternating content → always BUSY."""
        checker = IdleChecker()
        checker.check(["screen A"])  # baseline
        for i in range(10):
            lines = [f"screen {'A' if i % 2 == 0 else 'B'}"]
            r = checker.check(lines)
        # Should never reach IDLE with alternating content
        assert r.state == IdleState.BUSY

    def test_prompt_after_output_burst(self):
        """Simulates command finishing: output → prompt appears → idle."""
        cfg = IdleCheckerConfig(min_stable_polls=2)
        checker = IdleChecker(config=cfg)

        # Running command
        checker.check(["compiling..."])
        checker.check(["compiling...\nlinking..."])
        checker.check(["done!\nuser@host:~$ "])

        # Now prompt is visible and stable
        r = checker.check(["done!\nuser@host:~$ "])  # stable 1
        assert r.state == IdleState.BUSY  # need 2

        r = checker.check(["done!\nuser@host:~$ "])  # stable 2 → IDLE
        assert r.state == IdleState.IDLE
