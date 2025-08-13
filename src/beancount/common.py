"""Common utilities and helpers for beancount operations."""

import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Optional, Any, Union, List
import pytz


class BeancountError(Exception):
    """Base exception for beancount-related errors."""

    pass


def sanitize_account_name(name: str) -> str:
    """Sanitize account name for beancount compliance."""
    # Strip initial underscores and convert spaces to hyphens
    name = name.lstrip("_")
    name = name.replace(" ", "-")
    # Replace other invalid characters with hyphens
    name = re.sub(r"[^a-zA-Z0-9\-]", "-", name)
    name = re.sub(r"-+", "-", name)
    return name.strip("-").title()


def format_account_name(account_type: str, institution: str, account_name: str) -> str:
    """Format a full account name for beancount."""
    sanitized_institution = sanitize_account_name(institution)
    sanitized_account = sanitize_account_name(account_name)
    return f"{account_type}:{sanitized_institution}:{sanitized_account}"


def convert_id_to_decimal(id_value: Any) -> Optional[Decimal]:
    """Convert ID to decimal number with error handling."""
    if id_value is None:
        return None

    try:
        # Handle both string and numeric IDs
        if isinstance(id_value, str):
            # Remove any non-numeric characters except decimal point
            cleaned_id = re.sub(r"[^\d.]", "", id_value)
            if not cleaned_id:
                return None
            return Decimal(cleaned_id)
        else:
            return Decimal(str(id_value))
    except (InvalidOperation, ValueError):
        # Return None for invalid IDs
        return None


def convert_to_aest(timestamp: Union[str, datetime]) -> str:
    """Convert timestamp to Australian Eastern Standard Time."""
    try:
        # Handle datetime objects
        if isinstance(timestamp, datetime):
            dt = timestamp
        else:
            # Handle string timestamps
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        # Convert to AEST (UTC+10) or AEDT (UTC+11) depending on date
        aest_tz = pytz.timezone("Australia/Sydney")
        aest_dt = dt.astimezone(aest_tz)

        # Return formatted string with milliseconds
        return aest_dt.strftime("%b %d %H:%M:%S.%f")[
            :-3
        ]  # Remove last 3 digits for milliseconds
    except (ValueError, AttributeError):
        # Fallback to string representation
        return str(timestamp)


def sanitize_tags_for_beancount(labels: List[str]) -> List[str]:
    """Sanitize labels to be valid beancount tags."""
    if not labels:
        return []

    sanitized_labels = []
    for label in labels:
        sanitized = re.sub(r"[^a-zA-Z0-9\-_]", "-", label).strip("-")
        if sanitized:
            sanitized_labels.append(sanitized)
    return sanitized_labels
