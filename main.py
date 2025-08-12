"""Main CLI entry point for PocketSmith to Beancount converter."""

import typer
from pathlib import Path
from typing import Optional

from src.cli.clone import clone_command

# Create the main typer app
app = typer.Typer(
    name="peabody",
    help="PocketSmith to Beancount converter with intelligent rules and synchronization",
    no_args_is_help=True,
)


@app.command()
def clone(
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
    clone_command(
        destination=destination,
        single_file=single_file,
        limit=limit,
        all_transactions=all_transactions,
        from_date=from_date,
        to_date=to_date,
        this_month=this_month,
        last_month=last_month,
        this_year=this_year,
        last_year=last_year,
    )


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
