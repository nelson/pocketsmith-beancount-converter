import pytest
import requests
from unittest.mock import Mock, patch
from src.pocketsmith_beancount.pocketsmith_client import PocketSmithClient


class TestPocketSmithClient:
    def test_init_with_api_key(self):
        client = PocketSmithClient("test_key")
        assert client.api_key == "test_key"
        assert client.base_url == "https://api.pocketsmith.com/v2"

    def test_init_without_api_key_raises_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="PocketSmith API key is required"):
                PocketSmithClient()

    @patch("src.pocketsmith_beancount.pocketsmith_client.requests.get")
    def test_get_user(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"id": 1, "login": "test_user"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = PocketSmithClient("test_key")
        result = client.get_user()

        assert result == {"id": 1, "login": "test_user"}
        mock_get.assert_called_once_with(
            "https://api.pocketsmith.com/v2/me",
            headers={"X-Developer-Key": "test_key", "Accept": "application/json"},
            params=None,
        )

    @patch("src.pocketsmith_beancount.pocketsmith_client.requests.get")
    def test_get_transactions_with_params(self, mock_get):
        def mock_get_side_effect(url, headers=None, params=None):
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None

            if "me" in url:
                mock_response.json.return_value = {"id": 123, "login": "test_user"}
            else:
                mock_response.json.return_value = [{"id": 1, "amount": "10.00"}]

            return mock_response

        mock_get.side_effect = mock_get_side_effect

        client = PocketSmithClient("test_key")
        result = client.get_transactions(
            start_date="2024-01-01", end_date="2024-12-31", account_id=123
        )

        assert result == [{"id": 1, "amount": "10.00"}]
        assert mock_get.call_count == 2

        # Check the transactions call (second call)
        transactions_call = mock_get.call_args_list[1]
        assert (
            transactions_call[0][0]
            == "https://api.pocketsmith.com/v2/users/123/transactions"
        )
        assert transactions_call[1]["params"] == {
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "account_id": 123,
        }

    @patch("src.pocketsmith_beancount.pocketsmith_client.requests.get")
    def test_get_accounts(self, mock_get):
        def mock_get_side_effect(url, headers=None, params=None):
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None

            if "me" in url:
                mock_response.json.return_value = {"id": 123, "login": "test_user"}
            else:
                mock_response.json.return_value = [
                    {"id": 1, "name": "Checking", "type": "checking"},
                    {"id": 2, "name": "Savings", "type": "savings"},
                ]

            return mock_response

        mock_get.side_effect = mock_get_side_effect

        client = PocketSmithClient("test_key")
        result = client.get_accounts()

        assert len(result) == 2
        assert result[0]["name"] == "Checking"
        assert result[1]["name"] == "Savings"
        assert mock_get.call_count == 2

    @patch("src.pocketsmith_beancount.pocketsmith_client.requests.get")
    def test_get_categories(self, mock_get):
        def mock_get_side_effect(url, headers=None, params=None):
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None

            if "me" in url:
                mock_response.json.return_value = {"id": 123, "login": "test_user"}
            else:
                mock_response.json.return_value = [
                    {"id": 1, "title": "Groceries", "is_transfer": False},
                    {"id": 2, "title": "Salary", "is_income": True},
                ]

            return mock_response

        mock_get.side_effect = mock_get_side_effect

        client = PocketSmithClient("test_key")
        result = client.get_categories()

        assert len(result) == 2
        assert result[0]["title"] == "Groceries"
        assert result[1]["title"] == "Salary"
        assert mock_get.call_count == 2

    @patch("src.pocketsmith_beancount.pocketsmith_client.requests.get")
    def test_get_transaction_accounts(self, mock_get):
        def mock_get_side_effect(url, headers=None, params=None):
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None

            if "me" in url:
                mock_response.json.return_value = {"id": 123, "login": "test_user"}
            else:
                mock_response.json.return_value = [
                    {"id": 1, "name": "Checking", "type": "bank"},
                    {"id": 2, "name": "Credit Card", "type": "credit_card"},
                ]

            return mock_response

        mock_get.side_effect = mock_get_side_effect

        client = PocketSmithClient("test_key")
        result = client.get_transaction_accounts()

        assert len(result) == 2
        assert result[0]["name"] == "Checking"
        assert result[1]["name"] == "Credit Card"
        assert mock_get.call_count == 2

    @patch("src.pocketsmith_beancount.pocketsmith_client.requests.get")
    def test_make_request_error_handling(self, mock_get):
        client = PocketSmithClient("test_key")

        # Test 404 error
        mock_response_404 = Mock()
        mock_response_404.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )
        mock_get.return_value = mock_response_404

        with pytest.raises(requests.exceptions.HTTPError):
            client._make_request("nonexistent")

        # Test 401 error
        mock_response_401 = Mock()
        mock_response_401.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Unauthorized"
        )
        mock_get.return_value = mock_response_401

        with pytest.raises(requests.exceptions.HTTPError):
            client._make_request("me")

        # Test 500 error
        mock_response_500 = Mock()
        mock_response_500.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Internal Server Error"
        )
        mock_get.return_value = mock_response_500

        with pytest.raises(requests.exceptions.HTTPError):
            client._make_request("me")

    @patch("src.pocketsmith_beancount.pocketsmith_client.requests.get")
    def test_get_transactions_without_params(self, mock_get):
        def mock_get_side_effect(url, headers=None, params=None):
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None

            if "me" in url:
                mock_response.json.return_value = {"id": 123, "login": "test_user"}
            else:
                mock_response.json.return_value = [
                    {"id": 1, "amount": "10.00"},
                    {"id": 2, "amount": "20.00"},
                ]

            return mock_response

        mock_get.side_effect = mock_get_side_effect

        client = PocketSmithClient("test_key")
        result = client.get_transactions()

        assert len(result) == 2
        assert mock_get.call_count == 2

        # Check that transactions call was made without params
        transactions_call = mock_get.call_args_list[1]
        assert transactions_call[1]["params"] == {}

    @patch("src.pocketsmith_beancount.pocketsmith_client.requests.get")
    def test_api_response_type_handling(self, mock_get):
        client = PocketSmithClient("test_key")

        # Test non-list response for methods that expect lists
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"error": "Invalid response"}
        mock_get.return_value = mock_response

        # Should return empty list when expecting list but getting dict
        with patch.object(client, "get_user", return_value={"id": 123}):
            result = client.get_accounts()
            assert result == []

            result = client.get_categories()
            assert result == []

            result = client.get_transactions()
            assert result == []

            result = client.get_transaction_accounts()
            assert result == []

        # Test non-dict response for get_user
        mock_response.json.return_value = ["not", "a", "dict"]
        result = client.get_user()
        # Should return empty dict when response is not a dict
        assert isinstance(result, dict)
        assert result == {}
