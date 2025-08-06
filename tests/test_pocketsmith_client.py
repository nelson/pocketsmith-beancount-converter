import pytest
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
