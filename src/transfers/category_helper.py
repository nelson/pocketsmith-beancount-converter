"""Helper to find Transfer category ID from beancount ledger."""

from pathlib import Path
from typing import Optional

from ..beancount.read import read_ledger
from beancount.core import data as bc_data


def find_transfer_category_id(ledger_path: Path) -> Optional[int]:
    """Find the PocketSmith Transfer category ID from main.beancount.

    Args:
        ledger_path: Path to ledger (file or directory with main.beancount)

    Returns:
        Transfer category ID, or None if not found
    """
    # Determine main file
    if ledger_path.is_file():
        main_file = ledger_path
    else:
        main_file = ledger_path / "main.beancount"

    if not main_file.exists():
        return None

    # Read ledger
    entries, _errors, _options = read_ledger(str(main_file))

    # Find Expenses:Transfer account opening
    for entry in entries:
        if isinstance(entry, bc_data.Open):
            if entry.account == "Expenses:Transfer":
                # Extract ID from metadata
                category_id = entry.meta.get("id")
                if category_id is not None:
                    return int(category_id)

    return None
