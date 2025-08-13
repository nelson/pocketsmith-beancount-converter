"""User operations for PocketSmith API."""

from typing import Dict, Any, Optional
from .common import PocketSmithClient


def get_user(
    client: Optional[PocketSmithClient] = None, api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Get user information from PocketSmith API."""
    if client is None:
        client = PocketSmithClient(api_key)

    result = client._make_request("me")
    if isinstance(result, dict):
        return result
    return {}
