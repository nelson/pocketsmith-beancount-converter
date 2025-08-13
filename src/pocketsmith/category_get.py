"""Category operations for PocketSmith API."""

from typing import List, Dict, Any, Optional
from .common import PocketSmithClient
from .user_get import get_user


def get_categories(
    client: Optional[PocketSmithClient] = None, api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get all categories for the user."""
    if client is None:
        client = PocketSmithClient(api_key)

    user = get_user(client)
    user_id: int = user["id"]
    result = client._make_request(f"users/{user_id}/categories")
    if isinstance(result, list):
        return result
    return []
