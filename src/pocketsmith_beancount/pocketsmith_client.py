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
    ) -> List[Dict[str, Any]]:
        user = self.get_user()
        user_id: int = user["id"]

        params: Dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if account_id:
            params["account_id"] = account_id

        result = self._make_request(f"users/{user_id}/transactions", params)
        if isinstance(result, list):
            return result
        return []

    def get_transaction_accounts(self) -> List[Dict[str, Any]]:
        user = self.get_user()
        user_id: int = user["id"]
        result = self._make_request(f"users/{user_id}/transaction_accounts")
        if isinstance(result, list):
            return result
        return []
