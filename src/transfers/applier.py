"""Apply transfer detection results to transactions."""

from typing import Any, Dict, List, Set
from pathlib import Path
from decimal import Decimal

from .models import DetectionResult
from ..compare.model import Transaction
from ..beancount.read import read_ledger
from ..beancount.update import _build_transaction_line_map as build_line_map
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
        self, result: DetectionResult, transactions: List[Transaction]
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
                        "is_transfer": True,
                    }
                if dest_tx.category:
                    dest_tx.category = {
                        "id": self.transfer_category_id,
                        "title": "Transfer",
                        "is_transfer": True,
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
        self, result: DetectionResult, ledger_path: Path, in_place: bool = True
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
            # Only write files that have modified transactions
            if in_place:
                # Get set of modified entry IDs
                modified_entry_ids = {id(new) for old, new in updated_entries}
                self._write_entries_to_files(entries, ledger_path, modified_entry_ids)

    def _update_postings_to_transfer(
        self, entry: bc_data.Transaction
    ) -> bc_data.Transaction:
        """Update transaction postings to use Expenses:Transfer category.

        Args:
            entry: Beancount transaction entry to modify

        Returns:
            New transaction with updated postings
        """

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
        self, entries: List[Any], ledger_path: Path, modified_entry_ids: Set[int]
    ) -> None:
        """Write modified entries back to their source files using text-based updates.

        Args:
            entries: List of beancount entries to write
            ledger_path: Base ledger path (file or directory)
            modified_entry_ids: Set of entry IDs that were modified
        """
        from collections import defaultdict

        # Group transactions by their source file
        # Track which files have modified transactions and which entries are modified
        entries_by_file: Dict[str, List[Any]] = defaultdict(list)
        files_with_modifications: Dict[str, List[Any]] = {}  # file -> modified entries

        for entry in entries:
            if (
                isinstance(entry, bc_data.Transaction)
                and hasattr(entry, "meta")
                and "filename" in entry.meta
            ):
                source_file = entry.meta["filename"]
                # Skip main.beancount - only write monthly files
                if not source_file.endswith("main.beancount"):
                    entries_by_file[source_file].append(entry)
                    # Track if this entry was modified
                    if id(entry) in modified_entry_ids:
                        if source_file not in files_with_modifications:
                            files_with_modifications[source_file] = []
                        files_with_modifications[source_file].append(entry)

        # Only write files that have modifications
        for filepath, modified_entries in files_with_modifications.items():
            path = Path(filepath)

            # Read current file content
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Build map of transaction ID to line numbers
            txn_line_map = build_line_map(lines)

            # Convert modified entries to PocketSmith-style dicts for text generation
            # Sort by line number in reverse order to maintain line indices
            sorted_entries = sorted(
                modified_entries,
                key=lambda e: txn_line_map.get(str(e.meta.get("id")), (0, 0))[0],
                reverse=True,
            )

            # Apply updates
            new_lines = lines[:]
            for entry in sorted_entries:
                tx_id = str(entry.meta.get("id"))
                if tx_id not in txn_line_map:
                    continue

                start_line, end_line = txn_line_map[tx_id]

                # Generate new transaction content from the modified entry
                new_txn_text = self._format_entry_as_text(entry)

                # Build replacement lines
                txn_lines = new_txn_text.split("\n")
                replacement_lines = [line + "\n" for line in txn_lines]

                # Check if original had a blank line at end_line
                original_had_blank = new_lines[end_line].strip() == ""

                # Check if this is not the last line in the file
                not_last_line = end_line < len(new_lines) - 1

                # Add blank line if original had one OR if there's content after this transaction
                if original_had_blank or not_last_line:
                    replacement_lines.append("\n")

                new_lines[start_line : end_line + 1] = replacement_lines

            # Write back
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

    def _format_entry_as_text(self, entry: bc_data.Transaction) -> str:
        """Format a beancount transaction entry as text, preserving ALL details.

        Preserves:
        - Payee and narration
        - All tags and links
        - All metadata fields (not just transfer-related ones)
        - Posting amounts aligned by decimal point

        Args:
            entry: Beancount transaction entry

        Returns:
            Formatted transaction text
        """
        lines: List[str] = []

        # Transaction header: date flag "payee" "narration" tags/links
        date_str = entry.date.strftime("%Y-%m-%d")
        flag = entry.flag or "*"
        payee = entry.payee or ""
        narration = entry.narration or ""

        # Build header line with payee and narration
        header = f'{date_str} {flag} "{payee}" "{narration}"'

        # Add tags (sorted for consistency)
        if entry.tags:
            sorted_tags = sorted(entry.tags)
            header += " " + " ".join(f"#{tag}" for tag in sorted_tags)

        # Add links (sorted for consistency)
        if entry.links:
            sorted_links = sorted(entry.links)
            header += " " + " ".join(f"^{link}" for link in sorted_links)

        lines.append(header)

        # Add metadata (4 spaces, before postings)
        # Preserve ALL metadata fields, not just specific ones
        meta = entry.meta or {}

        # Define the order for known metadata fields
        # Transfer-specific fields should come after standard beancount fields
        known_fields_order = [
            "id",
            "last_modified",
            "closing_balance",
            "is_transfer",
            "paired",
            "suspect_reason",
        ]

        # Internal beancount metadata to skip
        skip_fields = {"filename", "lineno", "__tolerances__"}

        # First, add known fields in order
        for field in known_fields_order:
            if field in meta and field not in skip_fields:
                value = meta[field]

                # Special handling for different value types
                if isinstance(value, Decimal):
                    lines.append(f"    {field}: {value}")
                elif isinstance(value, str):
                    # String values need quotes
                    lines.append(f'    {field}: "{value}"')
                else:
                    # Numbers, booleans, etc.
                    lines.append(f"    {field}: {value}")

        # Then add any other metadata fields not in the known list
        for field, value in sorted(meta.items()):
            if field not in known_fields_order and field not in skip_fields:
                if isinstance(value, Decimal):
                    lines.append(f"    {field}: {value}")
                elif isinstance(value, str):
                    lines.append(f'    {field}: "{value}"')
                else:
                    lines.append(f"    {field}: {value}")

        # Add postings (2 spaces, with amounts aligned by decimal point)
        if entry.postings:
            # First pass: collect all posting info and find alignment position
            posting_info: List[Dict[str, Any]] = []
            max_account_len = 0
            max_amount_int_len = 0  # Length of integer part (before decimal)

            for posting in entry.postings:
                account = posting.account
                max_account_len = max(max_account_len, len(account))

                if posting.units:
                    amount_str = str(posting.units.number)
                    # Find integer part length (before decimal point or entire number)
                    if "." in amount_str:
                        int_part = amount_str.split(".")[0]
                    else:
                        int_part = amount_str

                    # Handle negative sign
                    int_len = len(int_part)
                    max_amount_int_len = max(max_amount_int_len, int_len)

                    posting_info.append(
                        {
                            "account": account,
                            "number": posting.units.number,
                            "currency": posting.units.currency,
                            "amount_str": amount_str,
                            "int_len": int_len,
                        }
                    )
                else:
                    posting_info.append(
                        {
                            "account": account,
                            "number": None,
                            "currency": None,
                            "amount_str": "",
                            "int_len": 0,
                        }
                    )

            # Second pass: format with aligned decimal points
            for info in posting_info:
                number = info.get("number")
                account_name = str(info.get("account", ""))
                if number is not None:
                    # Calculate padding: account + 2 spaces minimum
                    account_padding = max_account_len - len(account_name) + 2

                    # Align decimal points by right-aligning the integer part
                    int_len = int(info.get("int_len", 0))
                    int_padding = max_amount_int_len - int_len

                    amount_str = str(info.get("amount_str", ""))
                    padded_amount = " " * max(int_padding, 0) + amount_str
                    currency_code = info.get("currency") or ""

                    lines.append(
                        f"  {account_name}{' ' * account_padding}{padded_amount} {currency_code}"
                    )
                else:
                    # Posting without amount
                    lines.append(f"  {account_name}")

        return "\n".join(lines)
