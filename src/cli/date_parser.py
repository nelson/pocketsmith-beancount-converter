"""Date parsing and validation utilities for CLI commands."""

import re
from datetime import datetime, date
from typing import Tuple, Optional
import calendar


class DateParseError(Exception):
    """Raised when date parsing fails."""

    pass


def parse_date_string(date_str: str) -> date:
    """Parse a date string in various formats.

    Supported formats:
    - YYYY-MM-DD: Full date
    - YYYYMMDD: Compact date
    - YYYY-MM: Month (uses first day)
    - YYYY: Year (uses first day)

    Args:
        date_str: Date string to parse

    Returns:
        Parsed date object

    Raises:
        DateParseError: If date string is invalid
    """
    if not date_str:
        raise DateParseError("Date string cannot be empty")

    # Remove any whitespace
    date_str = date_str.strip()

    # Try YYYY-MM-DD format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as e:
            raise DateParseError(f"Invalid date '{date_str}': {e}")

    # Try YYYYMMDD format
    if re.match(r"^\d{8}$", date_str):
        try:
            return datetime.strptime(date_str, "%Y%m%d").date()
        except ValueError as e:
            raise DateParseError(f"Invalid date '{date_str}': {e}")

    # Try YYYY-MM format (first day of month)
    if re.match(r"^\d{4}-\d{2}$", date_str):
        try:
            year, month = map(int, date_str.split("-"))
            return date(year, month, 1)
        except ValueError as e:
            raise DateParseError(f"Invalid year-month '{date_str}': {e}")

    # Try YYYY format (first day of year)
    if re.match(r"^\d{4}$", date_str):
        try:
            year = int(date_str)
            return date(year, 1, 1)
        except ValueError as e:
            raise DateParseError(f"Invalid year '{date_str}': {e}")

    raise DateParseError(
        f"Unsupported date format '{date_str}'. Use YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY"
    )


def expand_date_range(
    from_str: Optional[str], to_str: Optional[str]
) -> Tuple[date, date]:
    """Expand partial date strings to full date range.

    Args:
        from_str: Start date string (can be partial)
        to_str: End date string (can be partial), defaults to today if None

    Returns:
        Tuple of (start_date, end_date)

    Raises:
        DateParseError: If date strings are invalid
    """
    if not from_str:
        raise DateParseError("Start date is required")

    # Parse start date
    start_date = parse_date_string(from_str)

    # If no end date provided, use today
    if not to_str:
        end_date = date.today()
    else:
        # Parse end date, but handle partial dates specially
        if re.match(r"^\d{4}-\d{2}$", to_str.strip()):
            # YYYY-MM format - use last day of month
            year, month = map(int, to_str.strip().split("-"))
            last_day = calendar.monthrange(year, month)[1]
            end_date = date(year, month, last_day)
        elif re.match(r"^\d{4}$", to_str.strip()):
            # YYYY format - use last day of year
            year = int(to_str.strip())
            end_date = date(year, 12, 31)
        else:
            # Full date format
            end_date = parse_date_string(to_str)

    # Validate date range
    if start_date > end_date:
        raise DateParseError(f"Start date {start_date} is after end date {end_date}")

    return start_date, end_date


def get_this_month_range() -> Tuple[date, date]:
    """Get date range for current calendar month."""
    today = date.today()
    start_date = date(today.year, today.month, 1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    end_date = date(today.year, today.month, last_day)
    return start_date, end_date


def get_last_month_range() -> Tuple[date, date]:
    """Get date range for previous calendar month."""
    today = date.today()
    if today.month == 1:
        # Previous month is December of last year
        year = today.year - 1
        month = 12
    else:
        year = today.year
        month = today.month - 1

    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    return start_date, end_date


def get_this_year_range() -> Tuple[date, date]:
    """Get date range for current calendar year."""
    today = date.today()
    start_date = date(today.year, 1, 1)
    end_date = date(today.year, 12, 31)
    return start_date, end_date


def get_last_year_range() -> Tuple[date, date]:
    """Get date range for previous calendar year."""
    today = date.today()
    year = today.year - 1
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    return start_date, end_date
