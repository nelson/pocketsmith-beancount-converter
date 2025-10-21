"""Shared date parsing utilities for compare module."""

from typing import Any
from datetime import datetime, date


def parse_date(date_value: Any) -> date:
    """Parse date from various formats (PocketSmith, Beancount, etc.).

    Args:
        date_value: Date value in various formats (date, datetime, str, or None)

    Returns:
        Parsed date object, defaults to today if parsing fails
    """
    if date_value is None:
        return date.today()

    if isinstance(date_value, date):
        return date_value

    if isinstance(date_value, datetime):
        return date_value.date()

    if isinstance(date_value, str):
        try:
            # Try ISO format first (handles PocketSmith/Beancount format)
            parsed = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            return parsed.date()
        except ValueError:
            try:
                # Try just date format - slice to 10 chars to handle longer strings
                parsed = datetime.strptime(date_value[:10], "%Y-%m-%d")
                return parsed.date()
            except (ValueError, IndexError):
                pass

    # Fallback to today
    return date.today()
