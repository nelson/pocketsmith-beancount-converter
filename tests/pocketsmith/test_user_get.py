"""Tests for pocketsmith.user_get module functionality."""

import pytest
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st

from src.pocketsmith.user_get import get_user
from src.pocketsmith.common import PocketSmithClient


class TestGetUser:
    """Test user retrieval functions."""

    def test_get_user_with_client(self):
        """Test getting user with provided client."""
        mock_client = Mock(spec=PocketSmithClient)

        mock_user = {
            "id": 123,
            "login": "testuser",
            "email": "test@example.com",
            "name": "Test User",
        }
        mock_client._make_request.return_value = mock_user

        result = get_user(client=mock_client)

        assert result == mock_user
        mock_client._make_request.assert_called_once_with("me")

    @patch("src.pocketsmith.user_get.PocketSmithClient")
    def test_get_user_with_api_key(self, mock_client_class):
        """Test getting user with API key (creates new client)."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_client_class.return_value = mock_client

        mock_user = {"id": 456, "login": "apiuser", "email": "api@example.com"}
        mock_client._make_request.return_value = mock_user

        result = get_user(api_key="test_api_key")

        assert result == mock_user
        mock_client_class.assert_called_once_with("test_api_key")
        mock_client._make_request.assert_called_once_with("me")

    def test_get_user_non_dict_response(self):
        """Test handling non-dict response from API."""
        mock_client = Mock(spec=PocketSmithClient)

        # API returns non-dict response (e.g., error list or string)
        mock_client._make_request.return_value = ["error", "invalid response"]

        result = get_user(client=mock_client)

        assert result == {}

    def test_get_user_empty_dict(self):
        """Test handling empty dict response."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_client._make_request.return_value = {}

        result = get_user(client=mock_client)

        assert result == {}

    def test_get_user_api_error(self):
        """Test handling API request error."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_client._make_request.side_effect = Exception("API connection failed")

        with pytest.raises(Exception):
            get_user(client=mock_client)

    def test_get_user_none_response(self):
        """Test handling None response from API."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_client._make_request.return_value = None

        result = get_user(client=mock_client)

        assert result == {}


class TestPropertyBasedTests:
    """Property-based tests for user functions."""

    @given(
        st.fixed_dictionaries(
            {
                "id": st.integers(min_value=1, max_value=999999),
                "login": st.text(min_size=1, max_size=50),
                "email": st.emails(),
                "name": st.text(min_size=0, max_size=100),
            }
        )
    )
    def test_get_user_response_properties(self, user_data):
        """Property test: valid user dict responses should be returned as-is."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_client._make_request.return_value = user_data

        result = get_user(client=mock_client)

        assert result == user_data
        assert result["id"] == user_data["id"]
        assert result["login"] == user_data["login"]
        assert result["email"] == user_data["email"]
        assert result["name"] == user_data["name"]
        mock_client._make_request.assert_called_once_with("me")

    @given(
        st.one_of(
            st.text(),  # String response
            st.lists(st.text()),  # List response
            st.integers(),  # Integer response
            st.none(),  # None response
            st.booleans(),  # Boolean response
        )
    )
    def test_get_user_invalid_response_properties(self, invalid_response):
        """Property test: non-dict responses should return empty dict."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_client._make_request.return_value = invalid_response

        result = get_user(client=mock_client)

        # All non-dict responses should result in empty dict
        if not isinstance(invalid_response, dict):
            assert result == {}
        else:
            assert result == invalid_response

    @patch("src.pocketsmith.user_get.PocketSmithClient")
    def test_get_user_various_api_keys(self, mock_client_class):
        """Test different API keys create clients correctly."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_client_class.return_value = mock_client
        mock_client._make_request.return_value = {"id": 123, "login": "test"}

        for api_key in ["key1", "test_key_abc", "sk_1234567890"]:
            result = get_user(api_key=api_key)
            mock_client_class.assert_called_with(api_key)
            assert isinstance(result, dict)
