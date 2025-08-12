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
from .validators import validate_all_clone_options, ValidationError

# Import existing functionality
from ..pocketsmith_beancount.pocketsmith_client import PocketSmithClient
from ..pocketsmith_beancount.beancount_converter import BeancountConverter
from ..pocketsmith_beancount.file_writer import BeancountFileWriter


def clone_command(
    destination: Path = typer.Argument(..., help="Output file or directory path"),
    single_file: bool = typer.Option(
        False,
        "-1",
        "--single-file",
        help="Write all data to a single file instead of hierarchical structure",
    ),
    limit: Optional[int] = typer.Option(
        30, "-n", "--limit", help="Number of transactions to download (default: 30)"
    ),
    all_transactions: bool = typer.Option(
        False, "--all", help="Download all transactions (subject to date limitations)"
    ),
    from_date: Optional[str] = typer.Option(
        None, "--from", help="Start date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)"
    ),
    to_date: Optional[str] = typer.Option(
        None, "--to", help="End date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)"
    ),
    this_month: bool = typer.Option(
        False, "--this-month", help="Download transactions from current calendar month"
    ),
    last_month: bool = typer.Option(
        False, "--last-month", help="Download transactions from previous calendar month"
    ),
    this_year: bool = typer.Option(
        False, "--this-year", help="Download transactions from current calendar year"
    ),
    last_year: bool = typer.Option(
        False, "--last-year", help="Download transactions from previous calendar year"
    ),
) -> None:
    """Download PocketSmith transactions and write them to beancount format.

    By default, creates a hierarchical structure with main.beancount and monthly
    files in yearly subdirectories. Use -1/--single-file to write everything
    to a single file.

    The destination must not exist and must be in a writable location.
    """
    # Load environment variables
    load_dotenv()

    try:
        # Validate all input options
        validate_all_clone_options(
            limit,
            all_transactions,
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

        if this_month:
            start_date, end_date = get_this_month_range()
        elif last_month:
            start_date, end_date = get_last_month_range()
        elif this_year:
            start_date, end_date = get_this_year_range()
        elif last_year:
            start_date, end_date = get_last_year_range()
        elif from_date or to_date:
            start_date, end_date = expand_date_range(from_date, to_date)

        # Determine transaction limit
        transaction_limit = None if all_transactions else limit

        # Connect to PocketSmith API
        typer.echo("Connecting to PocketSmith API...")
        try:
            client = PocketSmithClient()
            user = client.get_user()
            typer.echo(f"Connected as: {user.get('login', 'Unknown User')}")
        except Exception as e:
            typer.echo(f"Error: Failed to connect to PocketSmith API: {e}", err=True)
            raise typer.Exit(1)

        # Fetch data from PocketSmith
        typer.echo("Fetching transaction accounts...")
        try:
            transaction_accounts = client.get_transaction_accounts()
            typer.echo(f"Found {len(transaction_accounts)} transaction accounts")
        except Exception as e:
            typer.echo(f"Error: Failed to fetch transaction accounts: {e}", err=True)
            raise typer.Exit(1)

        typer.echo("Fetching categories...")
        try:
            categories = client.get_categories()
            typer.echo(f"Found {len(categories)} categories")
        except Exception as e:
            typer.echo(f"Error: Failed to fetch categories: {e}", err=True)
            raise typer.Exit(1)

        typer.echo("Fetching transactions...")
        try:
            transactions = client.get_transactions(
                start_date=start_date.isoformat() if start_date else None,
                end_date=end_date.isoformat() if end_date else None,
                account_id=None,  # Could be added as a future option
            )

            # Apply transaction limit if specified
            if transaction_limit is not None:
                transactions = transactions[:transaction_limit]

            typer.echo(f"Found {len(transactions)} transactions")
        except Exception as e:
            typer.echo(f"Error: Failed to fetch transactions: {e}", err=True)
            raise typer.Exit(1)

        if not transactions:
            typer.echo("No transactions found for the specified criteria.")
            return

        # Fetch account balances
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
            typer.echo(f"Extracted balances for {len(account_balances)} accounts")
        except Exception as e:
            typer.echo(f"Warning: Failed to fetch account balances: {e}", err=True)
            account_balances = {}

        # Convert to Beancount format
        typer.echo("Converting to Beancount format...")
        converter = BeancountConverter()

        if single_file:
            # Single file output
            output_file = get_output_file_path(dest_path, single_file)

            beancount_content = converter.convert_transactions(
                transactions, transaction_accounts, categories, account_balances
            )

            typer.echo("Writing to file...")
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(beancount_content)
                typer.echo(
                    f"Successfully wrote {len(transactions)} transactions to: {output_file}"
                )
            except Exception as e:
                typer.echo(f"Error: Failed to write file: {e}", err=True)
                raise typer.Exit(1)
        else:
            # Hierarchical file structure
            create_hierarchical_structure(dest_path)

            writer = BeancountFileWriter(str(dest_path))

            typer.echo("Using hierarchical file structure...")
            try:
                written_files = writer.write_hierarchical_beancount_files(
                    transactions,
                    transaction_accounts,
                    categories,
                    account_balances,
                    converter,
                )

                typer.echo(
                    f"Successfully wrote {len(transactions)} transactions to hierarchical structure:"
                )
                for relative_path in sorted(written_files.keys()):
                    typer.echo(f"  {relative_path}")
                typer.echo(f"Output directory: {dest_path}")
            except Exception as e:
                typer.echo(f"Error: Failed to write hierarchical files: {e}", err=True)
                raise typer.Exit(1)

        typer.echo("Clone completed successfully!")

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
