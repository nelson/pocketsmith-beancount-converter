"""Tests for pocketsmith.account_get module functionality."""

import pytest

from src.pocketsmith.account_get import get_accounts, get_transaction_accounts


class TestGetAccounts:
    """Test account retrieval functions."""

    def test_get_accounts_with_client(self, patch_get_user, mock_client):
        """Test getting accounts with provided client."""
        mock_get_user = patch_get_user("account_get", user_id=123)

        mock_accounts = [
            {"id": 1, "name": "Checking", "balance": "1000.00"},
            {"id": 2, "name": "Savings", "balance": "5000.00"},
        ]
        mock_client._make_request.return_value = mock_accounts

        result = get_accounts(client=mock_client)

        assert result == mock_accounts
        mock_get_user.assert_called_once_with(mock_client)
        mock_client._make_request.assert_called_once_with("users/123/accounts")

    def test_get_accounts_with_api_key(
        self, patch_get_user, patch_client_class, mock_client
    ):
        """Test getting accounts with API key (creates new client)."""
        mock_get_user = patch_get_user("account_get", user_id=456)
        mock_client_class = patch_client_class("account_get")

        mock_accounts = [{"id": 1, "name": "Test Account"}]
        mock_client._make_request.return_value = mock_accounts

        result = get_accounts(api_key="test_key")

        assert result == mock_accounts
        mock_client_class.assert_called_once_with("test_key")
        mock_get_user.assert_called_once_with(mock_client)
        mock_client._make_request.assert_called_once_with("users/456/accounts")

    def test_get_accounts_non_list_response(self, patch_get_user, mock_client):
        """Test handling non-list response from API."""
        patch_get_user("account_get", user_id=123)

        # API returns non-list response
        mock_client._make_request.return_value = {"error": "Not found"}

        result = get_accounts(client=mock_client)

        assert result == []

    def test_get_accounts_empty_list(self, patch_get_user, mock_client):
        """Test handling empty list response."""
        patch_get_user("account_get", user_id=123)
        mock_client._make_request.return_value = []

        result = get_accounts(client=mock_client)

        assert result == []

    def test_get_accounts_api_error(self, patch_get_user, mock_client):
        """Test handling API request error."""
        patch_get_user("account_get", user_id=123)
        mock_client._make_request.side_effect = Exception("API Error")

        with pytest.raises(Exception):
            get_accounts(client=mock_client)


class TestGetTransactionAccounts:
    """Test transaction account retrieval functions."""

    def test_get_transaction_accounts_with_client(self, patch_get_user, mock_client):
        """Test getting transaction accounts with provided client."""
        mock_get_user = patch_get_user("account_get", user_id=789)

        mock_accounts = [
            {"id": 1, "name": "Main Account", "type": "bank"},
            {"id": 2, "name": "Credit Card", "type": "credit_card"},
        ]
        mock_client._make_request.return_value = mock_accounts

        result = get_transaction_accounts(client=mock_client)

        assert result == mock_accounts
        mock_get_user.assert_called_once_with(mock_client)
        mock_client._make_request.assert_called_once_with(
            "users/789/transaction_accounts"
        )

    def test_get_transaction_accounts_with_api_key(
        self, patch_get_user, patch_client_class, mock_client
    ):
        """Test getting transaction accounts with API key."""
        mock_get_user = patch_get_user("account_get", user_id=999)
        mock_client_class = patch_client_class("account_get")

        mock_accounts = [{"id": 5, "name": "Investment Account"}]
        mock_client._make_request.return_value = mock_accounts

        result = get_transaction_accounts(api_key="test_key_2")

        assert result == mock_accounts
        mock_client_class.assert_called_once_with("test_key_2")
        mock_get_user.assert_called_once_with(mock_client)
        mock_client._make_request.assert_called_once_with(
            "users/999/transaction_accounts"
        )

    def test_get_transaction_accounts_non_list_response(
        self, patch_get_user, mock_client
    ):
        """Test handling non-list response from transaction accounts API."""
        patch_get_user("account_get", user_id=123)

        # API returns non-list response
        mock_client._make_request.return_value = {"message": "Unauthorized"}

        result = get_transaction_accounts(client=mock_client)

        assert result == []

    def test_get_transaction_accounts_get_user_fails(
        self, patch_get_user, mock_client
    ):
        """Test handling get_user failure."""
        mock_get_user = patch_get_user("account_get")
        mock_get_user.side_effect = Exception("User fetch failed")

        with pytest.raises(Exception):
            get_transaction_accounts(client=mock_client)


class TestPropertyBasedTests:
    """Property-based tests for account functions."""

    def test_get_accounts_various_user_ids(self, patch_get_user, mock_client):
        """Test different user IDs construct correct API paths."""
        mock_client._make_request.return_value = []
        mock_get_user = patch_get_user("account_get")

        for user_id in [1, 123, 999999]:
            mock_get_user.return_value = {"id": user_id}
            get_accounts(client=mock_client)
            expected_path = f"users/{user_id}/accounts"
            mock_client._make_request.assert_called_with(expected_path)

    def test_get_transaction_accounts_various_user_ids(
        self, patch_get_user, mock_client
    ):
        """Test different user IDs construct correct API paths."""
        mock_client._make_request.return_value = []
        mock_get_user = patch_get_user("account_get")

        for user_id in [1, 456, 789123]:
            mock_get_user.return_value = {"id": user_id}
            get_transaction_accounts(client=mock_client)
            expected_path = f"users/{user_id}/transaction_accounts"
            mock_client._make_request.assert_called_with(expected_path)
