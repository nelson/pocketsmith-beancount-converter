"""Apply transfer detection results to transactions."""

from typing import List, Dict, Any
from pathlib import Path

from .models import DetectionResult
from ..compare.model import Transaction
from ..beancount.read import read_ledger
from ..beancount.write import convert_transaction_to_beancount
from beancount.core import data as bc_data


class TransferApplier:
    """Applies transfer detection results to beancount ledger."""

    def __init__(self, transfer_category_id: int):
        """Initialize with the Transfer category ID from PocketSmith.

        Args:
            transfer_category_id: PocketSmith ID for Expenses:Transfer category
        """
        self.transfer_category_id = transfer_category_id

    def apply_to_transactions(
        self,
        result: DetectionResult,
        transactions: List[Transaction]
    ) -> List[Transaction]:
        """Apply transfer markings to transaction list.

        Args:
            result: Detection result with confirmed/suspected pairs
            transactions: List of transactions to modify

        Returns:
            Modified list of transactions
        """
        # Create lookup by transaction ID
        tx_by_id = {tx.id: tx for tx in transactions}

        # Apply confirmed transfers
        for pair in result.confirmed_pairs:
            source_tx = tx_by_id.get(pair.source_id)
            dest_tx = tx_by_id.get(pair.dest_id)

            if source_tx and dest_tx:
                # Mark both as transfers
                source_tx.is_transfer = True
                source_tx.paired = int(dest_tx.id)
                source_tx.suspect_reason = None

                dest_tx.is_transfer = True
                dest_tx.paired = int(source_tx.id)
                dest_tx.suspect_reason = None

                # Update category to Transfer for confirmed
                if source_tx.category:
                    source_tx.category = {
                        "id": self.transfer_category_id,
                        "title": "Transfer",
                        "is_transfer": True
                    }
                if dest_tx.category:
                    dest_tx.category = {
                        "id": self.transfer_category_id,
                        "title": "Transfer",
                        "is_transfer": True
                    }

        # Apply suspected transfers
        for pair in result.suspected_pairs:
            source_tx = tx_by_id.get(pair.source_id)
            dest_tx = tx_by_id.get(pair.dest_id)

            if source_tx and dest_tx:
                # Mark as paired but not is_transfer
                source_tx.is_transfer = False
                source_tx.paired = int(dest_tx.id)
                source_tx.suspect_reason = pair.reason

                dest_tx.is_transfer = False
                dest_tx.paired = int(source_tx.id)
                dest_tx.suspect_reason = pair.reason

                # Keep original category for suspected transfers

        return transactions

    def apply_to_ledger(
        self,
        result: DetectionResult,
        ledger_path: Path,
        in_place: bool = True
    ) -> None:
        """Apply transfer markings directly to beancount ledger files.

        Args:
            result: Detection result with confirmed/suspected pairs
            ledger_path: Path to ledger (file or directory with main.beancount)
            in_place: If True, modify files in place (like rule apply)
        """
        # Read ledger
        if ledger_path.is_file():
            main_file = ledger_path
        else:
            main_file = ledger_path / "main.beancount"

        entries, errors, options = read_ledger(str(main_file))

        # Build transaction lookup by ID
        tx_entries_by_id: Dict[str, bc_data.Transaction] = {}
        for entry in entries:
            if isinstance(entry, bc_data.Transaction):
                tx_id = entry.meta.get("id")
                if tx_id is not None:
                    tx_entries_by_id[str(tx_id)] = entry

        # Apply confirmed transfers
        updated_entries = []  # Track which entries were updated and their new versions
        for pair in result.confirmed_pairs:
            source_entry = tx_entries_by_id.get(pair.source_id)
            dest_entry = tx_entries_by_id.get(pair.dest_id)

            if source_entry and dest_entry:
                # Update metadata for both transactions
                from ..beancount.common import convert_id_to_decimal

                source_entry.meta["is_transfer"] = "true"
                # Store paired as Decimal for beancount compatibility
                paired_dest = convert_id_to_decimal(pair.dest_id)
                if paired_dest is not None:
                    source_entry.meta["paired"] = paired_dest
                if "suspect_reason" in source_entry.meta:
                    del source_entry.meta["suspect_reason"]

                dest_entry.meta["is_transfer"] = "true"
                # Store paired as Decimal for beancount compatibility
                paired_source = convert_id_to_decimal(pair.source_id)
                if paired_source is not None:
                    dest_entry.meta["paired"] = paired_source
                if "suspect_reason" in dest_entry.meta:
                    del dest_entry.meta["suspect_reason"]

                # Update category account in postings for confirmed transfers
                new_source = self._update_postings_to_transfer(source_entry)
                new_dest = self._update_postings_to_transfer(dest_entry)

                # Track the replacements
                updated_entries.append((source_entry, new_source))
                updated_entries.append((dest_entry, new_dest))

                # Update the lookup table
                tx_entries_by_id[pair.source_id] = new_source
                tx_entries_by_id[pair.dest_id] = new_dest

        # Apply suspected transfers
        for pair in result.suspected_pairs:
            source_entry = tx_entries_by_id.get(pair.source_id)
            dest_entry = tx_entries_by_id.get(pair.dest_id)

            if source_entry and dest_entry:
                # Update metadata but don't set is_transfer
                from ..beancount.common import convert_id_to_decimal

                # Store paired as Decimal for beancount compatibility
                paired_dest = convert_id_to_decimal(pair.dest_id)
                if paired_dest is not None:
                    source_entry.meta["paired"] = paired_dest
                source_entry.meta["suspect_reason"] = pair.reason or ""
                if "is_transfer" in source_entry.meta:
                    del source_entry.meta["is_transfer"]

                # Store paired as Decimal for beancount compatibility
                paired_source = convert_id_to_decimal(pair.source_id)
                if paired_source is not None:
                    dest_entry.meta["paired"] = paired_source
                dest_entry.meta["suspect_reason"] = pair.reason or ""
                if "is_transfer" in dest_entry.meta:
                    del dest_entry.meta["is_transfer"]

        # Replace old entries with updated ones in the entries list
        if updated_entries:
            old_to_new = {id(old): new for old, new in updated_entries}
            entries = [old_to_new.get(id(e), e) for e in entries]

        # Write back to files (in-place modification)
        if in_place:
            self._write_entries_to_files(entries, ledger_path)

    def _update_postings_to_transfer(self, entry: bc_data.Transaction) -> bc_data.Transaction:
        """Update transaction postings to use Expenses:Transfer category.

        Args:
            entry: Beancount transaction entry to modify

        Returns:
            New transaction with updated postings
        """
        from beancount.core.amount import Amount

        new_postings = []
        for posting in entry.postings:
            # Replace Expenses:* or Income:* accounts with Expenses:Transfer
            if posting.account.startswith(("Expenses:", "Income:")):
                new_posting = posting._replace(account="Expenses:Transfer")
                new_postings.append(new_posting)
            else:
                new_postings.append(posting)

        # Return new transaction with replaced postings
        return entry._replace(postings=new_postings)

    def _write_entries_to_files(
        self,
        entries: List[Any],
        ledger_path: Path
    ) -> None:
        """Write modified entries back to their source files.

        Args:
            entries: List of beancount entries to write
            ledger_path: Base ledger path (file or directory)
        """
        from beancount.parser import printer
        from collections import defaultdict
        from datetime import datetime

        # Group transactions by their source file
        # Only include Transaction entries, skip Open/Commodity/etc from main.beancount
        entries_by_file: Dict[str, List[Any]] = defaultdict(list)

        for entry in entries:
            if isinstance(entry, bc_data.Transaction) and hasattr(entry, "meta") and "filename" in entry.meta:
                source_file = entry.meta["filename"]
                # Skip main.beancount - only write monthly files
                if not source_file.endswith("main.beancount"):
                    entries_by_file[source_file].append(entry)

        # Write each file
        for filepath, file_entries in entries_by_file.items():
            path = Path(filepath)

            # Sort entries by date
            sorted_entries = sorted(
                file_entries,
                key=lambda e: (
                    getattr(e, "date", datetime.min.date()),
                    getattr(e, "meta", {}).get("lineno", 0)
                )
            )

            # Generate beancount content
            content_lines = []

            # Add header if it's a monthly file
            if path.stem.count("-") == 1:  # Format: YYYY-MM
                year_month = path.stem
                try:
                    year, month = year_month.split("-")
                    month_name = datetime(int(year), int(month), 1).strftime("%B %Y")
                    content_lines.append(f"; Transactions for {month_name}")
                    content_lines.append(
                        f"; Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    content_lines.append("")
                except (ValueError, IndexError):
                    pass

            # Write each entry
            for entry in sorted_entries:
                entry_str = printer.format_entry(entry)
                content_lines.append(entry_str)
                content_lines.append("")  # Blank line between entries

            # Write to file
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(content_lines))
