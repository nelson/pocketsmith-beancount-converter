"""Main CLI entry point for PocketSmith to Beancount converter."""

import typer
from pathlib import Path
from typing import Optional

from src.cli.clone import clone_command
from src.cli.pull import pull_command
from src.cli.diff import diff_command
from src.cli.file_handler import find_default_beancount_file, FileHandlerError

# Create the main typer app
app = typer.Typer(
    name="peabody",
    help="PocketSmith to Beancount converter with intelligent rules and synchronization",
    no_args_is_help=True,
)


@app.command()
def clone(
    destination: Optional[Path] = typer.Argument(
        None,
        help="Output file or directory path (defaults to current directory's beancount file)",
    ),
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
    If no destination is provided, attempts to find a default beancount file
    in the current directory.
    """
    # Handle default destination
    if destination is None:
        try:
            destination = find_default_beancount_file()
        except FileHandlerError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)

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
    destination: Optional[Path] = typer.Argument(
        None,
        help="File or directory to update (defaults to current directory's beancount file)",
    ),
    dry_run: bool = typer.Option(
        False, "-n", "--dry-run", help="Preview changes without applying them"
    ),
    verbose: bool = typer.Option(
        False, "-v", "--verbose", help="Show detailed update information"
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

    If no destination is provided, attempts to find a default beancount file
    in the current directory.
    """
    # Handle default destination
    if destination is None:
        try:
            destination = find_default_beancount_file()
        except FileHandlerError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)

    pull_command(
        destination=destination,
        verbose=verbose,
        from_date=from_date,
        to_date=to_date,
        this_month=this_month,
        last_month=last_month,
        this_year=this_year,
        last_year=last_year,
        dry_run=dry_run,
        quiet=quiet,
    )


@app.command()
def diff(
    destination: Optional[Path] = typer.Argument(
        None,
        help="File or directory to compare (defaults to current directory's beancount file)",
    ),
    format: str = typer.Option(
        "summary",
        "--format",
        help="Output format: summary, ids, changelog, or diff",
    ),
    from_date: Optional[str] = typer.Option(
        None, "--from", help="Start date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)"
    ),
    to_date: Optional[str] = typer.Option(
        None, "--to", help="End date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)"
    ),
    this_month: bool = typer.Option(
        False, "--this-month", help="Compare transactions from current calendar month"
    ),
    last_month: bool = typer.Option(
        False, "--last-month", help="Compare transactions from previous calendar month"
    ),
    this_year: bool = typer.Option(
        False, "--this-year", help="Compare transactions from current calendar year"
    ),
    last_year: bool = typer.Option(
        False, "--last-year", help="Compare transactions from previous calendar year"
    ),
) -> None:
    """Compare local beancount ledger with remote PocketSmith data.

    Print information about the differences between local and remote transaction data.
    The purpose is to understand which transactions will be changed on remote if
    the push command is issued.

    Never modifies the local ledger, changelog, or remote data.

    If no destination is provided, attempts to find a default beancount file
    in the current directory.
    """
    # Handle default destination
    if destination is None:
        try:
            destination = find_default_beancount_file()
        except FileHandlerError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)

    diff_command(
        destination=destination,
        format=format,
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
