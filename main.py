"""Main CLI entry point for PocketSmith to Beancount converter."""

import typer
from pathlib import Path
from typing import Optional, List

from src.cli.clone import clone_command
from src.cli.pull import pull_command
from src.cli.diff import diff_command
from src.cli.push import push_command
from src.cli.common import handle_default_destination, transaction_id_option
from src.cli.date_options import DateOptions

# Create the main typer app
app = typer.Typer(
    name="peabody",
    help="PocketSmith to Beancount converter with intelligent rules and synchronization",
    no_args_is_help=True,
)


@app.command()
def help() -> None:
    """List all available subcommands."""
    typer.echo("Available commands:")
    typer.echo("")
    typer.echo(
        "  clone   Download PocketSmith transactions and write them to beancount format"
    )
    typer.echo("  pull    Update local Beancount ledger with recent PocketSmith data")
    typer.echo("  diff    Compare local beancount ledger with remote PocketSmith data")
    typer.echo("  push    Upload local changes to PocketSmith")
    typer.echo("  rule    Manage transaction processing rules")
    typer.echo("  help    Show this help message")
    typer.echo("")
    typer.echo("Use 'peabody COMMAND --help' for detailed help on any command.")


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
    quiet: bool = typer.Option(
        False, "-q", "--quiet", help="Suppress informational output"
    ),
    from_date: Optional[str] = typer.Option(
        None,
        "--from",
        help="Start date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)",
        hidden=True,
    ),
    to_date: Optional[str] = typer.Option(
        None,
        "--to",
        help="End date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)",
        hidden=True,
    ),
    this_month: bool = typer.Option(
        False,
        "--this-month",
        help="Download transactions from current calendar month",
        hidden=True,
    ),
    last_month: bool = typer.Option(
        False,
        "--last-month",
        help="Download transactions from previous calendar month",
        hidden=True,
    ),
    this_year: bool = typer.Option(
        False,
        "--this-year",
        help="Download transactions from current calendar year",
        hidden=True,
    ),
    last_year: bool = typer.Option(
        False,
        "--last-year",
        help="Download transactions from previous calendar year",
        hidden=True,
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
    destination = handle_default_destination(destination)

    date_options = DateOptions(
        from_date=from_date,
        to_date=to_date,
        this_month=this_month,
        last_month=last_month,
        this_year=this_year,
        last_year=last_year,
    )

    clone_command(
        destination=destination,
        single_file=single_file,
        date_options=date_options,
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
    transaction_id: Optional[str] = transaction_id_option(),
    from_date: Optional[str] = typer.Option(
        None,
        "--from",
        help="Start date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)",
        hidden=True,
    ),
    to_date: Optional[str] = typer.Option(
        None,
        "--to",
        help="End date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)",
        hidden=True,
    ),
    this_month: bool = typer.Option(
        False,
        "--this-month",
        help="Pull transactions from current calendar month",
        hidden=True,
    ),
    last_month: bool = typer.Option(
        False,
        "--last-month",
        help="Pull transactions from previous calendar month",
        hidden=True,
    ),
    this_year: bool = typer.Option(
        False,
        "--this-year",
        help="Pull transactions from current calendar year",
        hidden=True,
    ),
    last_year: bool = typer.Option(
        False,
        "--last-year",
        help="Pull transactions from previous calendar year",
        hidden=True,
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
    destination = handle_default_destination(destination)

    date_options = DateOptions(
        from_date=from_date,
        to_date=to_date,
        this_month=this_month,
        last_month=last_month,
        this_year=this_year,
        last_year=last_year,
    )

    pull_command(
        destination=destination,
        verbose=verbose,
        date_options=date_options,
        dry_run=dry_run,
        quiet=quiet,
        transaction_id=transaction_id,
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
    transaction_id: Optional[str] = transaction_id_option(),
    from_date: Optional[str] = typer.Option(
        None,
        "--from",
        help="Start date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)",
        hidden=True,
    ),
    to_date: Optional[str] = typer.Option(
        None,
        "--to",
        help="End date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)",
        hidden=True,
    ),
    this_month: bool = typer.Option(
        False,
        "--this-month",
        help="Compare transactions from current calendar month",
        hidden=True,
    ),
    last_month: bool = typer.Option(
        False,
        "--last-month",
        help="Compare transactions from previous calendar month",
        hidden=True,
    ),
    this_year: bool = typer.Option(
        False,
        "--this-year",
        help="Compare transactions from current calendar year",
        hidden=True,
    ),
    last_year: bool = typer.Option(
        False,
        "--last-year",
        help="Compare transactions from previous calendar year",
        hidden=True,
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
    destination = handle_default_destination(destination)

    date_options = DateOptions(
        from_date=from_date,
        to_date=to_date,
        this_month=this_month,
        last_month=last_month,
        this_year=this_year,
        last_year=last_year,
    )

    diff_command(
        destination=destination,
        format=format,
        date_options=date_options,
        transaction_id=transaction_id,
    )


@app.command()
def push(
    destination: Optional[Path] = typer.Argument(
        None,
        help="File or directory to push (defaults to current directory's beancount file)",
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
    transaction_id: Optional[str] = transaction_id_option(),
    from_date: Optional[str] = typer.Option(
        None,
        "--from",
        help="Start date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)",
        hidden=True,
    ),
    to_date: Optional[str] = typer.Option(
        None,
        "--to",
        help="End date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)",
        hidden=True,
    ),
    this_month: bool = typer.Option(
        False,
        "--this-month",
        help="Push transactions from current calendar month",
        hidden=True,
    ),
    last_month: bool = typer.Option(
        False,
        "--last-month",
        help="Push transactions from previous calendar month",
        hidden=True,
    ),
    this_year: bool = typer.Option(
        False,
        "--this-year",
        help="Push transactions from current calendar year",
        hidden=True,
    ),
    last_year: bool = typer.Option(
        False,
        "--last-year",
        help="Push transactions from previous calendar year",
        hidden=True,
    ),
) -> None:
    """Upload local changes to PocketSmith."""
    destination = handle_default_destination(destination)

    date_options = DateOptions(
        from_date=from_date,
        to_date=to_date,
        this_month=this_month,
        last_month=last_month,
        this_year=this_year,
        last_year=last_year,
    )

    push_command(
        destination=destination,
        dry_run=dry_run,
        verbose=verbose,
        quiet=quiet,
        transaction_id=transaction_id,
        date_options=date_options,
    )


# Create rule sub-app
rule_app = typer.Typer(
    name="rule",
    help="Manage transaction processing rules",
    no_args_is_help=True,
)
app.add_typer(rule_app, name="rule")


@rule_app.callback(invoke_without_command=True)
def rule_main(
    ctx: typer.Context,
    if_params: Optional[List[str]] = typer.Option(
        None, "--if", help="Add precondition: key=value"
    ),
    then_params: Optional[List[str]] = typer.Option(
        None, "--then", help="Add transform: key=value"
    ),
    destination: Optional[Path] = typer.Option(
        None,
        "--destination",
        help="File or directory to work with (defaults to current directory's beancount file)",
    ),
    rules: Optional[Path] = typer.Option(
        None,
        "--rules",
        help="Rules file or directory (single .yaml file or directory containing .yaml files)",
    ),
) -> None:
    """Manage transaction processing rules."""
    if ctx.invoked_subcommand is None:
        # If no subcommand provided, show help
        typer.echo(ctx.get_help())

    # Store the options in context for subcommands to use
    ctx.ensure_object(dict)
    ctx.obj["destination"] = destination
    ctx.obj["rules"] = rules


@rule_app.command("add")
def rule_add(
    ctx: typer.Context,
    if_params: List[str] = typer.Option(
        ..., "--if", help="Precondition: key=value (e.g., --if merchant=starbucks)"
    ),
    then_params: List[str] = typer.Option(
        ..., "--then", help="Transform: key=value (e.g., --then category=Dining)"
    ),
) -> None:
    """Add a new transaction processing rule.

    Example:
    peabody rule add --if merchant=starbucks --then category=Dining --then labels=coffee
    """
    from src.cli.rule_commands import rule_add_command

    # Get destination and rules from parent context
    destination = ctx.obj.get("destination") if ctx.obj else None
    rules = ctx.obj.get("rules") if ctx.obj else None

    rule_add_command(if_params, then_params, destination, rules)


@rule_app.command("rm")
def rule_remove(
    ctx: typer.Context,
    rule_id: int = typer.Argument(..., help="Rule ID to remove"),
) -> None:
    """Remove a transaction processing rule."""
    from src.cli.rule_commands import rule_remove_command

    # Get rules from parent context
    rules = ctx.obj.get("rules") if ctx.obj else None

    rule_remove_command(rule_id, rules)


@rule_app.command("apply")
def rule_apply(
    ctx: typer.Context,
    rule_id: int = typer.Argument(..., help="Rule ID to apply"),
    transaction_id: str = typer.Argument(..., help="Transaction ID to apply rule to"),
    dry_run: bool = typer.Option(
        False, "-n", "--dry-run", help="Preview changes without applying them"
    ),
) -> None:
    """Apply a specific rule to a specific transaction."""
    from src.cli.rule_commands import rule_apply_command

    # Get destination and rules from parent context
    destination = ctx.obj.get("destination") if ctx.obj else None
    rules = ctx.obj.get("rules") if ctx.obj else None

    rule_apply_command(rule_id, transaction_id, dry_run, destination, rules)


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
