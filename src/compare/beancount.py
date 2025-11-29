"""Convert beancount data to standard transaction model."""

from typing import Dict, Any, List, Optional
from decimal import Decimal

from .model import Transaction
from .date_utils import parse_date


def convert_beancount_to_model(beancount_data: Dict[str, Any]) -> Transaction:
    """Convert beancount transaction data to standard Transaction model."""

    # Extract core fields
    transaction_id = str(beancount_data.get("id", ""))
    amount = _extract_amount_from_beancount(beancount_data)
    transaction_date = parse_date(beancount_data.get("date"))
    currency_code = _extract_currency_from_beancount(beancount_data)

    # Extract transaction details
    payee = beancount_data.get("payee", "").strip() or None
    note = beancount_data.get("narration", "").strip() or None
    memo = note  # Use narration as memo for consistency

    # Extract labels/tags
    labels = list(beancount_data.get("tags", []))
    tags = labels.copy()  # Beancount tags become our tags/labels

    # Extract metadata
    closing_balance = None
    if "closing_balance" in beancount_data:
        try:
            closing_balance = Decimal(str(beancount_data["closing_balance"]))
        except (ValueError, TypeError):
            pass

    # Extract timestamps
    last_modified = beancount_data.get("last_modified")
    created_at = None
    updated_at = None

    # Extract account information from postings
    account = _extract_account_from_postings(beancount_data.get("postings", []))
    category = _extract_category_from_postings(beancount_data.get("postings", []))

    # Check if transaction needs review (flagged transactions)
    needs_review = beancount_data.get("flag") == "!"

    # Extract transfer metadata
    is_transfer = beancount_data.get("is_transfer", False)
    paired = beancount_data.get("paired")
    suspect_reason = beancount_data.get("suspect_reason")

    return Transaction(
        id=transaction_id,
        amount=amount,
        date=transaction_date,
        currency_code=currency_code,
        payee=payee,
        note=note,
        memo=memo,
        category=category,
        account=account,
        labels=labels,
        tags=tags,
        needs_review=needs_review,
        closing_balance=closing_balance,
        created_at=created_at,
        updated_at=updated_at,
        last_modified=last_modified,
        is_transfer=is_transfer,
        paired=paired,
        suspect_reason=suspect_reason,
        metadata=beancount_data.copy(),  # Store original data as metadata
    )


def convert_beancount_list_to_model(
    beancount_transactions: List[Dict[str, Any]],
) -> List[Transaction]:
    """Convert a list of beancount transactions to Transaction models."""
    return [convert_beancount_to_model(tx) for tx in beancount_transactions]


def _extract_amount_from_beancount(beancount_data: Dict[str, Any]) -> Decimal:
    """Extract the main transaction amount from beancount postings."""
    postings = beancount_data.get("postings", [])

    # Look for the Assets/Liabilities posting first (has correct sign for transfers)
    for posting in postings:
        account_name = posting.get("account", "")
        if account_name.startswith(("Assets:", "Liabilities:")):
            if posting.get("units") and posting["units"].get("number"):
                try:
                    return Decimal(str(posting["units"]["number"]))
                except (ValueError, TypeError):
                    continue

    # Fallback: look for the first posting with units (amount)
    for posting in postings:
        if posting.get("units") and posting["units"].get("number"):
            try:
                return Decimal(str(posting["units"]["number"]))
            except (ValueError, TypeError):
                continue

    # Fallback to zero if no amount found
    return Decimal("0")


def _extract_currency_from_beancount(beancount_data: Dict[str, Any]) -> str:
    """Extract currency code from beancount postings."""
    postings = beancount_data.get("postings", [])

    # Look for the first posting with currency
    for posting in postings:
        if posting.get("units") and posting["units"].get("currency"):
            return str(posting["units"]["currency"])

    # Fallback to USD
    return "USD"


def _extract_account_from_postings(
    postings: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Extract account information from beancount postings."""
    # Look for Assets or Liabilities account (main account)
    for posting in postings:
        account_name = posting.get("account", "")
        if account_name.startswith(("Assets:", "Liabilities:")):
            return {
                "name": account_name,
                "type": "Assets"
                if account_name.startswith("Assets:")
                else "Liabilities",
            }

    return None


def _extract_category_from_postings(
    postings: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Extract category information from beancount postings."""
    # Look for Expenses, Income, or Transfers account (category)
    for posting in postings:
        account_name = posting.get("account", "")
        if account_name.startswith(("Expenses:", "Income:", "Transfers:")):
            # Parse category from account name
            parts = account_name.split(":")
            if len(parts) >= 2:
                return {
                    "title": parts[-1],  # Last part is the category name
                    "is_income": account_name.startswith("Income:"),
                    "is_transfer": account_name.startswith("Transfers:"),
                    "full_account": account_name,
                }

    return None
