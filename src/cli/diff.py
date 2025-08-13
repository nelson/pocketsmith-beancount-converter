"""Diff command implementation for comparing local and remote PocketSmith data."""

from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
import json

import typer
from dotenv import load_dotenv

from .date_parser import (
    expand_date_range,
    get_this_month_range,
    get_last_month_range,
    get_this_year_range,
    get_last_year_range,
    DateParseError,
)
from .validators import validate_date_options, ValidationError
from .date_options import DateOptions
from .changelog import ChangelogManager, determine_changelog_path
from .file_handler import find_default_beancount_file, FileHandlerError

# Import existing functionality
from ..pocketsmith_beancount.pocketsmith_client import PocketSmithClient


class DiffComparator:
    """Compare local and remote transactions to detect differences."""

    def __init__(self) -> None:
        self.differences: List[Dict[str, Any]] = []
        self.identical_count = 0
        self.different_count = 0
        self.not_fetched_count = 0
        self.total_fetched = 0

    def compare_for_diff(
        self,
        local_transactions: Dict[str, Dict[str, Any]],
        remote_transactions: List[Dict[str, Any]],
    ) -> None:
        """Compare local and remote transactions for differences.

        Args:
            local_transactions: Dict mapping transaction ID to local transaction data
            remote_transactions: List of remote transactions from PocketSmith
        """
        self.total_fetched = len(remote_transactions)

        # Create lookup for remote transactions
        remote_lookup = {str(t.get("id")): t for t in remote_transactions}

        # Track which local transactions were found in remote
        local_ids = set(local_transactions.keys())
        remote_ids = set(remote_lookup.keys())

        # Find transactions not fetched from remote
        not_fetched_ids = local_ids - remote_ids
        self.not_fetched_count = len(not_fetched_ids)

        # Compare each remote transaction with local
        for transaction_id, remote_txn in remote_lookup.items():
            if transaction_id in local_transactions:
                local_txn = local_transactions[transaction_id]
                changes = self._detect_differences(
                    transaction_id, local_txn, remote_txn
                )

                if changes:
                    self.different_count += 1
                    self.differences.append(
                        {
                            "id": transaction_id,
                            "local": local_txn,
                            "remote": remote_txn,
                            "changes": changes,
                        }
                    )
                else:
                    self.identical_count += 1
            else:
                # Transaction exists in remote but not in local
                # This shouldn't happen if pull was done correctly
                pass

    def _detect_differences(
        self, transaction_id: str, local: Dict[str, Any], remote: Dict[str, Any]
    ) -> List[Tuple[str, str, str]]:
        """Detect differences between local and remote transaction.

        Returns:
            List of (field, local_value, remote_value) tuples for fields that differ
        """
        differences = []

        # Check key fields for differences
        fields_to_check = [
            ("amount", "amount"),
            ("payee", "payee"),
            ("category_id", "category"),
            ("labels", "labels"),
            ("note", "note"),
            ("merchant", "merchant"),
        ]

        for field, display_name in fields_to_check:
            local_value = local.get(field)
            remote_value = remote.get(field)

            # Special handling for labels (list comparison)
            if field == "labels":
                local_value = sorted(local_value or [])
                remote_value = sorted(remote_value or [])
                if local_value != remote_value:
                    differences.append(
                        (
                            display_name,
                            json.dumps(local_value),
                            json.dumps(remote_value),
                        )
                    )
            elif local_value != remote_value:
                differences.append(
                    (
                        display_name,
                        str(local_value) if local_value is not None else "null",
                        str(remote_value) if remote_value is not None else "null",
                    )
                )

        return differences

    def format_summary(self, from_date: Optional[str], to_date: Optional[str]) -> str:
        """Format a summary of the differences."""
        from_str = from_date or "(null)"
        to_str = to_date or "(null)"

        lines = [
            f"{self.total_fetched} existing transactions were fetched between dates {from_str} to {to_str}.",
            f"{self.different_count} transactions were different on the local ledger.",
            f"{self.identical_count} transactions were identical to the local ledger.",
            f"{self.not_fetched_count} transactions on the local ledger were not fetched from remote.",
        ]
        return "\n".join(lines)

    def format_ids(self) -> str:
        """Format transaction IDs that have differences."""
        ids = [diff["id"] for diff in self.differences]
        return "\n".join(ids)

    def format_changelog(self) -> str:
        """Format differences in changelog format."""
        lines = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for diff in self.differences:
            for field, local_val, remote_val in diff["changes"]:
                lines.append(
                    f"[{timestamp}] DIFF {diff['id']} {field} {local_val} <> {remote_val}"
                )

        return "\n".join(lines)

    def format_diff(self, ledger_path: Path, single_file: bool) -> str:
        """Format differences in diff format."""
        lines = []

        for diff in self.differences:
            transaction_id = diff["id"]

            # For simplicity, we'll use a basic diff format
            # In a real implementation, we'd need to parse the beancount file
            # to get actual line numbers
            lines.append(f"peabody diff {transaction_id}")

            if single_file:
                file_path = str(ledger_path)
            else:
                # Would need to determine which file contains the transaction
                file_path = str(ledger_path / "main.beancount")

            lines.append(f"--- local/{file_path}/{transaction_id}")
            lines.append(f"+++ remote/{transaction_id}")
            lines.append("@@@ -1,1 +1,1 @@@")

            # Show the actual differences
            for field, local_val, remote_val in diff["changes"]:
                lines.append(f"-   {field}: {local_val}")
                lines.append(f"+   {field}: {remote_val}")

            lines.append("")  # Empty line between diffs

        return "\n".join(lines)


