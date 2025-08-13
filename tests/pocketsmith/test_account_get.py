"""Tests for pocketsmith.account_get module functionality."""

import pytest
from unittest.mock import Mock, patch

from src.pocketsmith.account_get import get_accounts, get_transaction_accounts
from src.pocketsmith.common import PocketSmithClient


class TestGetAccounts:
    """Test account retrieval functions."""

    @patch("src.pocketsmith.account_get.get_user")
    def test_get_accounts_with_client(self, mock_get_user):
        """Test getting accounts with provided client."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_get_user.return_value = {"id": 123}

        mock_accounts = [
            {"id": 1, "name": "Checking", "balance": "1000.00"},
            {"id": 2, "name": "Savings", "balance": "5000.00"},
        ]
        mock_client._make_request.return_value = mock_accounts

        result = get_accounts(client=mock_client)

        assert result == mock_accounts
        mock_get_user.assert_called_once_with(mock_client)
        mock_client._make_request.assert_called_once_with("users/123/accounts")

    @patch("src.pocketsmith.account_get.get_user")
    @patch("src.pocketsmith.account_get.PocketSmithClient")
    def test_get_accounts_with_api_key(self, mock_client_class, mock_get_user):
        """Test getting accounts with API key (creates new client)."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_client_class.return_value = mock_client
        mock_get_user.return_value = {"id": 456}

        mock_accounts = [{"id": 1, "name": "Test Account"}]
        mock_client._make_request.return_value = mock_accounts

        result = get_accounts(api_key="test_key")

        assert result == mock_accounts
        mock_client_class.assert_called_once_with("test_key")
        mock_get_user.assert_called_once_with(mock_client)
        mock_client._make_request.assert_called_once_with("users/456/accounts")

    @patch("src.pocketsmith.account_get.get_user")
    def test_get_accounts_non_list_response(self, mock_get_user):
        """Test handling non-list response from API."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_get_user.return_value = {"id": 123}

        # API returns non-list response
        mock_client._make_request.return_value = {"error": "Not found"}

        result = get_accounts(client=mock_client)

        assert result == []

    @patch("src.pocketsmith.account_get.get_user")
    def test_get_accounts_empty_list(self, mock_get_user):
        """Test handling empty list response."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_get_user.return_value = {"id": 123}
        mock_client._make_request.return_value = []

        result = get_accounts(client=mock_client)

        assert result == []

    @patch("src.pocketsmith.account_get.get_user")
    def test_get_accounts_api_error(self, mock_get_user):
        """Test handling API request error."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_get_user.return_value = {"id": 123}
        mock_client._make_request.side_effect = Exception("API Error")

        with pytest.raises(Exception):
            get_accounts(client=mock_client)


class TestGetTransactionAccounts:
    """Test transaction account retrieval functions."""

    @patch("src.pocketsmith.account_get.get_user")
    def test_get_transaction_accounts_with_client(self, mock_get_user):
        """Test getting transaction accounts with provided client."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_get_user.return_value = {"id": 789}

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

    @patch("src.pocketsmith.account_get.get_user")
    @patch("src.pocketsmith.account_get.PocketSmithClient")
    def test_get_transaction_accounts_with_api_key(
        self, mock_client_class, mock_get_user
    ):
        """Test getting transaction accounts with API key."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_client_class.return_value = mock_client
        mock_get_user.return_value = {"id": 999}

        mock_accounts = [{"id": 5, "name": "Investment Account"}]
        mock_client._make_request.return_value = mock_accounts

        result = get_transaction_accounts(api_key="test_key_2")

        assert result == mock_accounts
        mock_client_class.assert_called_once_with("test_key_2")
        mock_get_user.assert_called_once_with(mock_client)
        mock_client._make_request.assert_called_once_with(
            "users/999/transaction_accounts"
        )

    @patch("src.pocketsmith.account_get.get_user")
    def test_get_transaction_accounts_non_list_response(self, mock_get_user):
        """Test handling non-list response from transaction accounts API."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_get_user.return_value = {"id": 123}

        # API returns non-list response
        mock_client._make_request.return_value = {"message": "Unauthorized"}

        result = get_transaction_accounts(client=mock_client)

        assert result == []

    @patch("src.pocketsmith.account_get.get_user")
    def test_get_transaction_accounts_get_user_fails(self, mock_get_user):
        """Test handling get_user failure."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_get_user.side_effect = Exception("User fetch failed")

        with pytest.raises(Exception):
            get_transaction_accounts(client=mock_client)


class TestPropertyBasedTests:
    """Property-based tests for account functions."""

    @patch("src.pocketsmith.account_get.get_user")
    def test_get_accounts_various_user_ids(self, mock_get_user):
        """Test different user IDs construct correct API paths."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_client._make_request.return_value = []

        for user_id in [1, 123, 999999]:
            mock_get_user.return_value = {"id": user_id}
            get_accounts(client=mock_client)
            expected_path = f"users/{user_id}/accounts"
            mock_client._make_request.assert_called_with(expected_path)

    @patch("src.pocketsmith.account_get.get_user")
    def test_get_transaction_accounts_various_user_ids(self, mock_get_user):
        """Test different user IDs construct correct API paths."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_client._make_request.return_value = []

        for user_id in [1, 456, 789123]:
            mock_get_user.return_value = {"id": user_id}
            get_transaction_accounts(client=mock_client)
            expected_path = f"users/{user_id}/transaction_accounts"
            mock_client._make_request.assert_called_with(expected_path)
