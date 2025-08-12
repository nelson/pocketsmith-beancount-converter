import os
import requests
from typing import List, Dict, Any, Optional


class PocketSmithClient:
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

    def get_user(self) -> Dict[str, Any]:
        result = self._make_request("me")
        if isinstance(result, dict):
            return result
        return {}

    def get_accounts(self) -> List[Dict[str, Any]]:
        user = self.get_user()
        user_id: int = user["id"]
        result = self._make_request(f"users/{user_id}/accounts")
        if isinstance(result, list):
            return result
        return []

    def get_categories(self) -> List[Dict[str, Any]]:
        user = self.get_user()
        user_id: int = user["id"]
        result = self._make_request(f"users/{user_id}/categories")
        if isinstance(result, list):
            return result
        return []

    def get_transactions(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        account_id: Optional[int] = None,
        updated_since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        user = self.get_user()
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
        url: Optional[str] = f"{self.base_url}/users/{user_id}/transactions"

        first_request = True
        while url:
            response = requests.get(
                url,
                headers=self.headers,
                params=params if first_request else None,
            )
            response.raise_for_status()

            result = response.json()
            if isinstance(result, list):
                all_transactions.extend(result)

            # Parse Link header for next page
            link_header = response.headers.get("Link", "")
            links = self._parse_link_header(link_header)
            url = links.get("next")
            first_request = False

        return all_transactions

    def get_transaction_accounts(self) -> List[Dict[str, Any]]:
        user = self.get_user()
        user_id: int = user["id"]
        result = self._make_request(f"users/{user_id}/transaction_accounts")
        if isinstance(result, list):
            return result
        return []

    def update_transaction_note(self, transaction_id: str, note: str) -> Dict[str, Any]:
        """Update a transaction's note field."""
        data = {"note": note}
        return self._make_put_request(f"transactions/{transaction_id}", data)

    def update_transaction_labels(
        self, transaction_id: str, labels: List[str]
    ) -> Dict[str, Any]:
        """Update a transaction's labels field."""
        data = {"labels": labels}
        return self._make_put_request(f"transactions/{transaction_id}", data)

    def update_transaction(
        self, transaction_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update multiple fields of a transaction."""
        return self._make_put_request(f"transactions/{transaction_id}", updates)
