"""Tests for changelog.printer module functionality."""

import sys
from io import StringIO
from unittest.mock import patch
from hypothesis import given, strategies as st

from src.changelog.printer import (
    ColoredOutput,
    ChangelogPrinter,
    format_change_entry,
)


class TestColoredOutput:
    """Test ColoredOutput class functionality."""

    def test_color_constants(self):
        """Test that color constants are defined."""
        assert ColoredOutput.RED == "\033[91m"
        assert ColoredOutput.GREEN == "\033[92m"
        assert ColoredOutput.YELLOW == "\033[93m"
        assert ColoredOutput.BLUE == "\033[94m"
        assert ColoredOutput.MAGENTA == "\033[95m"
        assert ColoredOutput.CYAN == "\033[96m"
        assert ColoredOutput.WHITE == "\033[97m"
        assert ColoredOutput.GREY == "\033[90m"
        assert ColoredOutput.BOLD == "\033[1m"
        assert ColoredOutput.DIM == "\033[2m"
        assert ColoredOutput.UNDERLINE == "\033[4m"
        assert ColoredOutput.RESET == "\033[0m"

    def test_is_tty_with_tty(self):
        """Test is_tty detection with TTY."""
        with patch("sys.stdout.isatty", return_value=True):
            assert ColoredOutput.is_tty() is True

    def test_is_tty_without_tty(self):
        """Test is_tty detection without TTY."""
        with patch("sys.stdout.isatty", return_value=False):
            assert ColoredOutput.is_tty() is False

    def test_colorize_with_tty(self):
        """Test colorizing text when TTY is available."""
        with patch.object(ColoredOutput, "is_tty", return_value=True):
            result = ColoredOutput.colorize("test text", ColoredOutput.RED)
            expected = f"{ColoredOutput.RED}test text{ColoredOutput.RESET}"
            assert result == expected

    def test_colorize_without_tty(self):
        """Test colorizing text when TTY is not available."""
        with patch.object(ColoredOutput, "is_tty", return_value=False):
            result = ColoredOutput.colorize("test text", ColoredOutput.RED)
            assert result == "test text"

    def test_colorize_empty_text(self):
        """Test colorizing empty text."""
        with patch.object(ColoredOutput, "is_tty", return_value=True):
            result = ColoredOutput.colorize("", ColoredOutput.GREEN)
            expected = f"{ColoredOutput.GREEN}{ColoredOutput.RESET}"
            assert result == expected


