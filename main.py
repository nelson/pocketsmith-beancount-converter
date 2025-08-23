"""Main CLI entry point for PocketSmith to Beancount converter."""

import typer
from pathlib import Path
from typing import Optional, List

from src.cli.clone import clone_command
from src.cli.pull import pull_command
from src.cli.diff import diff_command
from src.cli.push import push_command
from src.cli.common import (
    handle_default_ledger,
    resolve_config_path,
    transaction_id_option,
)
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
    ledger: Optional[Path] = typer.Argument(
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

    The ledger must not exist and must be in a writable location.
    If no ledger is provided, attempts to find a default beancount file
    in the current directory.
    """
    ledger_path, ledger_source = handle_default_ledger(ledger)
    if not quiet:
        typer.echo(f"Using ledger: {ledger_path} (from {ledger_source})")

    date_options = DateOptions(
        from_date=from_date,
        to_date=to_date,
        this_month=this_month,
        last_month=last_month,
        this_year=this_year,
        last_year=last_year,
    )

    clone_command(
        destination=ledger_path,
        single_file=single_file,
        date_options=date_options,
        quiet=quiet,
    )


@app.command()
def pull(
    ledger: Optional[Path] = typer.Argument(
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

    If no ledger is provided, attempts to find a default beancount file
    in the current directory.
    """
    ledger_path, ledger_source = handle_default_ledger(ledger)
    if not quiet:
        typer.echo(f"Using ledger: {ledger_path} (from {ledger_source})")

    date_options = DateOptions(
        from_date=from_date,
        to_date=to_date,
        this_month=this_month,
        last_month=last_month,
        this_year=this_year,
        last_year=last_year,
    )

    pull_command(
        destination=ledger_path,
        verbose=verbose,
        date_options=date_options,
        dry_run=dry_run,
        quiet=quiet,
        transaction_id=transaction_id,
    )


@app.command()
def diff(
    ledger: Optional[Path] = typer.Argument(
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

    If no ledger is provided, attempts to find a default beancount file
    in the current directory.
    """
    ledger_path, ledger_source = handle_default_ledger(ledger)
    typer.echo(f"Using ledger: {ledger_path} (from {ledger_source})")

    date_options = DateOptions(
        from_date=from_date,
        to_date=to_date,
        this_month=this_month,
        last_month=last_month,
        this_year=this_year,
        last_year=last_year,
    )

    diff_command(
        destination=ledger_path,
        format=format,
        date_options=date_options,
        transaction_id=transaction_id,
    )


@app.command()
def push(
    ledger: Optional[Path] = typer.Argument(
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
    ledger_path, ledger_source = handle_default_ledger(ledger)
    if not quiet:
        typer.echo(f"Using ledger: {ledger_path} (from {ledger_source})")

    date_options = DateOptions(
        from_date=from_date,
        to_date=to_date,
        this_month=this_month,
        last_month=last_month,
        this_year=this_year,
        last_year=last_year,
    )

    push_command(
        destination=ledger_path,
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
    ledger: Optional[Path] = typer.Option(
        None,
        "--ledger",
        help="File or directory to work with (defaults to current directory's beancount file)",
    ),
    rules: Optional[Path] = typer.Option(
        None,
        "--rules",
        help="Rules file or directory (single .yaml file or directory containing .yaml files)",
    ),
) -> None:
    """Manage transaction processing rules."""
    # Load environment variables from .env file
    from dotenv import load_dotenv

    load_dotenv()

    if ctx.invoked_subcommand is None:
        # If no subcommand provided, show help
        typer.echo(ctx.get_help())

    # Resolve configuration paths with environment variable support
    ledger_path, ledger_source = handle_default_ledger(ledger)
    rules_path, rules_source = resolve_config_path(
        rules, "PEABODY_RULES", ".rules/", "rules"
    )

    # Store the resolved options in context for subcommands to use
    ctx.ensure_object(dict)
    ctx.obj["ledger"] = ledger_path
    ctx.obj["ledger_source"] = ledger_source
    ctx.obj["rules"] = rules_path
    ctx.obj["rules_source"] = rules_source


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

    # Get ledger and rules from parent context
    ledger = ctx.obj.get("ledger") if ctx.obj else None
    ledger_source = ctx.obj.get("ledger_source") if ctx.obj else None
    rules = ctx.obj.get("rules") if ctx.obj else None
    rules_source = ctx.obj.get("rules_source") if ctx.obj else None

    # Show config sources
    if ledger_source:
        typer.echo(f"Using ledger: {ledger} (from {ledger_source})")
    if rules_source:
        typer.echo(f"Using rules: {rules} (from {rules_source})")

    rule_add_command(if_params, then_params, ledger, rules)


@rule_app.command("rm")
def rule_remove(
    ctx: typer.Context,
    rule_id: int = typer.Argument(..., help="Rule ID to remove"),
) -> None:
    """Remove a transaction processing rule."""
    from src.cli.rule_commands import rule_remove_command

    # Get rules from parent context
    rules = ctx.obj.get("rules") if ctx.obj else None
    rules_source = ctx.obj.get("rules_source") if ctx.obj else None

    # Show config source
    if rules_source:
        typer.echo(f"Using rules: {rules} (from {rules_source})")

    rule_remove_command(rule_id, rules)


@rule_app.command("apply")
def rule_apply(
    ctx: typer.Context,
    ruleset: Optional[str] = typer.Argument(
        None,
        help="Rule set to apply: numeric IDs (1,3-5), wildcards (1x, 3xxx), or YAML file (rules.yaml)",
    ),
    dry_run: bool = typer.Option(
        False, "-n", "--dry-run", help="Preview changes without applying them"
    ),
    from_date: Optional[str] = typer.Option(
        None,
        "--from",
        help="Start date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)",
    ),
    to_date: Optional[str] = typer.Option(
        None,
        "--to",
        help="End date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)",
    ),
    this_month: bool = typer.Option(
        False,
        "--this-month",
        help="Process transactions from current calendar month",
    ),
    last_month: bool = typer.Option(
        False,
        "--last-month",
        help="Process transactions from previous calendar month",
    ),
    this_year: bool = typer.Option(
        False,
        "--this-year",
        help="Process transactions from current calendar year",
    ),
    last_year: bool = typer.Option(
        False,
        "--last-year",
        help="Process transactions from previous calendar year",
    ),
    ledgerset: Optional[str] = typer.Option(
        None,
        "--ledgerset",
        help="File or directory relative to ledger to limit transaction processing to",
    ),
    verbose: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        help="Show detailed matching results for each transaction",
    ),
    experimental_continue: bool = typer.Option(
        False,
        "--experimental-continue",
        help="Show experimental transaction matching output format",
    ),
) -> None:
    """Apply rules to transactions.

    If ruleset is not provided, all rules will be eligible for evaluation.

    Ruleset can be:
    - Numeric IDs: 1,3-5,9-11 (individual IDs, ranges, or combinations)
    - Wildcards: 1x (10-19), 3x (3000-3999), 25x (250-259)
    - YAML files: rules.yaml (all rules from that file)
    """
    from src.cli.rule_commands import rule_apply_command

    # Get ledger and rules from parent context
    ledger = ctx.obj.get("ledger") if ctx.obj else None
    ledger_source = ctx.obj.get("ledger_source") if ctx.obj else None
    rules = ctx.obj.get("rules") if ctx.obj else None
    rules_source = ctx.obj.get("rules_source") if ctx.obj else None

    # Show config sources
    if ledger_source:
        typer.echo(f"Using ledger: {ledger} (from {ledger_source})")
    if rules_source:
        typer.echo(f"Using rules: {rules} (from {rules_source})")

    # Create DateOptions object
    from src.cli.date_options import DateOptions

    date_options = DateOptions(
        from_date=from_date,
        to_date=to_date,
        this_month=this_month,
        last_month=last_month,
        this_year=this_year,
        last_year=last_year,
    )

    rule_apply_command(
        ruleset=ruleset,
        dry_run=dry_run,
        ledger=ledger,
        rules_path=rules,
        date_options=date_options,
        ledgerset=ledgerset,
        verbose=verbose,
        experimental_continue=experimental_continue,
    )


@rule_app.command("list")
def rule_list(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False, "-v", "--verbose", help="Show detailed rule information"
    ),
    rule_id: Optional[str] = typer.Option(
        None, "--id", help="Filter by rule ID(s) - supports ranges like '1,3-5,7'"
    ),
) -> None:
    """List all rules found.

    By default, shows a summary with rule counts by file and category.
    Use --verbose to see full rule details.
    """
    from src.cli.rule_commands import rule_list_command

    # Get rules from parent context
    rules = ctx.obj.get("rules") if ctx.obj else None
    rules_source = ctx.obj.get("rules_source") if ctx.obj else None

    # Show config source
    if rules_source:
        typer.echo(f"Using rules: {rules} (from {rules_source})")

    rule_list_command(verbose, rule_id, rules)


@rule_app.command("lookup")
def rule_lookup(
    ctx: typer.Context,
    merchant: Optional[str] = typer.Option(
        None, "--merchant", help="Transaction merchant/payee to match"
    ),
    category: Optional[str] = typer.Option(
        None, "--category", help="Transaction category to match"
    ),
    account: Optional[str] = typer.Option(
        None, "--account", help="Transaction account to match"
    ),
) -> None:
    """Look up which rule would match given transaction data.

    At least one of --merchant, --category, or --account must be provided.
    """
    from src.cli.rule_commands import rule_lookup_command

    # Get rules from parent context
    rules = ctx.obj.get("rules") if ctx.obj else None
    rules_source = ctx.obj.get("rules_source") if ctx.obj else None

    # Show config source
    if rules_source:
        typer.echo(f"Using rules: {rules} (from {rules_source})")

    rule_lookup_command(merchant, category, account, rules)


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
