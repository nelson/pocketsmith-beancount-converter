"""Account operations for PocketSmith API."""

from typing import List, Dict, Any, Optional
from .common import PocketSmithClient
from .user_get import get_user


def get_accounts(
    client: Optional[PocketSmithClient] = None, api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get all accounts for the user."""
    if client is None:
        client = PocketSmithClient(api_key)

    user = get_user(client)
    user_id: int = user["id"]
    result = client._make_request(f"users/{user_id}/accounts")
    if isinstance(result, list):
        return result
    return []


def get_transaction_accounts(
    client: Optional[PocketSmithClient] = None, api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get transaction accounts for the user."""
    if client is None:
        client = PocketSmithClient(api_key)

    user = get_user(client)
    user_id: int = user["id"]
    result = client._make_request(f"users/{user_id}/transaction_accounts")
    if isinstance(result, list):
        return result
    return []
