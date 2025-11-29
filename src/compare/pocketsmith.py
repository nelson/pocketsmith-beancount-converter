"""Convert PocketSmith data to standard transaction model."""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime

from .model import Transaction
from .date_utils import parse_date


def convert_pocketsmith_to_model(pocketsmith_data: Dict[str, Any]) -> Transaction:
    """Convert PocketSmith transaction data to standard Transaction model."""

    # Extract core fields
    transaction_id = str(pocketsmith_data.get("id", ""))

    # Amount
    amount = Decimal(str(pocketsmith_data.get("amount", "0")))

    # Date
    transaction_date = parse_date(pocketsmith_data.get("date"))

    # Currency
    currency_code = pocketsmith_data.get("currency_code") or pocketsmith_data.get(
        "transaction_account", {}
    ).get("currency_code")
    if not currency_code:
        import json

        transaction_json = json.dumps(pocketsmith_data, indent=2, default=str)
        raise ValueError(
            f"Transaction {transaction_id} is missing currency_code.\n"
            f"Transaction data:\n{transaction_json}"
        )
    currency_code = currency_code.upper()

    # Transaction details
    payee = pocketsmith_data.get("payee", "").strip() or None
    raw_note = pocketsmith_data.get("note", "").strip() or None
    memo = pocketsmith_data.get("memo", "").strip() or raw_note

    # Extract transfer metadata from note field
    from ..pocketsmith.metadata_encoding import decode_metadata_from_note

    clean_note, note_metadata = decode_metadata_from_note(raw_note)
    note = clean_note or None

    # Extract transfer fields
    is_transfer = pocketsmith_data.get("is_transfer", False)
    paired = note_metadata.get("paired")
    suspect_reason = note_metadata.get("suspect_reason")

    # Category information
    category = _format_category(pocketsmith_data.get("category"))

    # Account information
    account = _format_account(pocketsmith_data.get("transaction_account"))

    # Labels and tags
    labels = pocketsmith_data.get("labels", [])
    if not isinstance(labels, list):
        labels = [labels] if labels else []
    tags = labels.copy()

    # Status
    needs_review = pocketsmith_data.get("needs_review", False)

    # Balance information
    closing_balance = None
    if pocketsmith_data.get("closing_balance") is not None:
        try:
            closing_balance = Decimal(str(pocketsmith_data["closing_balance"]))
        except (ValueError, TypeError):
            pass

    # Timestamps
    created_at = _parse_timestamp(pocketsmith_data.get("created_at"))
    updated_at = _parse_timestamp(pocketsmith_data.get("updated_at"))
    last_modified = pocketsmith_data.get("last_modified")

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
        metadata=pocketsmith_data.copy(),  # Store original data as metadata
    )


def convert_pocketsmith_list_to_model(
    pocketsmith_transactions: List[Dict[str, Any]],
) -> List[Transaction]:
    """Convert a list of PocketSmith transactions to Transaction models."""
    return [convert_pocketsmith_to_model(tx) for tx in pocketsmith_transactions]


def _format_category(
    category_data: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Format PocketSmith category data for the standard model."""
    if not category_data:
        return None

    return {
        "id": category_data.get("id"),
        "title": category_data.get("title", "Uncategorized"),
        "is_income": category_data.get("is_income", False),
        "is_transfer": category_data.get("is_transfer", False),
        "is_bill": category_data.get("is_bill", False),
        "colour": category_data.get("colour"),
        "parent_id": category_data.get("parent_id"),
    }


def _format_account(account_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Format PocketSmith account data for the standard model."""
    if not account_data:
        return None

    institution = account_data.get("institution") or {}

    # Get currency_code - raise error if missing
    currency_code = account_data.get("currency_code")
    if not currency_code:
        import json

        account_json = json.dumps(account_data, indent=2, default=str)
        raise ValueError(
            f"Account {account_data.get('id', 'unknown')} is missing currency_code.\n"
            f"Account data:\n{account_json}"
        )

    return {
        "id": account_data.get("id"),
        "name": account_data.get("name", "Unknown"),
        "type": account_data.get("type", "bank"),
        "currency_code": currency_code,
        "institution": {
            "title": institution.get("title", "Unknown"),
            "currency_code": institution.get("currency_code"),
        },
        "current_balance": account_data.get("current_balance"),
        "current_balance_date": account_data.get("current_balance_date"),
        "starting_balance": account_data.get("starting_balance"),
        "starting_balance_date": account_data.get("starting_balance_date"),
    }


def _parse_timestamp(timestamp_value: Any) -> Optional[datetime]:
    """Parse timestamp from PocketSmith format."""
    if timestamp_value is None:
        return None

    if isinstance(timestamp_value, datetime):
        return timestamp_value

    if isinstance(timestamp_value, str):
        try:
            # PocketSmith uses ISO format with Z suffix
            if timestamp_value.endswith("Z"):
                timestamp_value = timestamp_value[:-1] + "+00:00"
            return datetime.fromisoformat(timestamp_value)
        except ValueError:
            try:
                # Try other common formats
                return datetime.strptime(timestamp_value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass

    return None
