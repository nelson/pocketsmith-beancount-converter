"""Shared utility functions for CLI commands to eliminate duplication."""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta

import typer

from .date_parser import (
    get_this_month_range,
    get_last_month_range,
    get_this_year_range,
    get_last_year_range,
    expand_date_range,
)
from .date_options import DateOptions
from .changelog import ChangelogManager


def determine_single_file_mode(path: Path) -> bool:
    """Determine if the path is using single file or hierarchical mode.

    Args:
        path: File or directory path to check

    Returns:
        True if single file mode, False if hierarchical mode

    Raises:
        ValueError: If path does not exist
    """
    if path.is_file():
        return True
    elif path.is_dir():
        # Check if it has the hierarchical structure
        main_file = path / "main.beancount"
        return not main_file.exists()
    else:
        raise ValueError(f"Path does not exist: {path}")


def choose_date_range(
    changelog: ChangelogManager,
    date_options: Optional[DateOptions],
) -> Tuple[Optional[str], Optional[str]]:
    """Determine date range from options or last sync info.

    This function handles both required and optional DateOptions, making it
    suitable for all CLI commands.

    Args:
        changelog: Changelog manager to retrieve last sync info
        date_options: Optional date filtering options

    Returns:
        Tuple of (from_date, to_date) as ISO format strings, or (None, None)
    """
    if not date_options:
        # No date options provided, use last sync info or reasonable defaults
        last = changelog.get_last_sync_info()
        if last:
            _, from_date, to_date = last
            return from_date, to_date
        else:
            # No sync info, get recent transactions (last 30 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            return start_date.isoformat()[:10], end_date.isoformat()[:10]

    if date_options.this_month:
        start, end = get_this_month_range()
        return start.isoformat(), end.isoformat()
    if date_options.last_month:
        start, end = get_last_month_range()
        return start.isoformat(), end.isoformat()
    if date_options.this_year:
        start, end = get_this_year_range()
        return start.isoformat(), end.isoformat()
    if date_options.last_year:
        start, end = get_last_year_range()
        return start.isoformat(), end.isoformat()
    if date_options.from_date or date_options.to_date:
        start, end = expand_date_range(date_options.from_date, date_options.to_date)
        return start.isoformat() if start else None, end.isoformat() if end else None

    # No specific date options, use last sync info or reasonable defaults
    last = changelog.get_last_sync_info()
    if last:
        _, from_date, to_date = last
        return from_date, to_date
    else:
        # No sync info, get recent transactions (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        return start_date.isoformat()[:10], end_date.isoformat()[:10]


def apply_ledgerset_filtering(
    transactions: Dict[str, Dict[str, Any]], ledgerset: str, ledger_base_path: Path
) -> Dict[str, Dict[str, Any]]:
    """Filter transactions to only those that match the ledgerset criteria.

    Args:
        transactions: Dictionary mapping transaction IDs to transaction data
        ledgerset: Ledgerset pattern (file/directory name or date range pattern)
        ledger_base_path: Base path of the ledger for file resolution

    Returns:
        Filtered dictionary of transactions matching the ledgerset
    """
    # Import here to avoid circular dependency
    from .rule_commands import (
        _get_transaction_ids_from_ledgerset,
        _extract_date_ranges_from_ledgerset,
        _get_transaction_date,
        _transaction_matches_date_ranges,
    )

    # Try to get transaction IDs from specific ledgerset files
    target_transaction_ids = _get_transaction_ids_from_ledgerset(
        ledger_base_path, ledgerset
    )

    if target_transaction_ids:
        # Filter transactions to only those in the ledgerset
        filtered_transactions = {
            tx_id: tx_data
            for tx_id, tx_data in transactions.items()
            if tx_id in target_transaction_ids
        }
        typer.echo(
            f"Ledgerset '{ledgerset}' filtered to {len(filtered_transactions)} transactions"
        )
        return filtered_transactions
    else:
        # Fall back to date-based filtering if no files found but pattern matches date ranges
        date_ranges = _extract_date_ranges_from_ledgerset(ledgerset)
        if date_ranges:
            filtered_transactions = {}
            for tx_id, tx_data in transactions.items():
                transaction_date = _get_transaction_date(tx_data)
                if transaction_date and _transaction_matches_date_ranges(
                    transaction_date, date_ranges
                ):
                    filtered_transactions[tx_id] = tx_data
            typer.echo(
                f"Ledgerset '{ledgerset}' date-filtered to {len(filtered_transactions)} transactions"
            )
            return filtered_transactions
        else:
            typer.echo(f"Warning: No transactions found for ledgerset '{ledgerset}'")
            return {}
