"""Clone command implementation for downloading PocketSmith transactions."""

from pathlib import Path
from typing import Optional
from datetime import date

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
from .file_handler import (
    validate_output_destination,
    get_output_file_path,
    create_hierarchical_structure,
    FileHandlerError,
)
from .validators import validate_date_options, ValidationError
from .changelog import ChangelogManager, determine_changelog_path
from .date_options import DateOptions

# Import existing functionality
from ..pocketsmith_beancount.pocketsmith_client import PocketSmithClient
from ..pocketsmith_beancount.beancount_converter import BeancountConverter
from ..pocketsmith_beancount.file_writer import BeancountFileWriter


def clone_command(
    destination: Path,
    single_file: bool = False,
    date_options: Optional[DateOptions] = None,
    quiet: bool = False,
) -> None:
    """Download PocketSmith transactions and write them to beancount format.

    By default, creates a hierarchical structure with main.beancount and monthly
    files in yearly subdirectories. Use -1/--single-file to write everything
    to a single file.

    The destination must not exist and must be in a writable location.
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

        # Validate and prepare output destination
        dest_path = validate_output_destination(destination, single_file)

        # Determine date range
        start_date: Optional[date] = None
        end_date: Optional[date] = None
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

        # Fetch data from PocketSmith
        if not quiet:
            typer.echo("Fetching transaction accounts...")
        try:
            transaction_accounts = client.get_transaction_accounts()
            if not quiet:
                typer.echo(f"Found {len(transaction_accounts)} transaction accounts")
        except Exception as e:
            typer.echo(f"Error: Failed to fetch transaction accounts: {e}", err=True)
            raise typer.Exit(1)

        if not quiet:
            typer.echo("Fetching categories...")
        try:
            categories = client.get_categories()
            if not quiet:
                typer.echo(f"Found {len(categories)} categories")
        except Exception as e:
            typer.echo(f"Error: Failed to fetch categories: {e}", err=True)
            raise typer.Exit(1)

        if not quiet:
            typer.echo("Fetching transactions...")
        try:
            transactions = client.get_transactions(
                start_date=start_date_str,
                end_date=end_date_str,
                account_id=None,  # Could be added as a future option
            )

            if not quiet:
                typer.echo(f"Found {len(transactions)} transactions")
        except Exception as e:
            typer.echo(f"Error: Failed to fetch transactions: {e}", err=True)
            raise typer.Exit(1)

        if not transactions:
            if not quiet:
                typer.echo("No transactions found for the specified criteria.")

            # Still create the changelog even with no transactions
            changelog_path = determine_changelog_path(dest_path, single_file)
            changelog = ChangelogManager(changelog_path)
            changelog.write_clone_entry(start_date_str, end_date_str)

            if not quiet:
                ledger_location = (
                    str(dest_path) if single_file else str(dest_path) + "/"
                )
                typer.echo(f"Ledger written to {ledger_location}.")
                typer.echo(f"Changelog written to {changelog_path}.")
                from_str = start_date_str or "(null)"
                to_str = end_date_str or "(null)"
                typer.echo(
                    f"0 transactions cloned between dates {from_str} to {to_str}."
                )
            return

        # Fetch account balances
        if not quiet:
            typer.echo("Fetching account balances...")
        try:
            account_balances = {}
            for transaction_account in transaction_accounts:
                transaction_account_id = transaction_account.get("id")
                current_balance = transaction_account.get("current_balance")
                current_balance_date = transaction_account.get("current_balance_date")

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
            if not quiet:
                typer.echo(f"Extracted balances for {len(account_balances)} accounts")
        except Exception as e:
            if not quiet:
                typer.echo(f"Warning: Failed to fetch account balances: {e}", err=True)
            account_balances = {}

        # Convert to Beancount format
        if not quiet:
            typer.echo("Converting to Beancount format...")
        converter = BeancountConverter()

        if single_file:
            # Single file output
            output_file = get_output_file_path(dest_path, single_file)

            beancount_content = converter.convert_transactions(
                transactions, transaction_accounts, categories, account_balances
            )

            if not quiet:
                typer.echo("Writing to file...")
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(beancount_content)
            except Exception as e:
                typer.echo(f"Error: Failed to write file: {e}", err=True)
                raise typer.Exit(1)
        else:
            # Hierarchical file structure
            create_hierarchical_structure(dest_path)

            writer = BeancountFileWriter(str(dest_path))

            if not quiet:
                typer.echo("Using hierarchical file structure...")
            try:
                writer.write_hierarchical_beancount_files(
                    transactions,
                    transaction_accounts,
                    categories,
                    account_balances,
                    converter,
                )
            except Exception as e:
                typer.echo(f"Error: Failed to write hierarchical files: {e}", err=True)
                raise typer.Exit(1)

        # Write changelog
        changelog_path = determine_changelog_path(dest_path, single_file)
        changelog = ChangelogManager(changelog_path)
        changelog.write_clone_entry(start_date_str, end_date_str)

        # Print summary unless quiet
        if not quiet:
            ledger_location = str(dest_path) if single_file else str(dest_path) + "/"
            typer.echo(f"Ledger written to {ledger_location}.")
            typer.echo(f"Changelog written to {changelog_path}.")
            from_str = start_date_str or "(null)"
            to_str = end_date_str or "(null)"
            typer.echo(
                f"{len(transactions)} transactions cloned between dates {from_str} to {to_str}."
            )

    except ValidationError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except DateParseError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except FileHandlerError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)
