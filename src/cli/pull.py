"""Pull command implementation for updating PocketSmith transactions."""

from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
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
from .changelog import ChangelogManager, determine_changelog_path

# Import existing functionality
from ..pocketsmith_beancount.pocketsmith_client import PocketSmithClient
from ..pocketsmith_beancount.beancount_converter import BeancountConverter
from ..pocketsmith_beancount.file_writer import BeancountFileWriter


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
    """Read existing transactions from beancount files.

    Returns:
        Dict mapping transaction ID to transaction data
    """
    transactions: Dict[str, Dict[str, Any]] = {}

    # This is a simplified implementation - in reality, we'd need to parse
    # the beancount files to extract transaction metadata
    # For now, return empty dict to allow the pull to proceed
    return transactions


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


def pull_command(
    destination: Path,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    this_month: bool = False,
    last_month: bool = False,
    this_year: bool = False,
    last_year: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    quiet: bool = False,
) -> None:
    """Update local Beancount ledger with recent PocketSmith data.

    Updates the local Beancount ledger to the most recent data based on remote
    PocketSmith, fetching any new transactions within the scope of the original clone.
    """
    # Load environment variables
    load_dotenv()

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
            # Fetch account balances
            account_balances = {}
            try:
                for transaction_account in transaction_accounts:
                    transaction_account_id = transaction_account.get("id")
                    current_balance = transaction_account.get("current_balance")
                    current_balance_date = transaction_account.get(
                        "current_balance_date"
                    )

                    if (
                        transaction_account_id
                        and current_balance is not None
                        and current_balance_date
                    ):
                        account_balances[transaction_account_id] = [
                            {
                                "date": f"{current_balance_date}T00:00:00Z",
                                "balance": str(current_balance),
                            }
                        ]
            except Exception:
                account_balances = {}

            # Convert and write transactions
            converter = BeancountConverter()

            if single_file:
                # For single file, we need to merge with existing content
                # This is simplified - in reality we'd need to parse and merge
                beancount_content = converter.convert_transactions(
                    all_transactions, transaction_accounts, categories, account_balances
                )

                with open(destination, "w", encoding="utf-8") as f:
                    f.write(beancount_content)
            else:
                # For hierarchical structure
                writer = BeancountFileWriter(str(destination))
                writer.write_hierarchical_beancount_files(
                    all_transactions,
                    transaction_accounts,
                    categories,
                    account_balances,
                    converter,
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
