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
from .common import handle_default_ledger
from .shared_utils import determine_single_file_mode

# Import existing functionality
from ..pocketsmith.common import PocketSmithClient
from ..beancount.read import read_ledger
from beancount.core import data as bc_data
from decimal import Decimal


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

    def _normalize_value(self, value: Any, field: str) -> Any:
        """Normalize value for semantic comparison.

        Args:
            value: The value to normalize
            field: The field name (for field-specific normalization)

        Returns:
            Normalized value for comparison
        """
        # Special handling for is_transfer first (before general None handling)
        if field == "is_transfer":
            # Both None and False mean "not a transfer"
            # Normalize both to False for comparison
            if (
                value is None
                or value is False
                or (isinstance(value, str) and value.lower() in ("false", "0", ""))
            ):
                return False
            return bool(value)

        # Treat None, empty string, and empty list as equivalent "unset" values
        if value is None or value == "" or value == []:
            return None

        return value

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
            ("is_transfer", "is_transfer"),
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
            else:
                # Normalize values for semantic equivalence
                normalized_local = self._normalize_value(local_value, field)
                normalized_remote = self._normalize_value(remote_value, field)

                if normalized_local != normalized_remote:
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
    """Read transactions from beancount and map to comparable local fields.

    Produces mapping: id -> {amount, payee, category_id, labels, note}
    """
    # Determine the main file to parse
    ledger_file = path if single_file else (path / "main.beancount")
    if not ledger_file.exists():
        return {}

    try:
        entries, _errors, _opts = read_ledger(str(ledger_file))
    except Exception:
        return {}

    # Build category account -> id mapping from Open directives metadata
    category_id_map: Dict[str, Optional[int]] = {}
    for entry in entries:
        if isinstance(entry, bc_data.Open):
            account = entry.account
            if account.startswith(("Expenses:", "Income:", "Transfers:")):
                meta = entry.meta or {}
                cat_id = meta.get("id")
                try:
                    category_id_map[account] = (
                        int(str(cat_id)) if cat_id is not None else None
                    )
                except Exception:
                    category_id_map[account] = None

    # Extract transactions
    local: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        if isinstance(entry, bc_data.Transaction):
            meta = entry.meta or {}
            tx_id = meta.get("id")
            if tx_id is None:
                continue
            tx_id = str(tx_id)

            payee = entry.payee or ""
            narration = entry.narration or ""
            labels = list(entry.tags) if entry.tags else []

            # Determine amount and category account from postings
            amount_val: Optional[float] = None
            category_account: Optional[str] = None
            for p in entry.postings:
                acct = p.account
                if p.units is None:
                    continue
                number_val = p.units.number
                if isinstance(number_val, Decimal):
                    num = float(number_val)
                elif number_val is None:
                    num = 0.0
                else:
                    try:
                        num = float(number_val)
                    except Exception:
                        num = 0.0

                if acct.startswith(("Assets:", "Liabilities:")):
                    # Preserve sign from Assets/Liabilities posting to match PocketSmith API
                    # where negative = debit (money out), positive = credit (money in)
                    amount_val = num
                elif acct.startswith(("Expenses:", "Income:", "Transfers:")):
                    category_account = acct

            # Fallback amount: take first posting with preserved sign
            if amount_val is None and entry.postings:
                p0 = entry.postings[0]
                if p0.units is not None:
                    n0 = p0.units.number
                    if isinstance(n0, Decimal):
                        amount_val = float(n0)
                    elif n0 is None:
                        amount_val = None
                    else:
                        try:
                            amount_val = float(n0)
                        except Exception:
                            amount_val = None

            # Map category account to id if possible
            category_id = None
            if category_account:
                category_id = category_id_map.get(category_account)

            # Encode transfer metadata into note field
            from ..pocketsmith.metadata_encoding import encode_metadata_in_note

            transfer_metadata = {}
            if meta.get("paired") is not None:
                transfer_metadata["paired"] = int(str(meta["paired"]))
            if meta.get("suspect_reason"):
                transfer_metadata["suspect_reason"] = str(meta["suspect_reason"])

            # Encode metadata into narration
            note_with_metadata = encode_metadata_in_note(narration, transfer_metadata)

            # Get is_transfer from metadata
            is_transfer_val = meta.get("is_transfer")
            # Normalize to boolean for comparison
            if isinstance(is_transfer_val, str):
                is_transfer = is_transfer_val.lower() in ("true", "1", "yes")
            else:
                is_transfer = (
                    bool(is_transfer_val) if is_transfer_val is not None else False
                )

            local[tx_id] = {
                "amount": amount_val,
                "payee": payee,
                "category_id": category_id,
                "labels": sorted(list(labels)),
                "note": note_with_metadata,
                "is_transfer": is_transfer,
            }

    return local


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

        # Handle default destination using consistent resolution pattern
        if destination is None:
            try:
                destination, _ = handle_default_ledger(None)
            except Exception as e:
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
            if transaction_id:
                txn = client.get_transaction(int(transaction_id))
                transactions = [txn]
            else:
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
