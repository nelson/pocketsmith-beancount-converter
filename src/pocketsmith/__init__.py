"""PocketSmith API client module for handling REST API operations."""

from .common import PocketSmithAPIError
from .user_get import get_user
from .account_get import get_accounts, get_transaction_accounts
from .category_get import get_categories
from .transaction_get import get_transactions, get_transaction
from .transaction_put import (
    update_transaction,
    update_transaction_note,
    update_transaction_labels,
    batch_update_transactions,
)

__all__ = [
    "PocketSmithAPIError",
    "get_user",
    "get_accounts",
    "get_transaction_accounts",
    "get_categories",
    "get_transactions",
    "get_transaction",
    "update_transaction",
    "update_transaction_note",
    "update_transaction_labels",
    "batch_update_transactions",
]