class TestChangelogPrinter:
    """Test ChangelogPrinter class functionality."""

    def test_init_default_colors(self):
        """Test initialization with default color settings."""
        with patch.object(ColoredOutput, "is_tty", return_value=True):
            printer = ChangelogPrinter()
            assert printer.use_colors is True

        with patch.object(ColoredOutput, "is_tty", return_value=False):
            printer = ChangelogPrinter()
            assert printer.use_colors is False

    def test_init_explicit_colors(self):
        """Test initialization with explicit color settings."""
        printer = ChangelogPrinter(use_colors=True)
        assert printer.use_colors is True

        printer = ChangelogPrinter(use_colors=False)
        assert printer.use_colors is False

    def test_print_changelog_entries_empty(self, capsys):
        """Test printing empty changelog entries."""
        printer = ChangelogPrinter(use_colors=False)

        printer.print_changelog_entries([])

        captured = capsys.readouterr()
        assert "No changelog entries to display" in captured.out

    def test_print_changelog_entries_with_entries(self, capsys):
        """Test printing changelog entries with content."""
        printer = ChangelogPrinter(use_colors=False)
        entries = [
            "Jan 15 10:30:45.123 CREATE 123",
            "Jan 15 10:31:00.456 MODIFY 124 amount: 100.00 -> 150.00",
        ]

        with patch.object(
            printer, "format_change_entry", side_effect=lambda x: f"formatted: {x}"
        ):
            printer.print_changelog_entries(entries)

            captured = capsys.readouterr()
            assert "formatted: Jan 15 10:30:45.123 CREATE 123" in captured.out
            assert (
                "formatted: Jan 15 10:31:00.456 MODIFY 124 amount: 100.00 -> 150.00"
                in captured.out
            )

    def test_format_change_entry_empty(self):
        """Test formatting empty changelog entry."""
        printer = ChangelogPrinter(use_colors=False)

        result = printer.format_change_entry("")
        assert result == ""

        result = printer.format_change_entry("   ")
        assert result == ""

    def test_format_change_entry_create_without_colors(self):
        """Test formatting CREATE entry without colors."""
        printer = ChangelogPrinter(use_colors=False)
        entry = "Jan 15 10:30:45.123 CREATE 123"

        result = printer.format_change_entry(entry)

        assert "Jan 15 10:30:45.123" in result
        assert "CREATE" in result
        assert "123" in result
        # Should not contain ANSI color codes
        assert "\033[" not in result

    def test_format_change_entry_create_with_colors(self):
        """Test formatting CREATE entry with colors."""
        with patch.object(ColoredOutput, "is_tty", return_value=True):
            printer = ChangelogPrinter(use_colors=True)
            entry = "Jan 15 10:30:45.123 CREATE 123"

            result = printer.format_change_entry(entry)

            # Should contain ANSI color codes
            assert "\033[" in result
            assert ColoredOutput.GREEN in result or ColoredOutput.BOLD in result
            assert ColoredOutput.RESET in result

    def test_format_change_entry_delete_without_colors(self):
        """Test formatting DELETE entry without colors."""
        printer = ChangelogPrinter(use_colors=False)
        entry = "Jan 15 10:30:45.123 DELETE 123"

        result = printer.format_change_entry(entry)

        assert "DELETE" in result
        assert "123" in result
        assert "\033[" not in result

    def test_format_change_entry_delete_with_colors(self):
        """Test formatting DELETE entry with colors."""
        with patch.object(ColoredOutput, "is_tty", return_value=True):
            printer = ChangelogPrinter(use_colors=True)
            entry = "Jan 15 10:30:45.123 DELETE 123"

            result = printer.format_change_entry(entry)

            assert "\033[" in result
            assert ColoredOutput.RED in result or ColoredOutput.BOLD in result

    def test_format_change_entry_modify_without_colors(self):
        """Test formatting MODIFY entry without colors."""
        printer = ChangelogPrinter(use_colors=False)
        entry = (
            "Jan 15 10:30:45.123 MODIFY 123 amount: 100.00 -> 150.00, payee: Old -> New"
        )

        result = printer.format_change_entry(entry)

        assert "MODIFY" in result
        assert "123" in result
        assert "amount: 100.00 -> 150.00" in result
        assert "payee: Old -> New" in result
        assert "\033[" not in result

    def test_format_change_entry_modify_with_colors(self):
        """Test formatting MODIFY entry with colors."""
        with patch.object(ColoredOutput, "is_tty", return_value=True):
            printer = ChangelogPrinter(use_colors=True)
            entry = "Jan 15 10:30:45.123 MODIFY 123 amount: 100.00 -> 150.00"

            result = printer.format_change_entry(entry)

            assert "\033[" in result
            # Should contain colors for operation, transaction ID, and field changes
            assert ColoredOutput.YELLOW in result or ColoredOutput.BOLD in result

    def test_format_change_entry_malformed(self):
        """Test formatting malformed changelog entry."""
        printer = ChangelogPrinter(use_colors=False)
        entry = "malformed entry"

        result = printer.format_change_entry(entry)

        # Should return original entry if format is unexpected
        assert result == entry

    def test_colorize_operation_create(self):
        """Test colorizing CREATE operation."""
        with patch.object(ColoredOutput, "is_tty", return_value=True):
            printer = ChangelogPrinter(use_colors=True)

            result = printer._colorize_operation("CREATE")

            assert ColoredOutput.GREEN in result
            assert ColoredOutput.BOLD in result
            assert "CREATE" in result

    def test_colorize_operation_delete(self):
        """Test colorizing DELETE operation."""
        with patch.object(ColoredOutput, "is_tty", return_value=True):
            printer = ChangelogPrinter(use_colors=True)

            result = printer._colorize_operation("DELETE")

            assert ColoredOutput.RED in result
            assert ColoredOutput.BOLD in result
            assert "DELETE" in result

    def test_colorize_operation_modify(self):
        """Test colorizing MODIFY operation."""
        with patch.object(ColoredOutput, "is_tty", return_value=True):
            printer = ChangelogPrinter(use_colors=True)

            result = printer._colorize_operation("MODIFY")

            assert ColoredOutput.YELLOW in result
            assert ColoredOutput.BOLD in result
            assert "MODIFY" in result

    def test_colorize_operation_unknown(self):
        """Test colorizing unknown operation."""
        with patch.object(ColoredOutput, "is_tty", return_value=True):
            printer = ChangelogPrinter(use_colors=True)

            result = printer._colorize_operation("UNKNOWN")

            assert ColoredOutput.BLUE in result
            assert ColoredOutput.BOLD in result
            assert "UNKNOWN" in result

    def test_colorize_operation_without_colors(self):
        """Test colorizing operation without colors."""
        printer = ChangelogPrinter(use_colors=False)

        result = printer._colorize_operation("CREATE")

        assert result == "CREATE"
        assert "\033[" not in result

    def test_colorize_field_changes_without_colors(self):
        """Test colorizing field changes without colors."""
        printer = ChangelogPrinter(use_colors=False)
        changes_str = "amount: 100.00 -> 150.00, payee: Old -> New"

        result = printer._colorize_field_changes(changes_str)

        assert result == changes_str
        assert "\033[" not in result

    def test_colorize_field_changes_with_colors(self):
        """Test colorizing field changes with colors."""
        with patch.object(ColoredOutput, "is_tty", return_value=True):
            printer = ChangelogPrinter(use_colors=True)
            changes_str = "amount: 100.00 -> 150.00"

            result = printer._colorize_field_changes(changes_str)

            assert "\033[" in result
            assert ColoredOutput.CYAN in result  # Field name
            assert ColoredOutput.RED in result  # Old value
            assert ColoredOutput.GREEN in result  # New value
            assert ColoredOutput.GREY in result  # Arrow

    def test_colorize_field_changes_multiple_fields(self):
        """Test colorizing multiple field changes."""
        with patch.object(ColoredOutput, "is_tty", return_value=True):
            printer = ChangelogPrinter(use_colors=True)
            changes_str = (
                "amount: 100.00 -> 150.00, payee: Old Merchant -> New Merchant"
            )

            result = printer._colorize_field_changes(changes_str)

            # Should color both field changes
            assert result.count(ColoredOutput.CYAN) >= 2  # Field names
            assert result.count(ColoredOutput.RED) >= 2  # Old values
            assert result.count(ColoredOutput.GREEN) >= 2  # New values

    def test_print_summary_empty(self, capsys):
        """Test printing empty summary."""
        printer = ChangelogPrinter(use_colors=False)

        printer.print_summary({})

        captured = capsys.readouterr()
        # Should not print anything for empty stats
        assert captured.out == ""

    def test_print_summary_with_stats_without_colors(self, capsys):
        """Test printing summary with stats without colors."""
        printer = ChangelogPrinter(use_colors=False)
        stats = {"total": 10, "CREATE": 5, "MODIFY": 3, "DELETE": 2}

        printer.print_summary(stats)

        captured = capsys.readouterr()
        assert "Changelog Summary:" in captured.out
        assert "Total entries: 10" in captured.out
        assert "Created: 5" in captured.out
        assert "Modified: 3" in captured.out
        assert "Deleted: 2" in captured.out
        assert "\033[" not in captured.out

    def test_print_summary_with_stats_with_colors(self, capsys):
        """Test printing summary with stats with colors."""
        with patch.object(ColoredOutput, "is_tty", return_value=True):
            printer = ChangelogPrinter(use_colors=True)
            stats = {"total": 10, "CREATE": 5, "MODIFY": 3, "DELETE": 2}

            printer.print_summary(stats)

            captured = capsys.readouterr()
            assert "Changelog Summary:" in captured.out
            # Should contain color codes
            assert "\033[" in captured.out