def read_local_transactions(path: Path, single_file: bool) -> Dict[str, Dict[str, Any]]:
    """Read existing transactions from beancount files.

    This is a placeholder implementation. In reality, we'd need to parse
    the beancount files to extract transaction metadata.

    Returns:
        Dict mapping transaction ID to transaction data
    """
    # TODO: Implement actual beancount file parsing
    return {}


def determine_single_file_mode(path: Path) -> bool:
    """Determine if the path is using single file or hierarchical mode."""
    if path.is_file():
        return True
    elif path.is_dir():
        # Check if it has the hierarchical structure
        main_file = path / "main.beancount"
        return not main_file.exists()
    else:
        raise ValueError(f"Path does not exist: {path}")


def diff_command(
    destination: Optional[Path] = None,
    date_options: Optional[DateOptions] = None,
    format: str = "summary",
    transaction_id: Optional[str] = None,
) -> None:
    """Compare local beancount ledger with remote PocketSmith data.

    Print information about the differences between local and remote transaction data.
    Never modifies any files.
    """
    # Load environment variables
    load_dotenv()

    # Extract date options
    if date_options is None:
        date_options = DateOptions()

    from_date = date_options.from_date
    to_date = date_options.to_date
    this_month = date_options.this_month
    last_month = date_options.last_month
    this_year = date_options.this_year
    last_year = date_options.last_year

    try:
        # Validate date options
        validate_date_options(
            from_date,
            to_date,
            this_month,
            last_month,
            this_year,
            last_year,
        )

        # Handle default destination
        if destination is None:
            try:
                destination = find_default_beancount_file()
            except FileHandlerError as e:
                typer.echo(f"Error: {e}", err=True)
                raise typer.Exit(1)

        # Check if destination exists
        if not destination.exists():
            typer.echo(f"Error: Destination does not exist: {destination}", err=True)
            raise typer.Exit(1)

        # Determine single file mode
        single_file = determine_single_file_mode(destination)

        # Get changelog path and read last sync info
        changelog_path = determine_changelog_path(destination, single_file)
        changelog = ChangelogManager(changelog_path)

        # Determine date range
        start_date_str: Optional[str] = None
        end_date_str: Optional[str] = None

        if this_month:
            start_date, end_date = get_this_month_range()
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
        elif last_month:
            start_date, end_date = get_last_month_range()
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
        elif this_year:
            start_date, end_date = get_this_year_range()
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
        elif last_year:
            start_date, end_date = get_last_year_range()
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
        elif from_date or to_date:
            start_date, end_date = expand_date_range(from_date, to_date)
            start_date_str = start_date.isoformat() if start_date else None
            end_date_str = end_date.isoformat() if end_date else None
        else:
            # Use dates from last sync
            last_sync_info = changelog.get_last_sync_info()
            if not last_sync_info:
                typer.echo(
                    "Error: No previous clone or pull found in changelog", err=True
                )
                raise typer.Exit(1)

            _, start_date_str, end_date_str = last_sync_info

        # Connect to PocketSmith API
        try:
            client = PocketSmithClient()
            client.get_user()
        except Exception as e:
            typer.echo(f"Error: Failed to connect to PocketSmith API: {e}", err=True)
            raise typer.Exit(1)

        # Fetch transactions (without updated_since to get all in range)
        try:
            transactions = client.get_transactions(
                start_date=start_date_str,
                end_date=end_date_str,
            )
        except Exception as e:
            typer.echo(f"Error: Failed to fetch transactions: {e}", err=True)
            raise typer.Exit(1)

        # Read local transactions
        local_transactions = read_local_transactions(destination, single_file)

        # Compare transactions
        comparator = DiffComparator()
        comparator.compare_for_diff(local_transactions, transactions)

        # Format and print output based on format option
        if format == "summary":
            output = comparator.format_summary(start_date_str, end_date_str)
        elif format == "ids":
            output = comparator.format_ids()
        elif format == "changelog":
            output = comparator.format_changelog()
        elif format == "diff":
            output = comparator.format_diff(destination, single_file)
        else:
            typer.echo(f"Error: Unknown format: {format}", err=True)
            raise typer.Exit(1)

        typer.echo(output)

    except ValidationError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except DateParseError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)
