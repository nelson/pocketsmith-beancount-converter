"""Pull command implementation for updating PocketSmith transactions."""

from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from datetime import timedelta
import json

import typer
from dotenv import load_dotenv

from .date_parser import (
    DateParseError,
    expand_date_range,
    get_this_month_range,
    get_last_month_range,
    get_this_year_range,
    get_last_year_range,
)
from .validators import validate_date_options, ValidationError
from .changelog import ChangelogManager, determine_changelog_path
from .date_options import DateOptions
from .shared_utils import apply_ledgerset_filtering, determine_single_file_mode

# Import refactored functionality
from ..pocketsmith.common import PocketSmithClient
from ..beancount.write import write_hierarchical_ledger
from .diff import read_local_transactions as _read_local_for_diff


class TransactionComparator:
    """Compare transactions to detect changes."""

    def __init__(self) -> None:
        self.changes: List[Tuple[str, str, str, str]] = []
        self.new_transactions = 0
        self.updated_transactions = 0

    def compare_transactions(
        self, existing: Dict[str, Dict[str, Any]], fetched: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Compare existing and fetched transactions.

        Returns:
            Tuple of (new_transactions, updated_transactions)
        """
        new_transactions = []
        updated_transactions = []

        # Create lookup for fetched transactions
        fetched_lookup = {str(t.get("id")): t for t in fetched}

        # Check each fetched transaction
        for transaction_id, transaction in fetched_lookup.items():
            if transaction_id in existing:
                # Compare for changes
                existing_txn = existing[transaction_id]
                changes = self._detect_changes(
                    transaction_id, existing_txn, transaction
                )
                if changes:
                    updated_transactions.append(transaction)
                    self.updated_transactions += 1
                    self.changes.extend(changes)
            else:
                new_transactions.append(transaction)
                self.new_transactions += 1

        return new_transactions, updated_transactions

    def _detect_changes(
        self, transaction_id: str, existing: Dict[str, Any], fetched: Dict[str, Any]
    ) -> List[Tuple[str, str, str, str]]:
        """Detect changes between existing and fetched transaction."""
        changes = []

        # Check key fields for changes
        fields_to_check = [
            ("amount", "amount"),
            ("payee", "payee"),
            ("category_id", "category"),
            ("labels", "labels"),
            ("note", "note"),
        ]

        for field, display_name in fields_to_check:
            old_value = existing.get(field)

            # Extract category_id from nested category object
            if field == "category_id":
                category_obj = fetched.get("category")
                new_value = category_obj.get("id") if category_obj else None
            else:
                new_value = fetched.get(field)

            # Special handling for labels (list comparison)
            if field == "labels":
                old_value = sorted(old_value or [])
                new_value = sorted(new_value or [])
                if old_value != new_value:
                    changes.append(
                        (
                            transaction_id,
                            display_name,
                            json.dumps(old_value),
                            json.dumps(new_value),
                        )
                    )
            elif old_value != new_value:
                changes.append(
                    (
                        transaction_id,
                        display_name,
                        str(old_value) if old_value is not None else "null",
                        str(new_value) if new_value is not None else "null",
                    )
                )

        return changes


def read_existing_transactions(
    path: Path, single_file: bool
) -> Dict[str, Dict[str, Any]]:
    """Read existing transactions leveraging the diff reader implementation."""
    return _read_local_for_diff(path, single_file)


def read_existing_month_includes(ledger_dir: Path) -> List[str]:
    """Read existing month includes from main.beancount file.

    Returns list of year-month strings like ["2020-02", "2020-03", ...]
    """
    main_file = ledger_dir / "main.beancount"
    if not main_file.exists():
        return []

    months = []
    try:
        with open(main_file, "r", encoding="utf-8") as f:
            for line in f:
                # Look for include statements like: include "2020/2020-02.beancount"
                if line.strip().startswith('include "') and '.beancount"' in line:
                    # Extract the year-month from the path
                    import re

                    match = re.search(
                        r'include "(\d{4})/(\d{4}-\d{2})\.beancount"', line
                    )
                    if match:
                        year_month = match.group(2)
                        months.append(year_month)
    except Exception:
        pass

    return months


def read_existing_account_dates(ledger_dir: Path) -> Dict[int, str]:
    """Read existing account opening dates from main.beancount.

    Returns dict mapping account_id to opening date string (YYYY-MM-DD).
    This preserves the account opening dates established during clone,
    preventing them from being recalculated incorrectly during pull operations.
    """
    import re

    main_file = ledger_dir / "main.beancount"
    if not main_file.exists():
        return {}

    account_dates = {}
    try:
        with open(main_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            i = 0
            while i < len(lines):
                line = lines[i]
                # Match account open directive: 2020-02-01 open Assets:Foo:Bar AUD
                match = re.match(r"^(\d{4}-\d{2}-\d{2})\s+open\s+[\w:]+", line)
                if match:
                    open_date = match.group(1)
                    # Look for id metadata on next line
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        id_match = re.search(r"id:\s+(\d+)", next_line)
                        if id_match:
                            account_id = int(id_match.group(1))
                            account_dates[account_id] = open_date
                i += 1
    except Exception:
        pass

    return account_dates


def pull_command(
    destination: Path,
    date_options: Optional[DateOptions] = None,
    dry_run: bool = False,
    verbose: bool = False,
    quiet: bool = False,
    transaction_id: Optional[str] = None,
    ledgerset: Optional[str] = None,
) -> None:
    """Update local Beancount ledger with recent PocketSmith data.

    Updates the local Beancount ledger to the most recent data based on remote
    PocketSmith, fetching any new transactions within the scope of the original clone.
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

        # Check if destination exists
        if not destination.exists():
            typer.echo(f"Error: Destination does not exist: {destination}", err=True)
            raise typer.Exit(1)

        # Determine single file mode
        single_file = determine_single_file_mode(destination)

        # Get changelog path and read last sync info
        changelog_path = determine_changelog_path(destination, single_file)
        changelog = ChangelogManager(changelog_path)

        last_sync_info = changelog.get_last_sync_info()
        if not last_sync_info:
            typer.echo("Error: No previous clone or pull found in changelog", err=True)
            raise typer.Exit(1)

        last_sync_timestamp, last_from_date, last_to_date = last_sync_info

        # Determine date range for fetch
        start_date_str: Optional[str] = None
        end_date_str: Optional[str] = None
        use_new_dates = False

        if this_month:
            start_date, end_date = get_this_month_range()
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
            use_new_dates = True
        elif last_month:
            start_date, end_date = get_last_month_range()
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
            use_new_dates = True
        elif this_year:
            start_date, end_date = get_this_year_range()
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
            use_new_dates = True
        elif last_year:
            start_date, end_date = get_last_year_range()
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
            use_new_dates = True
        elif from_date or to_date:
            start_date, end_date = expand_date_range(from_date, to_date)
            start_date_str = start_date.isoformat() if start_date else None
            end_date_str = end_date.isoformat() if end_date else None
            use_new_dates = True
        else:
            # Use dates from last sync
            start_date_str = last_from_date
            end_date_str = last_to_date

        # Connect to PocketSmith API
        if not quiet:
            typer.echo("Connecting to PocketSmith API...")

        try:
            client = PocketSmithClient()
            user = client.get_user()
            if not quiet:
                typer.echo(f"Connected as: {user.get('login', 'Unknown User')}")
        except Exception as e:
            typer.echo(f"Error: Failed to connect to PocketSmith API: {e}", err=True)
            raise typer.Exit(1)

        # Fetch transaction accounts and categories (needed for conversion)
        if not quiet:
            typer.echo("Fetching account and category information...")

        try:
            transaction_accounts = client.get_transaction_accounts()
            categories = client.get_categories()
        except Exception as e:
            typer.echo(f"Error: Failed to fetch account/category data: {e}", err=True)
            raise typer.Exit(1)

        # Fetch transactions with updated_since
        if not quiet:
            typer.echo("Fetching updated transactions...")

        all_transactions = []
        comparator = TransactionComparator()

        try:
            # First fetch: use updated_since with original date range
            if not use_new_dates:
                # Convert timestamp to UTC if it's naive (for backward compatibility)
                # Changelog now stores UTC timestamps, but old entries may be local

                if last_sync_timestamp.tzinfo is None:
                    # Naive timestamp - assume it's local time and convert to UTC
                    # Try to get system timezone
                    try:
                        from datetime import timezone
                        import time

                        # Get local timezone offset
                        if time.daylight:
                            utc_offset = -time.altzone
                        else:
                            utc_offset = -time.timezone
                        local_tz = timezone(timedelta(seconds=utc_offset))

                        # Localize and convert to UTC
                        last_sync_timestamp = last_sync_timestamp.replace(
                            tzinfo=local_tz
                        )
                        last_sync_timestamp = last_sync_timestamp.astimezone(
                            timezone.utc
                        )
                    except Exception:
                        # Fallback: treat as UTC
                        from datetime import timezone

                        last_sync_timestamp = last_sync_timestamp.replace(
                            tzinfo=timezone.utc
                        )

                # Use exact timestamp - API uses >, not >=, so transactions at exact
                # time won't be returned, but that's acceptable (very rare edge case)
                updated_since = last_sync_timestamp.isoformat()

                transactions = client.get_transactions(
                    start_date=start_date_str,
                    end_date=end_date_str,
                    updated_since=updated_since,
                )
                all_transactions.extend(transactions)

                if not quiet:
                    typer.echo(
                        f"Found {len(transactions)} updated transactions since {updated_since}"
                    )

            # Second fetch: new date range without updated_since
            if use_new_dates:
                transactions = client.get_transactions(
                    start_date=start_date_str,
                    end_date=end_date_str,
                )
                all_transactions.extend(transactions)

                if not quiet:
                    typer.echo(
                        f"Found {len(transactions)} transactions in new date range"
                    )

        except Exception as e:
            typer.echo(f"Error: Failed to fetch transactions: {e}", err=True)
            raise typer.Exit(1)

        # Read existing transactions
        existing_transactions = read_existing_transactions(destination, single_file)

        # Apply ledgerset filtering if specified
        if ledgerset:
            existing_transactions = apply_ledgerset_filtering(
                existing_transactions, ledgerset, destination
            )

        # Compare transactions
        new_txns, updated_txns = comparator.compare_transactions(
            existing_transactions, all_transactions
        )

        # If verbose mode and dry_run, print what would be updated
        if dry_run and verbose:
            for txn_id, key, old_val, new_val in comparator.changes:
                typer.echo(f"UPDATE {txn_id} {key} {old_val} → {new_val}")

        # Process updates if not dry run
        if not dry_run:
            # Skip balance assertions
            # Balance assertions in beancount require ALL prior transactions to be in the ledger
            # to calculate the accumulated balance. Auto-generated balance assertions will fail
            # unless we have complete transaction history. Users should manually add balance
            # assertions at points where they've verified their account balances.
            account_balances: Dict[int, List[Dict[str, Any]]] = {}

            # Write transactions using refactored functionality
            if single_file:
                # For single file, use the new write functionality
                from ..beancount.write import (
                    generate_transactions_content,
                    generate_main_file_content,
                )

                # Generate all transactions in one file
                content = generate_main_file_content(
                    [],  # No year_months for single file
                    transaction_accounts,
                    categories,
                    account_balances,
                )

                # Add transactions
                transaction_content = generate_transactions_content(all_transactions)
                if transaction_content:
                    content += "\n\n" + transaction_content

                with open(destination, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                # For hierarchical structure, read existing months and account dates
                existing_months = read_existing_month_includes(destination)
                existing_account_dates = read_existing_account_dates(destination)
                write_hierarchical_ledger(
                    all_transactions,
                    transaction_accounts,
                    categories,
                    str(destination),
                    account_balances,
                    existing_months,
                    existing_account_dates,
                )

            # Write changelog entries
            since_timestamp = (
                last_sync_timestamp.isoformat() if not use_new_dates else ""
            )
            changelog.write_pull_entry(since_timestamp, start_date_str, end_date_str)

            # Write UPDATE entries (using resolver strategy)
            for txn_id, key, old_val, new_val in comparator.changes:
                changelog.write_update_entry(txn_id, key, old_val, new_val)

                # Print update if verbose mode is enabled
                if verbose:
                    typer.echo(f"UPDATE {txn_id} {key} {old_val} → {new_val}")

        # Print summary
        if not quiet:
            ledger_str = str(destination) if single_file else str(destination) + "/"

            if dry_run:
                typer.echo(f"Ledger {ledger_str} not updated (due to --dry-run).")
                typer.echo(
                    f"Changelog {changelog_path} not updated (due to --dry-run)."
                )
            else:
                typer.echo(f"Ledger {ledger_str} updated.")
                typer.echo(f"Changelog {changelog_path} updated.")

            typer.echo(
                f"{len(all_transactions)} existing transactions were fetched, "
                f"with {comparator.updated_transactions} receiving updates."
            )

            from_str = start_date_str or "(null)"
            to_str = end_date_str or "(null)"
            typer.echo(
                f"{comparator.new_transactions} new transactions were added to the ledger "
                f"between dates {from_str} to {to_str}."
            )

    except ValidationError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except DateParseError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)
