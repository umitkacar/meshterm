"""Unit tests for meshterm.session dataclasses and helpers."""

from meshterm.session import ScreenLine, ScreenContents


# ── ScreenLine ──

class TestScreenLine:

    def test_create_default(self):
        line = ScreenLine(string="hello")
        assert line.string == "hello"
        assert line.hard_eol is True
        assert line.line_number == 0

    def test_create_with_all_fields(self):
        line = ScreenLine(string="world", hard_eol=False, line_number=5)
        assert line.string == "world"
        assert line.hard_eol is False
        assert line.line_number == 5

    def test_str_returns_string_field(self):
        line = ScreenLine(string="$ ls -la")
        assert str(line) == "$ ls -la"

    def test_empty_string(self):
        line = ScreenLine(string="")
        assert line.string == ""
        assert str(line) == ""


# ── ScreenContents ──

class TestScreenContents:

    def test_create_empty(self):
        sc = ScreenContents()
        assert sc.lines == []
        assert sc.cursor_row == 0
        assert sc.cursor_col == 0
        assert sc.rows == 24
        assert sc.cols == 80
        assert sc.alternate_screen_active is False

    def test_number_of_lines(self):
        lines = [ScreenLine(string=f"line {i}", line_number=i) for i in range(5)]
        sc = ScreenContents(lines=lines)
        assert sc.number_of_lines == 5

    def test_number_of_lines_empty(self):
        sc = ScreenContents()
        assert sc.number_of_lines == 0

    def test_line_access_valid_index(self):
        lines = [
            ScreenLine(string="first", line_number=0),
            ScreenLine(string="second", line_number=1),
        ]
        sc = ScreenContents(lines=lines)
        assert sc.line(0).string == "first"
        assert sc.line(1).string == "second"

    def test_line_access_out_of_range(self):
        sc = ScreenContents(lines=[ScreenLine(string="only")])
        result = sc.line(99)
        assert result.string == ""
        assert result.line_number == 99

    def test_line_access_negative_index_returns_empty(self):
        sc = ScreenContents(lines=[ScreenLine(string="x")])
        result = sc.line(-1)
        # Negative index is < 0, so the guard `0 <= index` fails
        assert result.string == ""

    def test_text_property(self):
        lines = [
            ScreenLine(string="hello"),
            ScreenLine(string="world"),
        ]
        sc = ScreenContents(lines=lines)
        assert sc.text == "hello\nworld"

    def test_text_property_empty(self):
        sc = ScreenContents()
        assert sc.text == ""

    def test_custom_dimensions(self):
        sc = ScreenContents(rows=50, cols=120)
        assert sc.rows == 50
        assert sc.cols == 120

    def test_alternate_screen_flag(self):
        sc = ScreenContents(alternate_screen_active=True)
        assert sc.alternate_screen_active is True