class TestFormatChangeEntry:
    """Test format_change_entry convenience function."""

    def test_format_change_entry_default_colors(self):
        """Test format_change_entry with default color settings."""
        entry = "Jan 15 10:30:45.123 CREATE 123"

        with patch.object(ColoredOutput, "is_tty", return_value=False):
            result = format_change_entry(entry)
            assert "CREATE" in result
            assert "\033[" not in result

    def test_format_change_entry_explicit_colors(self):
        """Test format_change_entry with explicit color settings."""
        with patch.object(ColoredOutput, "is_tty", return_value=True):
            entry = "Jan 15 10:30:45.123 CREATE 123"

            result = format_change_entry(entry, use_colors=True)
            assert "CREATE" in result
            assert "\033[" in result
        assert "\033[" in result

        result = format_change_entry(entry, use_colors=False)
        assert "CREATE" in result
        assert "\033[" not in result

    def test_format_change_entry_none_colors(self):
        """Test format_change_entry with None color setting."""
        entry = "Jan 15 10:30:45.123 CREATE 123"

        with patch.object(ColoredOutput, "is_tty", return_value=True):
            result = format_change_entry(entry, use_colors=None)
            assert "CREATE" in result
            # Should use TTY detection when None


class TestPropertyBasedTests:
    """Property-based tests for printer functionality."""

    @given(st.text(min_size=0, max_size=200))
    def test_colorize_text_properties(self, text):
        """Property test: colorizing should handle any text."""
        # With TTY
        with patch.object(ColoredOutput, "is_tty", return_value=True):
            result = ColoredOutput.colorize(text, ColoredOutput.RED)
            assert text in result
            assert ColoredOutput.RED in result
            assert ColoredOutput.RESET in result

        # Without TTY
        with patch.object(ColoredOutput, "is_tty", return_value=False):
            result = ColoredOutput.colorize(text, ColoredOutput.RED)
            assert result == text

    @given(st.text(min_size=0, max_size=500))
    def test_format_change_entry_properties(self, entry_text):
        """Property test: formatting should handle any entry text."""
        printer = ChangelogPrinter(use_colors=False)

        # Should not raise exception
        result = printer.format_change_entry(entry_text)
        assert isinstance(result, str)

    @given(
        st.one_of(
            st.just("CREATE"),
            st.just("DELETE"),
            st.just("MODIFY"),
            st.text(min_size=1, max_size=20),
        )
    )
    def test_colorize_operation_properties(self, operation):
        """Property test: operation colorizing should handle any operation."""
        with patch.object(ColoredOutput, "is_tty", return_value=True):
            printer = ChangelogPrinter(use_colors=True)

            result = printer._colorize_operation(operation)
            assert operation in result
            assert ColoredOutput.BOLD in result
            assert ColoredOutput.RESET in result

    @given(
        st.dictionaries(
            keys=st.sampled_from(["total", "CREATE", "MODIFY", "DELETE"]),
            values=st.integers(min_value=0, max_value=1000),
            min_size=0,
        )
    )
    def test_print_summary_properties(self, test_stats):
        """Property test: printing summary should handle any stats."""

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        try:
            printer = ChangelogPrinter(use_colors=False)
            # Should not raise exception
            printer.print_summary(test_stats)

            output = captured_output.getvalue()
            if test_stats:  # Non-empty stats
                assert "Changelog Summary:" in output
        finally:
            sys.stdout = sys.__stdout__

    @given(st.lists(st.text(min_size=0, max_size=100), min_size=0, max_size=20))
    def test_print_changelog_entries_properties(self, test_entries):
        """Property test: printing entries should handle any entry list."""

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        try:
            printer = ChangelogPrinter(use_colors=False)
            # Should not raise exception
            printer.print_changelog_entries(test_entries)

            output = captured_output.getvalue()
            if not test_entries:
                assert "No changelog entries to display" in output
        finally:
            sys.stdout = sys.__stdout__
