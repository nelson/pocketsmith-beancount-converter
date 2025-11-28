"""Common utilities and helpers for PocketSmith API operations."""

import os
import requests
import time
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class PocketSmithAPIError(Exception):
    """Base exception for PocketSmith API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        transaction_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
        self.transaction_id = transaction_id


class PocketSmithClient:
    """Base client for PocketSmith API operations."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.pocketsmith.com/v2",
    ):
        self.api_key = api_key or os.getenv("POCKETSMITH_API_KEY")
        if not self.api_key:
            raise ValueError("PocketSmith API key is required")

        self.base_url = base_url
        self.headers = {"X-Developer-Key": self.api_key, "Accept": "application/json"}

    def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Make a GET request to the API."""
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def _make_put_request(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a PUT request to the API."""
        url = f"{self.base_url}/{endpoint}"
        headers = self.headers.copy()
        headers["Content-Type"] = "application/json"
        response = requests.put(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result if isinstance(result, dict) else {}

    def _make_patch_request(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a PATCH request to the API."""
        url = f"{self.base_url}/{endpoint}"
        headers = self.headers.copy()
        headers["Content-Type"] = "application/json"
        response = requests.patch(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result if isinstance(result, dict) else {}

    def _parse_link_header(self, link_header: str) -> Dict[str, str]:
        """Parse Link header to extract pagination URLs."""
        links: Dict[str, str] = {}
        if not link_header:
            return links

        for link in link_header.split(","):
            parts = link.strip().split(";")
            if len(parts) != 2:
                continue
            url = parts[0].strip("<>")
            # Skip empty or invalid URLs
            if not url or not url.startswith(("http://", "https://")):
                continue
            rel_part = parts[1].strip().split("=")
            if len(rel_part) != 2:
                continue
            rel = rel_part[1].strip('"')
            links[rel] = url
        return links

    # Convenience methods that delegate to specific modules
    def get_user(self) -> Dict[str, Any]:
        """Get user info (delegates to user_get module)."""
        from .user_get import get_user

        return get_user(client=self)

    def get_categories(self) -> List[Dict[str, Any]]:
        """Get categories (delegates to category_get module)."""
        from .category_get import get_categories

        return get_categories(client=self)

    def get_transaction_accounts(self) -> List[Dict[str, Any]]:
        """Get transaction accounts (delegates to account_get module)."""
        from .account_get import get_transaction_accounts

        return get_transaction_accounts(client=self)

    def get_transactions(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        account_id: Optional[int] = None,
        updated_since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get transactions (delegates to transaction_get module)."""
        from .transaction_get import get_transactions

        return get_transactions(
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            updated_since=updated_since,
            client=self,
        )

    def get_transaction(self, transaction_id: int) -> Dict[str, Any]:
        """Get single transaction (delegates to transaction_get module)."""
        from .transaction_get import get_transaction

        return get_transaction(transaction_id=transaction_id, client=self)

    def update_transaction(
        self, transaction_id: str, updates: Dict[str, Any], dry_run: bool = False
    ) -> bool:
        """Update transaction (delegates to transaction_put module)."""
        from .transaction_put import update_transaction

        return update_transaction(
            transaction_id=transaction_id, updates=updates, dry_run=dry_run, client=self
        )


class RateLimiter:
    """Simple rate limiter for API requests."""

    def __init__(self, requests_per_second: float = 2.0):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0

    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()


def validate_update_data(updates: Dict[str, Any]) -> bool:
    """Validate update data before sending to API."""
    if not updates:
        logger.warning("No updates provided")
        return False

    # Basic validation - could be expanded
    for field_name, value in updates.items():
        if field_name in ["labels", "tags"] and value is not None:
            if not isinstance(value, list):
                if not isinstance(value, (str, int, float)):
                    logger.error(f"Invalid value for field '{field_name}': {value}")
                    return False

        if field_name in ["note", "memo"] and value is not None:
            if not isinstance(value, str):
                logger.error(f"Invalid value for field '{field_name}': {value}")
                return False

    return True


def convert_to_api_format(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Convert internal field names/values to API format."""
    api_updates = {}

    field_mapping = {
        "note": "note",
        "memo": "memo",
        "labels": "labels",
        "tags": "labels",  # Tags map to labels in API
        "category_id": "category_id",
        "is_transfer": "is_transfer",
    }

    for field_name, value in updates.items():
        # Map internal field names to API field names
        api_field_name = field_mapping.get(field_name, field_name)

        # Convert value to API format
        api_value: Any
        if field_name in ["labels", "tags"]:
            # Ensure labels are sent as a list of strings
            if isinstance(value, list):
                api_value = [str(item) for item in value]
            elif value:
                api_value = [str(value)]
            else:
                api_value = []
        elif field_name in ["note", "memo"]:
            # Ensure notes are strings
            api_value = str(value) if value is not None else ""
        else:
            api_value = value

        api_updates[api_field_name] = api_value

    return api_updates
