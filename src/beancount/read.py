"""Read and parse beancount ledger files using the beancount library."""

import logging
from typing import List, Dict, Any, Optional, Tuple

from beancount import loader
from beancount.core import data
from beancount.core.data import Transaction

from .common import BeancountError

logger = logging.getLogger(__name__)


def read_ledger(
    file_path: str,
) -> Tuple[List[data.Directive], List[Any], Dict[str, Any]]:
    """Read and parse a beancount file using the beancount library."""
    try:
        entries, errors, options_map = loader.load_file(file_path)

        if errors:
            logger.warning(f"Found {len(errors)} errors when loading {file_path}")
            for error in errors:
                logger.warning(f"  {error}")

            # Check for file not found or other critical errors
            for error in errors:
                if "does not exist" in str(error):
                    raise BeancountError(
                        f"Failed to load beancount file {file_path}: File does not exist"
                    )

        return entries, errors, options_map
    except BeancountError:
        # Re-raise BeancountError as-is
        raise
    except Exception as e:
        raise BeancountError(f"Failed to load beancount file {file_path}: {e}")


def parse_transactions_from_file(file_path: str) -> List[Dict[str, Any]]:
    """Parse transactions from a beancount file and return as dictionaries."""
    entries, _, _ = read_ledger(file_path)

    transactions = []
    for entry in entries:
        if isinstance(entry, Transaction):
            transaction_data = parse_transaction_entry(entry)
            if transaction_data:
                transactions.append(transaction_data)

    return transactions


def parse_transaction_entry(entry: Transaction) -> Optional[Dict[str, Any]]:
    """Parse a beancount Transaction entry into a dictionary."""
    try:
        # Extract basic transaction information
        transaction: Dict[str, Any] = {
            "id": None,
            "date": entry.date.strftime("%Y-%m-%d"),
            "flag": entry.flag,
            "payee": entry.payee or "",
            "narration": entry.narration or "",
            "tags": list(entry.tags) if entry.tags else [],
            "links": list(entry.links) if entry.links else [],
            "postings": [],
        }

        # Extract metadata
        if entry.meta:
            if "id" in entry.meta:
                transaction["id"] = str(entry.meta["id"])
            if "last_modified" in entry.meta:
                transaction["last_modified"] = entry.meta["last_modified"]
            if "closing_balance" in entry.meta:
                transaction["closing_balance"] = entry.meta["closing_balance"]

        # Extract postings
        for posting in entry.postings:
            posting_data: Dict[str, Any] = {
                "account": posting.account,
                "units": None,
                "cost": None,
                "price": None,
            }

            if posting.units:
                posting_data["units"] = {
                    "number": posting.units.number,
                    "currency": posting.units.currency,
                }

            if posting.cost:
                # Handle both Cost and CostSpec types
                cost_number = getattr(posting.cost, "number", None)
                cost_currency = getattr(posting.cost, "currency", None)
                if cost_number is not None:
                    posting_data["cost"] = {
                        "number": cost_number,
                        "currency": cost_currency,
                    }

            if posting.price:
                posting_data["price"] = {
                    "number": posting.price.number,
                    "currency": posting.price.currency,
                }

            transaction["postings"].append(posting_data)

        return transaction

    except Exception as e:
        logger.error(f"Failed to parse transaction entry: {e}")
        return None


def extract_accounts_from_entries(
    entries: List[data.Directive],
) -> List[Dict[str, Any]]:
    """Extract account information from beancount entries."""
    accounts = []

    for entry in entries:
        if isinstance(entry, data.Open):
            account_data = {
                "name": entry.account,
                "open_date": entry.date.strftime("%Y-%m-%d"),
                "currencies": list(entry.currencies) if entry.currencies else [],
                "meta": dict(entry.meta) if entry.meta else {},
            }
            accounts.append(account_data)

    return accounts


def extract_commodities_from_entries(
    entries: List[data.Directive],
) -> List[Dict[str, Any]]:
    """Extract commodity information from beancount entries."""
    commodities = []

    for entry in entries:
        if isinstance(entry, data.Commodity):
            commodity_data = {
                "currency": entry.currency,
                "date": entry.date.strftime("%Y-%m-%d"),
                "meta": dict(entry.meta) if entry.meta else {},
            }
            commodities.append(commodity_data)

    return commodities


def find_transactions_by_id(
    entries: List[data.Directive], transaction_id: str
) -> List[Transaction]:
    """Find transactions by ID in beancount entries."""
    matching_transactions = []

    for entry in entries:
        if isinstance(entry, Transaction):
            if entry.meta and str(entry.meta.get("id")) == str(transaction_id):
                matching_transactions.append(entry)

    return matching_transactions


def extract_balance_directives(entries: List[data.Directive]) -> List[Dict[str, Any]]:
    """Extract balance directives from beancount entries."""
    balances = []

    for entry in entries:
        if isinstance(entry, data.Balance):
            balance_data = {
                "date": entry.date.strftime("%Y-%m-%d"),
                "account": entry.account,
                "amount": entry.amount.number if entry.amount else None,
                "currency": entry.amount.currency if entry.amount else None,
                "tolerance": entry.tolerance,
                "meta": dict(entry.meta) if entry.meta else {},
            }
            balances.append(balance_data)

    return balances


def get_transaction_by_id(
    file_path: str, transaction_id: str
) -> Optional[Dict[str, Any]]:
    """Get a specific transaction by ID from a beancount file."""
    entries, _, _ = read_ledger(file_path)

    matching_transactions = find_transactions_by_id(entries, transaction_id)
    if matching_transactions:
        return parse_transaction_entry(matching_transactions[0])

    return None
