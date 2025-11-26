"""Transfer detection and management commands for the CLI."""

from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

from ..transfers.detector import TransferDetector
from ..transfers.models import DetectionCriteria
from ..transfers.applier import TransferApplier
from ..transfers.category_helper import find_transfer_category_id
from ..beancount.read import read_ledger
from ..compare.beancount import convert_beancount_list_to_model
from beancount.core import data as bc_data


def detect_transfers_command(
    ledger: Optional[Path] = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    """Detect and mark transfer transactions in the ledger.

    Analyzes transactions to find matching pairs that represent transfers
    between accounts. Marks confirmed transfers with is_transfer=true and
    suspected transfers with paired metadata.

    Args:
        ledger: Path to ledger (file or directory)
        dry_run: If True, show what would be marked without modifying files
        verbose: Show detailed detection information
    """
    load_dotenv()

    try:
        # Determine ledger path
        from .common import handle_default_ledger

        ledger_path, ledger_source = handle_default_ledger(ledger)
        typer.echo(f"Using ledger: {ledger_path} (from {ledger_source})")

        # Find Transfer category ID
        transfer_category_id = find_transfer_category_id(ledger_path)
        if transfer_category_id is None:
            typer.echo(
                "Error: Could not find Expenses:Transfer category in ledger",
                err=True,
            )
            typer.echo(
                "Make sure your ledger has an 'Expenses:Transfer' account with an ID",
                err=True,
            )
            raise typer.Exit(1)

        if verbose:
            typer.echo(f"Found Transfer category ID: {transfer_category_id}")

        # Read transactions from ledger
        if ledger_path.is_file():
            main_file = ledger_path
        else:
            main_file = ledger_path / "main.beancount"

        if not main_file.exists():
            typer.echo(f"Error: Ledger file not found: {main_file}", err=True)
            raise typer.Exit(1)

        typer.echo(f"Reading transactions from {main_file}...")
        entries, errors, options = read_ledger(str(main_file))

        if errors:
            typer.echo(
                f"Warning: {len(errors)} errors while reading ledger", err=True
            )

        # Convert to Transaction model
        beancount_txns = [e for e in entries if isinstance(e, bc_data.Transaction)]
        transactions = convert_beancount_list_to_model(
            [
                {
                    "id": e.meta.get("id"),
                    "date": e.date.isoformat(),
                    "payee": e.payee or "",
                    "narration": e.narration or "",
                    "postings": [
                        {
                            "account": p.account,
                            "units": {
                                "number": float(p.units.number)
                                if p.units and p.units.number
                                else 0,
                                "currency": p.units.currency if p.units else "USD",
                            },
                        }
                        for p in e.postings
                    ],
                    "tags": list(e.tags) if e.tags else [],
                    "flag": e.flag,
                    "is_transfer": e.meta.get("is_transfer"),
                    "paired": e.meta.get("paired"),
                    "suspect_reason": e.meta.get("suspect_reason"),
                }
                for e in beancount_txns
                if e.meta.get("id") is not None
            ]
        )

        typer.echo(f"Loaded {len(transactions)} transactions")

        # Run detection
        typer.echo("\nDetecting transfers...")
        criteria = DetectionCriteria()
        detector = TransferDetector(criteria)
        result = detector.detect_transfers(transactions)

        # Print results
        typer.echo("\n" + "=" * 60)
        typer.echo("TRANSFER DETECTION RESULTS")
        typer.echo("=" * 60)
        typer.echo(f"\nConfirmed transfers: {len(result.confirmed_pairs)}")
        typer.echo(f"Suspected transfers: {len(result.suspected_pairs)}")
        typer.echo(f"Unmatched transactions: {len(result.unmatched_transactions)}")

        # Show confirmed pairs
        if result.confirmed_pairs:
            typer.echo("\n" + "-" * 60)
            typer.echo("CONFIRMED TRANSFERS:")
            typer.echo("-" * 60)
            for pair in result.confirmed_pairs:
                source_tx = pair.source_transaction
                dest_tx = pair.dest_transaction
                typer.echo(
                    f"\n  {source_tx.id} → {dest_tx.id}  "
                    f"({pair.amount} {source_tx.currency_code})"
                )
                typer.echo(f"    Source: {source_tx.date} {source_tx.payee}")
                typer.echo(f"    Dest:   {dest_tx.date} {dest_tx.payee}")
                if source_tx.account:
                    typer.echo(f"    From:   {source_tx.account.get('name')}")
                if dest_tx.account:
                    typer.echo(f"    To:     {dest_tx.account.get('name')}")

        # Show suspected pairs
        if result.suspected_pairs:
            typer.echo("\n" + "-" * 60)
            typer.echo("SUSPECTED TRANSFERS:")
            typer.echo("-" * 60)
            for pair in result.suspected_pairs:
                source_tx = pair.source_transaction
                dest_tx = pair.dest_transaction
                typer.echo(
                    f"\n  {source_tx.id} ⇢ {dest_tx.id}  "
                    f"({pair.amount} {source_tx.currency_code})"
                )
                typer.echo(f"    Reason: {pair.reason}")
                typer.echo(f"    Source: {source_tx.date} {source_tx.payee}")
                typer.echo(f"    Dest:   {dest_tx.date} {dest_tx.payee}")
                if source_tx.account:
                    typer.echo(f"    From:   {source_tx.account.get('name')}")
                if dest_tx.account:
                    typer.echo(f"    To:     {dest_tx.account.get('name')}")

        # Apply changes
        if not dry_run:
            if result.confirmed_pairs or result.suspected_pairs:
                typer.echo("\n" + "=" * 60)
                typer.echo("APPLYING CHANGES TO LEDGER...")
                typer.echo("=" * 60)

                applier = TransferApplier(transfer_category_id)
                applier.apply_to_ledger(result, ledger_path, in_place=True)

                typer.echo("\n✓ Transfer metadata written to ledger files")
                typer.echo(
                    f"  • {len(result.confirmed_pairs)} confirmed transfers marked"
                )
                typer.echo(
                    f"  • {len(result.suspected_pairs)} suspected transfers flagged"
                )
            else:
                typer.echo("\nNo transfers detected. No changes made.")
        else:
            typer.echo("\n(Dry run - no changes applied)")

    except Exception as e:
        typer.echo(f"Error detecting transfers: {e}", err=True)
        import traceback

        traceback.print_exc()
        raise typer.Exit(1)


def clear_transfers_command(
    ledger: Optional[Path] = None,
    dry_run: bool = False,
) -> None:
    """Clear all transfer metadata from the ledger.

    Removes is_transfer, paired, and suspect_reason metadata from all
    transactions. Useful for re-running detection with different criteria.

    Args:
        ledger: Path to ledger (file or directory)
        dry_run: If True, show what would be cleared without modifying files
    """
    load_dotenv()

    try:
        # Determine ledger path
        from .common import handle_default_ledger

        ledger_path, ledger_source = handle_default_ledger(ledger)
        typer.echo(f"Using ledger: {ledger_path} (from {ledger_source})")

        # Read transactions from ledger
        if ledger_path.is_file():
            main_file = ledger_path
        else:
            main_file = ledger_path / "main.beancount"

        if not main_file.exists():
            typer.echo(f"Error: Ledger file not found: {main_file}", err=True)
            raise typer.Exit(1)

        typer.echo(f"Reading transactions from {main_file}...")
        entries, errors, options = read_ledger(str(main_file))

        if errors:
            typer.echo(
                f"Warning: {len(errors)} errors while reading ledger", err=True
            )

        # Count and clear transfer metadata
        cleared_count = 0
        for entry in entries:
            if isinstance(entry, bc_data.Transaction):
                has_metadata = False

                if "is_transfer" in entry.meta:
                    has_metadata = True
                    if not dry_run:
                        del entry.meta["is_transfer"]

                if "paired" in entry.meta:
                    has_metadata = True
                    if not dry_run:
                        del entry.meta["paired"]

                if "suspect_reason" in entry.meta:
                    has_metadata = True
                    if not dry_run:
                        del entry.meta["suspect_reason"]

                if has_metadata:
                    cleared_count += 1

        typer.echo(f"\nFound {cleared_count} transactions with transfer metadata")

        if not dry_run and cleared_count > 0:
            typer.echo("\nClearing metadata and writing files...")

            # Write back to files
            from ..transfers.applier import TransferApplier

            applier = TransferApplier(0)  # Category ID not needed for clearing
            applier._write_entries_to_files(entries, ledger_path)

            typer.echo(f"✓ Cleared transfer metadata from {cleared_count} transactions")
        else:
            if dry_run:
                typer.echo("\n(Dry run - no changes applied)")
            else:
                typer.echo("\nNo transfer metadata found. Nothing to clear.")

    except Exception as e:
        typer.echo(f"Error clearing transfers: {e}", err=True)
        raise typer.Exit(1)
