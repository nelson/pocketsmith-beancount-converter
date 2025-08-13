"""Transaction retrieval operations for PocketSmith API."""

import requests
from typing import List, Dict, Any, Optional
from .common import PocketSmithClient
from .user_get import get_user


def get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    account_id: Optional[int] = None,
    updated_since: Optional[str] = None,
    client: Optional[PocketSmithClient] = None,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get transactions with optional filtering."""
    if client is None:
        client = PocketSmithClient(api_key)

    user = get_user(client)
    user_id: int = user["id"]

    params: Dict[str, Any] = {"per_page": 1000}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if account_id:
        params["account_id"] = account_id
    if updated_since:
        params["updated_since"] = updated_since

    all_transactions = []
    url: Optional[str] = f"{client.base_url}/users/{user_id}/transactions"

    first_request = True
    while url:
        response = requests.get(
            url,
            headers=client.headers,
            params=params if first_request else None,
        )
        response.raise_for_status()

        result = response.json()
        if isinstance(result, list):
            all_transactions.extend(result)

        # Parse Link header for next page
        link_header = response.headers.get("Link", "")
        links = client._parse_link_header(link_header)
        url = links.get("next")
        first_request = False

    return all_transactions


def get_transaction(
    transaction_id: int,
    client: Optional[PocketSmithClient] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get a single transaction by ID."""
    if client is None:
        client = PocketSmithClient(api_key)

    result = client._make_request(f"transactions/{transaction_id}")
    if isinstance(result, dict):
        return result
    raise ValueError(f"Transaction {transaction_id} not found")
