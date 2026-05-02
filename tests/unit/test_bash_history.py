"""Unit tests for meshterm.bash_history — shell history reader."""

from __future__ import annotations

from pathlib import Path

import pytest

from meshterm.bash_history import BashHistory


@pytest.fixture
def sample_history(tmp_path: Path) -> Path:
    p = tmp_path / ".bash_history"
    p.write_text(
        "\n".join(
            [
                "ls -la",
                "cd /tmp",
                "echo hello",
                "echo world",
                "git status",
                "git log",
                "git status",
                "pytest tests/",
                "pytest tests/ -v",
                "vim README.md",
            ]
        )
        + "\n"
    )
    return p


class TestLoading:
    def test_load_from_path(self, sample_history: Path):
        h = BashHistory(sample_history)
        assert len(h) == 10

    def test_missing_file_empty(self, tmp_path: Path):
        h = BashHistory(tmp_path / "no-such-file")
        assert len(h) == 0

    def test_iter(self, sample_history: Path):
        h = BashHistory(sample_history)
        first = next(iter(h))
        assert first == "ls -la"

    def test_blank_lines_skipped(self, tmp_path: Path):
        p = tmp_path / ".bash_history"
        p.write_text("a\n\nb\n\n\nc\n")
        h = BashHistory(p)
        assert len(h) == 3

    def test_reload(self, sample_history: Path):
        h = BashHistory(sample_history)
        assert len(h) == 10
        sample_history.write_text("new cmd\n")
        h.reload()
        assert len(h) == 1


class TestRecent:
    def test_recent_default(self, sample_history: Path):
        h = BashHistory(sample_history)
        rec = h.recent()  # default n=20
        assert len(rec) == 10  # only 10 commands total
        assert rec[-1] == "vim README.md"

    def test_recent_n(self, sample_history: Path):
        h = BashHistory(sample_history)
        rec = h.recent(n=3)
        assert rec == ["pytest tests/ -v", "vim README.md"] or len(rec) == 3

    def test_recent_order(self, sample_history: Path):
        h = BashHistory(sample_history)
        rec = h.recent(n=3)
        # Last three commands, in order
        assert rec == ["pytest tests/", "pytest tests/ -v", "vim README.md"]


class TestSearch:
    def test_case_insensitive(self, sample_history: Path):
        h = BashHistory(sample_history)
        assert "git status" in h.search("STATUS")
        assert "git status" in h.search("status")

    def test_case_sensitive(self, sample_history: Path):
        h = BashHistory(sample_history)
        assert h.search("STATUS", case_insensitive=False) == []
        assert "git status" in h.search("status", case_insensitive=False)

    def test_substring_match(self, sample_history: Path):
        h = BashHistory(sample_history)
        matches = h.search("pytest")
        assert len(matches) == 2
        assert "pytest tests/" in matches

    def test_no_match(self, sample_history: Path):
        h = BashHistory(sample_history)
        assert h.search("doesnotexist") == []


class TestCountByCommand:
    def test_top_used(self, sample_history: Path):
        h = BashHistory(sample_history)
        top = h.count_by_command(top_n=3)
        # git appears 3x, echo 2x, pytest 2x, ls 1x, cd 1x, vim 1x
        counts = dict(top)
        assert counts["git"] == 3
        assert len(top) == 3
        # First is most-used
        assert top[0][0] == "git"

    def test_top_all(self, sample_history: Path):
        h = BashHistory(sample_history)
        top = h.count_by_command(top_n=20)
        counts = dict(top)
        assert counts["git"] == 3
        assert counts["echo"] == 2
        assert counts["pytest"] == 2
        assert counts["ls"] == 1
