"""Text-based updating of beancount files while preserving formatting."""

from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import re

from beancount import loader
from beancount.core import data as bc_data

from .write import convert_transaction_to_beancount


def update_monthly_file_preserving_format(
    file_path: Path,
    new_transactions: List[Dict[str, Any]],
    year: int,
    month: int,
) -> None:
    """Update a monthly beancount file while preserving formatting.

    Uses hybrid approach:
    1. Parse file with beancount to identify existing transactions
    2. Use text-based replacement to update/insert transactions
    3. Preserve all comments, whitespace, and formatting

    Args:
        file_path: Path to monthly beancount file
        new_transactions: List of PocketSmith transactions to merge
        year: Year for this file
        month: Month for this file
    """
    # Step 1: Parse file with beancount to understand structure
    entries, _, _ = loader.load_file(str(file_path))

    # Build map of existing transactions: id -> entry
    existing_txn_ids = {}
    for entry in entries:
        if isinstance(entry, bc_data.Transaction):
            meta = entry.meta or {}
            tx_id = meta.get("id")
            if tx_id is not None:
                existing_txn_ids[str(tx_id)] = entry

    # Step 2: Read file as text and build line map
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Build map: transaction_id -> (start_line, end_line)
    txn_line_map = _build_transaction_line_map(lines)

    # Step 3: Categorize new transactions
    to_update = []  # Transactions that exist and need updating
    to_insert = []  # New transactions to insert

    for txn in new_transactions:
        tx_id = str(txn.get("id"))
        if tx_id in existing_txn_ids:
            to_update.append(txn)
        else:
            to_insert.append(txn)

    # Step 4: Apply updates and insertions
    # Process in reverse order to maintain line numbers
    lines = _apply_updates(lines, to_update, txn_line_map)
    lines = _insert_new_transactions(lines, to_insert, year, month)

    # Step 5: Write back
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def _build_transaction_line_map(lines: List[str]) -> Dict[str, Tuple[int, int]]:
    """Build a map of transaction ID to line numbers.

    Returns:
        Dict mapping transaction_id -> (start_line_index, end_line_index)
        where end_line_index points to the last posting line or trailing blank line
    """
    txn_map = {}
    current_txn_start = None
    current_txn_id = None
    current_txn_last_content_line = None  # Last line with actual content (posting)
    i = 0

    while i < len(lines):
        line = lines[i]

        # Detect start of transaction (date + flag + payee pattern)
        if re.match(r"^\d{4}-\d{2}-\d{2}\s+[*!]", line):
            # If we have a previous transaction, finalize it
            if current_txn_start is not None and current_txn_id is not None:
                # Find the end: last posting line + any immediately following blank lines
                end_line = current_txn_last_content_line
                # Include blank lines immediately after the last posting
                j = current_txn_last_content_line + 1
                while j < i and lines[j].strip() == "":
                    end_line = j
                    j += 1

                txn_map[current_txn_id] = (current_txn_start, end_line)

            current_txn_start = i
            current_txn_id = None
            current_txn_last_content_line = i  # Transaction header line

        # Look for id metadata
        if current_txn_start is not None:
            id_match = re.search(r"^\s+id:\s+(\d+)", line)
            if id_match:
                current_txn_id = id_match.group(1)

            # Track last content line (metadata or posting)
            if line.strip() and not line.strip().startswith(";"):
                current_txn_last_content_line = i

        i += 1

    # Handle last transaction
    if current_txn_start is not None and current_txn_id is not None:
        # For the last transaction, include all remaining content lines
        end_line = current_txn_last_content_line
        # Include any trailing blank lines
        j = current_txn_last_content_line + 1
        while j < len(lines) and lines[j].strip() == "":
            end_line = j
            j += 1

        txn_map[current_txn_id] = (current_txn_start, end_line)

    return txn_map


def _apply_updates(
    lines: List[str],
    transactions: List[Dict[str, Any]],
    txn_line_map: Dict[str, Tuple[int, int]],
) -> List[str]:
    """Replace existing transactions in-place.

    Processes in reverse order to maintain line indices.
    """
    # Sort by line number in reverse order
    sorted_txns = sorted(
        transactions,
        key=lambda t: txn_line_map.get(str(t.get("id")), (0, 0))[0],
        reverse=True,
    )

    new_lines = lines[:]

    for txn in sorted_txns:
        tx_id = str(txn.get("id"))
        if tx_id not in txn_line_map:
            continue

        start_line, end_line = txn_line_map[tx_id]

        # Generate new transaction content
        new_txn_text = convert_transaction_to_beancount(txn)

        # Build replacement lines
        # Split the transaction text into individual lines and add newlines
        txn_lines = new_txn_text.split("\n")
        replacement_lines = [line + "\n" for line in txn_lines]

        # Ensure there's always a blank line after the transaction UNLESS:
        # - This is the last transaction in the file AND there's no blank line after it
        # - OR the replacement already consumed a blank line from the original

        # Check if original had a blank line at end_line (was consumed in the slice)
        original_had_blank = new_lines[end_line].strip() == ""

        # Check if this is not the last line in the file
        not_last_line = end_line < len(new_lines) - 1

        # Add blank line if original had one OR if there's content after this transaction
        if original_had_blank or not_last_line:
            replacement_lines.append("\n")

        new_lines[start_line : end_line + 1] = replacement_lines

    return new_lines


def _insert_new_transactions(
    lines: List[str],
    transactions: List[Dict[str, Any]],
    year: int,
    month: int,
) -> List[str]:
    """Insert new transactions in chronological order.

    Args:
        lines: Current file lines
        transactions: New transactions to insert
        year: Year for date filtering
        month: Month for date filtering
    """
    if not transactions:
        return lines

    # Filter to only transactions for this month
    filtered_txns = []
    for txn in transactions:
        try:
            date = datetime.fromisoformat(txn["date"].replace("Z", "+00:00"))
            if date.year == year and date.month == month:
                filtered_txns.append(txn)
        except (ValueError, KeyError):
            continue

    if not filtered_txns:
        return lines

    # Sort new transactions by date
    filtered_txns.sort(key=lambda t: t.get("date", ""))

    # Find insertion points for each transaction
    new_lines = lines[:]

    for txn in filtered_txns:
        txn_date = txn.get("date", "")[:10]  # YYYY-MM-DD
        insertion_line = _find_insertion_point(new_lines, txn_date)

        # Generate transaction content
        new_txn_text = convert_transaction_to_beancount(txn)

        # Insert with blank line after
        new_lines.insert(insertion_line, new_txn_text + "\n")
        new_lines.insert(insertion_line + 1, "\n")

    return new_lines


def _find_insertion_point(lines: List[str], target_date: str) -> int:
    """Find the line index where a transaction with target_date should be inserted.

    Maintains chronological order.
    """
    # Scan for transaction dates
    for i, line in enumerate(lines):
        match = re.match(r"^(\d{4}-\d{2}-\d{2})\s+[*!]", line)
        if match:
            line_date = match.group(1)
            if line_date > target_date:
                # Insert before this transaction
                return i

    # If no later date found, append at end (before final blank lines if any)
    # Find last non-blank line
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            return i + 1

    return len(lines)
