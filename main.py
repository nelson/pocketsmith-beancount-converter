"""Main CLI entry point for PocketSmith to Beancount converter."""

import typer
from pathlib import Path
from typing import Optional

from src.cli.clone import clone_command
from src.cli.pull import pull_command

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
    quiet: bool = typer.Option(
        False, "-q", "--quiet", help="Suppress informational output"
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
        from_date=from_date,
        to_date=to_date,
        this_month=this_month,
        last_month=last_month,
        this_year=this_year,
        last_year=last_year,
        quiet=quiet,
    )


@app.command()
def pull(
    destination: Path = typer.Argument(..., help="File or directory to update"),
    dry_run: bool = typer.Option(
        False, "-n", "--dry-run", help="Preview changes without applying them"
    ),
    quiet: bool = typer.Option(
        False, "-q", "--quiet", help="Suppress informational output"
    ),
    from_date: Optional[str] = typer.Option(
        None, "--from", help="Start date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)"
    ),
    to_date: Optional[str] = typer.Option(
        None, "--to", help="End date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)"
    ),
    this_month: bool = typer.Option(
        False, "--this-month", help="Pull transactions from current calendar month"
    ),
    last_month: bool = typer.Option(
        False, "--last-month", help="Pull transactions from previous calendar month"
    ),
    this_year: bool = typer.Option(
        False, "--this-year", help="Pull transactions from current calendar year"
    ),
    last_year: bool = typer.Option(
        False, "--last-year", help="Pull transactions from previous calendar year"
    ),
) -> None:
    """Update local Beancount ledger with recent PocketSmith data.

    Updates the local Beancount ledger to the most recent data based on remote
    PocketSmith, fetching any new transactions within the scope of the original clone.

    To avoid fetching unnecessary data, uses the updated_since parameter based on
    the most recent CLONE or PULL entry in the changelog.

    If date options are provided, triggers a second fetch operation with the new
    date ranges.
    """
    pull_command(
        destination=destination,
        from_date=from_date,
        to_date=to_date,
        this_month=this_month,
        last_month=last_month,
        this_year=this_year,
        last_year=last_year,
        dry_run=dry_run,
        quiet=quiet,
    )


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
