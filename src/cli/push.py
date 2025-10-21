"""Push command implementation for writing local changes to PocketSmith."""

from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import typer
from dotenv import load_dotenv

from .date_parser import DateParseError
from .validators import validate_date_options, ValidationError
from .date_options import DateOptions
from .changelog import ChangelogManager, determine_changelog_path
from .shared_utils import choose_date_range, apply_ledgerset_filtering

from ..pocketsmith.common import PocketSmithClient

# Reuse diff local reader
from .diff import read_local_transactions, determine_single_file_mode, DiffComparator


def _build_updates_from_changes(changes: List[Tuple[str, str, str]]) -> Dict[str, Any]:
    """Create a field update mapping from detected changes.

    Input is list of (field, local_value, remote_value). Use local_value.
    """
    updates: Dict[str, Any] = {}
    ALLOWED_FIELDS = {"note", "memo", "labels", "tags", "category_id"}

    for field, local_val, _remote_val in changes:
        key = field
        value: Any = local_val

        # Normalize field names for API
        if field.lower() == "category":
            key = "category_id"
            # local_val may be a JSON string; keep as-is if numeric-like
            try:
                value = int(str(local_val)) if local_val is not None else None
            except ValueError:
                # Leave as string; API will reject if invalid
                value = local_val
        elif field.lower() in ("labels",):
            # Expect JSON-encoded array strings from comparator; try to eval via json
            import json

            try:
                parsed = (
                    json.loads(local_val) if isinstance(local_val, str) else local_val
                )
                value = parsed
            except Exception:
                value = local_val

        # Only include allowed/writable fields
        if key in ALLOWED_FIELDS:
            updates[key] = value

    return updates


def push_command(
    destination: Path,
    date_options: Optional[DateOptions] = None,
    dry_run: bool = False,
    verbose: bool = False,
    quiet: bool = False,
    transaction_id: Optional[str] = None,
    ledgerset: Optional[str] = None,
) -> None:
    """Upload local changes to PocketSmith.

    Performs an internal diff and writes differing fields back to remote. Uses
    local-preferred resolution for category during push.
    """
    load_dotenv()

    if date_options is None:
        date_options = DateOptions()

    try:
        # Validate date options
        validate_date_options(
            date_options.from_date,
            date_options.to_date,
            date_options.this_month,
            date_options.last_month,
            date_options.this_year,
            date_options.last_year,
        )

        # Check destination
        if not destination.exists():
            typer.echo(f"Error: Destination does not exist: {destination}", err=True)
            raise typer.Exit(1)

        # Determine single-file/hierarchical
        single_file = determine_single_file_mode(destination)

        # Prepare changelog
        changelog_path = determine_changelog_path(destination, single_file)
        changelog = ChangelogManager(changelog_path)

        # Connect to API
        try:
            client = PocketSmithClient()
            client.get_user()
        except Exception as e:
            typer.echo(f"Error: Failed to connect to PocketSmith API: {e}", err=True)
            raise typer.Exit(1)

        # Determine date range
        from_date_str, to_date_str = choose_date_range(changelog, date_options)

        # Fetch transactions
        transactions: List[Dict[str, Any]] = []
        if transaction_id:
            try:
                txn = client.get_transaction(int(transaction_id))
                transactions = [txn]
            except Exception as e:
                typer.echo(
                    f"Error: Failed to fetch transaction {transaction_id}: {e}",
                    err=True,
                )
                raise typer.Exit(1)
        else:
            try:
                transactions = client.get_transactions(
                    start_date=from_date_str,
                    end_date=to_date_str,
                )
            except Exception as e:
                typer.echo(f"Error: Failed to fetch transactions: {e}", err=True)
                raise typer.Exit(1)

        # Read local transactions
        local_transactions = read_local_transactions(destination, single_file)

        # Apply ledgerset filtering if specified
        if ledgerset:
            local_transactions = apply_ledgerset_filtering(
                local_transactions, ledgerset, destination
            )

        # Diff local vs remote
        comparator = DiffComparator()
        comparator.compare_for_diff(local_transactions, transactions)

        # Log PUSH header (skip in dry-run)
        if not dry_run:
            changelog.write_push_entry(from_date_str, to_date_str)

        # For each differing txn, build updates and write back
        total_updates = 0
        for diff in comparator.differences:
            txn_id = diff["id"]
            changes = diff["changes"]  # List of (field, local, remote)

            # Favor local category: ensure category change included if present
            updates = _build_updates_from_changes(changes)
            if not updates:
                continue

            # Write to API
            success = client.update_transaction(txn_id, updates, dry_run=dry_run)
            if success:
                total_updates += 1
                # Log updates for applied fields only (skip in dry-run)
                if not dry_run:
                    applied_fields = set(updates.keys())
                    for field, local_val, remote_val in changes:
                        # Map 'category' to 'category_id' for comparison
                        mapped_field = (
                            "category_id" if field.lower() == "category" else field
                        )
                        if mapped_field in applied_fields:
                            changelog.write_update_entry(
                                txn_id, mapped_field, str(remote_val), str(local_val)
                            )
                # Verbose output for applied fields
                if verbose:
                    applied_fields = set(updates.keys())
                    for field, local_val, remote_val in changes:
                        mapped_field = (
                            "category_id" if field.lower() == "category" else field
                        )
                        if mapped_field in applied_fields:
                            typer.echo(
                                f"UPDATE {txn_id} {mapped_field} {remote_val} → {local_val}"
                            )

        # Summary
        if not quiet:
            if dry_run:
                typer.echo(
                    f"Changelog {changelog_path} not updated (due to --dry-run)."
                )
            else:
                typer.echo(f"Changelog {changelog_path} updated.")

            typer.echo(f"{len(transactions)} existing transactions were checked.")
            typer.echo(
                f"{len(comparator.differences)} transactions differed; {total_updates} updated."
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
