"""Tests for date parsing utilities."""

import pytest
from datetime import date
from src.cli.date_parser import (
    parse_date_string,
    expand_date_range,
    get_this_month_range,
    get_last_month_range,
    get_this_year_range,
    get_last_year_range,
    DateParseError,
)


class TestParseDateString:
    """Test date string parsing functionality."""

    def test_parse_full_date_format(self):
        """Test parsing YYYY-MM-DD format."""
        result = parse_date_string("2024-03-15")
        assert result == date(2024, 3, 15)

    def test_parse_compact_date_format(self):
        """Test parsing YYYYMMDD format."""
        result = parse_date_string("20240315")
        assert result == date(2024, 3, 15)

    def test_parse_year_month_format(self):
        """Test parsing YYYY-MM format (first day of month)."""
        result = parse_date_string("2024-03")
        assert result == date(2024, 3, 1)

    def test_parse_year_format(self):
        """Test parsing YYYY format (first day of year)."""
        result = parse_date_string("2024")
        assert result == date(2024, 1, 1)

    def test_parse_invalid_date(self):
        """Test parsing invalid date raises error."""
        with pytest.raises(DateParseError, match="Invalid date"):
            parse_date_string("2024-02-30")  # February 30th doesn't exist

    def test_parse_invalid_format(self):
        """Test parsing unsupported format raises error."""
        with pytest.raises(DateParseError, match="Unsupported date format"):
            parse_date_string("March 15, 2024")

    def test_parse_empty_string(self):
        """Test parsing empty string raises error."""
        with pytest.raises(DateParseError, match="Date string cannot be empty"):
            parse_date_string("")

    def test_parse_whitespace_handling(self):
        """Test that whitespace is properly handled."""
        result = parse_date_string("  2024-03-15  ")
        assert result == date(2024, 3, 15)

    def test_parse_leap_year(self):
        """Test parsing leap year date."""
        result = parse_date_string("2024-02-29")
        assert result == date(2024, 2, 29)

    def test_parse_non_leap_year_invalid(self):
        """Test parsing Feb 29 in non-leap year fails."""
        with pytest.raises(DateParseError):
            parse_date_string("2023-02-29")


class TestExpandDateRange:
    """Test date range expansion functionality."""

    def test_expand_full_dates(self):
        """Test expanding full date range."""
        start, end = expand_date_range("2024-01-01", "2024-12-31")
        assert start == date(2024, 1, 1)
        assert end == date(2024, 12, 31)

    def test_expand_partial_end_date_month(self):
        """Test expanding with partial end date (month)."""
        start, end = expand_date_range("2024-01-01", "2024-03")
        assert start == date(2024, 1, 1)
        assert end == date(2024, 3, 31)  # Last day of March

    def test_expand_partial_end_date_year(self):
        """Test expanding with partial end date (year)."""
        start, end = expand_date_range("2024-01-01", "2024")
        assert start == date(2024, 1, 1)
        assert end == date(2024, 12, 31)  # Last day of year

    def test_expand_no_end_date(self):
        """Test expanding with no end date (defaults to today)."""
        start, end = expand_date_range("2024-01-01", None)
        assert start == date(2024, 1, 1)
        assert end == date.today()

    def test_expand_invalid_range(self):
        """Test expanding invalid range (start after end)."""
        with pytest.raises(DateParseError, match="Start date .* is after end date"):
            expand_date_range("2024-12-31", "2024-01-01")

    def test_expand_no_start_date(self):
        """Test expanding with no start date raises error."""
        with pytest.raises(DateParseError, match="Start date is required"):
            expand_date_range(None, "2024-12-31")

    def test_expand_february_leap_year(self):
        """Test expanding February in leap year."""
        start, end = expand_date_range("2024-02-01", "2024-02")
        assert start == date(2024, 2, 1)
        assert end == date(2024, 2, 29)  # Leap year February

    def test_expand_february_non_leap_year(self):
        """Test expanding February in non-leap year."""
        start, end = expand_date_range("2023-02-01", "2023-02")
        assert start == date(2023, 2, 1)
        assert end == date(2023, 2, 28)  # Non-leap year February


class TestRelativeDateRanges:
    """Test relative date range calculations."""

    def test_this_month_range(self):
        """Test this month range calculation."""
        start, end = get_this_month_range()
        today = date.today()

        assert start.year == today.year
        assert start.month == today.month
        assert start.day == 1

        assert end.year == today.year
        assert end.month == today.month
        # End should be last day of current month
        assert end.day >= 28  # All months have at least 28 days

    def test_last_month_range(self):
        """Test last month range calculation."""
        start, end = get_last_month_range()
        today = date.today()

        if today.month == 1:
            # January -> previous month is December of last year
            assert start.year == today.year - 1
            assert start.month == 12
            assert end.year == today.year - 1
            assert end.month == 12
        else:
            # Other months -> previous month of same year
            assert start.year == today.year
            assert start.month == today.month - 1
            assert end.year == today.year
            assert end.month == today.month - 1

        assert start.day == 1
        assert end.day >= 28  # All months have at least 28 days

    def test_this_year_range(self):
        """Test this year range calculation."""
        start, end = get_this_year_range()
        today = date.today()

        assert start == date(today.year, 1, 1)
        assert end == date(today.year, 12, 31)

    def test_last_year_range(self):
        """Test last year range calculation."""
        start, end = get_last_year_range()
        today = date.today()

        assert start == date(today.year - 1, 1, 1)
        assert end == date(today.year - 1, 12, 31)


class TestDateParsingEdgeCases:
    """Test edge cases in date parsing."""

    def test_parse_year_boundaries(self):
        """Test parsing dates at year boundaries."""
        # New Year's Day
        result = parse_date_string("2024-01-01")
        assert result == date(2024, 1, 1)

        # New Year's Eve
        result = parse_date_string("2024-12-31")
        assert result == date(2024, 12, 31)

    def test_parse_month_boundaries(self):
        """Test parsing dates at month boundaries."""
        # First day of month
        result = parse_date_string("2024-06-01")
        assert result == date(2024, 6, 1)

        # Last day of month (30-day month)
        result = parse_date_string("2024-06-30")
        assert result == date(2024, 6, 30)

        # Last day of month (31-day month)
        result = parse_date_string("2024-07-31")
        assert result == date(2024, 7, 31)

    def test_parse_invalid_month(self):
        """Test parsing invalid month."""
        with pytest.raises(DateParseError):
            parse_date_string("2024-13-01")  # Month 13 doesn't exist

    def test_parse_invalid_day(self):
        """Test parsing invalid day."""
        with pytest.raises(DateParseError):
            parse_date_string("2024-06-31")  # June only has 30 days

    def test_parse_zero_values(self):
        """Test parsing zero values."""
        with pytest.raises(DateParseError):
            parse_date_string("2024-00-01")  # Month 0 doesn't exist

        with pytest.raises(DateParseError):
            parse_date_string("2024-01-00")  # Day 0 doesn't exist
