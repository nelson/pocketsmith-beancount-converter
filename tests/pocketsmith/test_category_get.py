"""Tests for pocketsmith.category_get module functionality."""

import pytest
from unittest.mock import Mock, patch

from src.pocketsmith.category_get import get_categories
from src.pocketsmith.common import PocketSmithClient


class TestGetCategories:
    """Test category retrieval functions."""

    @patch("src.pocketsmith.category_get.get_user")
    def test_get_categories_with_client(self, mock_get_user):
        """Test getting categories with provided client."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_get_user.return_value = {"id": 123}

        mock_categories = [
            {"id": 1, "title": "Food & Dining", "is_income": False},
            {"id": 2, "title": "Transportation", "is_income": False},
            {"id": 3, "title": "Salary", "is_income": True},
        ]
        mock_client._make_request.return_value = mock_categories

        result = get_categories(client=mock_client)

        assert result == mock_categories
        mock_get_user.assert_called_once_with(mock_client)
        mock_client._make_request.assert_called_once_with("users/123/categories")

    @patch("src.pocketsmith.category_get.get_user")
    @patch("src.pocketsmith.category_get.PocketSmithClient")
    def test_get_categories_with_api_key(self, mock_client_class, mock_get_user):
        """Test getting categories with API key (creates new client)."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_client_class.return_value = mock_client
        mock_get_user.return_value = {"id": 456}

        mock_categories = [{"id": 5, "title": "Shopping", "is_income": False}]
        mock_client._make_request.return_value = mock_categories

        result = get_categories(api_key="test_key")

        assert result == mock_categories
        mock_client_class.assert_called_once_with("test_key")
        mock_get_user.assert_called_once_with(mock_client)
        mock_client._make_request.assert_called_once_with("users/456/categories")

    @patch("src.pocketsmith.category_get.get_user")
    def test_get_categories_non_list_response(self, mock_get_user):
        """Test handling non-list response from API."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_get_user.return_value = {"id": 123}

        # API returns non-list response
        mock_client._make_request.return_value = {"error": "Forbidden"}

        result = get_categories(client=mock_client)

        assert result == []

    @patch("src.pocketsmith.category_get.get_user")
    def test_get_categories_empty_list(self, mock_get_user):
        """Test handling empty list response."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_get_user.return_value = {"id": 123}
        mock_client._make_request.return_value = []

        result = get_categories(client=mock_client)

        assert result == []

    @patch("src.pocketsmith.category_get.get_user")
    def test_get_categories_api_error(self, mock_get_user):
        """Test handling API request error."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_get_user.return_value = {"id": 123}
        mock_client._make_request.side_effect = Exception("Network timeout")

        with pytest.raises(Exception):
            get_categories(client=mock_client)

    @patch("src.pocketsmith.category_get.get_user")
    def test_get_categories_get_user_fails(self, mock_get_user):
        """Test handling get_user failure."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_get_user.side_effect = KeyError("id")  # User dict missing 'id'

        with pytest.raises(KeyError):
            get_categories(client=mock_client)

    @patch("src.pocketsmith.category_get.get_user")
    def test_get_categories_string_response(self, mock_get_user):
        """Test handling string response from API."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_get_user.return_value = {"id": 123}

        # API returns string instead of list
        mock_client._make_request.return_value = "Error message"

        result = get_categories(client=mock_client)

        assert result == []


class TestPropertyBasedTests:
    """Property-based tests for category functions."""

    @patch("src.pocketsmith.category_get.get_user")
    def test_get_categories_various_user_ids(self, mock_get_user):
        """Test different user IDs construct correct API paths."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_client._make_request.return_value = []

        for user_id in [1, 456, 789123]:
            mock_get_user.return_value = {"id": user_id}
            get_categories(client=mock_client)
            expected_path = f"users/{user_id}/categories"
            mock_client._make_request.assert_called_with(expected_path)

    @patch("src.pocketsmith.category_get.get_user")
    def test_get_categories_response_handling(self, mock_get_user):
        """Test category list responses are returned as-is."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_get_user.return_value = {"id": 123}

        category_lists = [
            [],
            [{"id": 1, "title": "Food", "is_income": False}],
            [{"id": 1, "title": "Food"}, {"id": 2, "title": "Transport"}],
        ]

        for category_list in category_lists:
            mock_client._make_request.return_value = category_list
            result = get_categories(client=mock_client)
            assert result == category_list

    @patch("src.pocketsmith.category_get.get_user")
    def test_get_categories_invalid_responses(self, mock_get_user):
        """Test non-list responses return empty list."""
        mock_client = Mock(spec=PocketSmithClient)
        mock_get_user.return_value = {"id": 123}

        invalid_responses = ["error", {"error": "not found"}, 404, None]

        for invalid_response in invalid_responses:
            mock_client._make_request.return_value = invalid_response
            result = get_categories(client=mock_client)
            assert result == []
