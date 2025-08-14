"""Tests for pocketsmith.category_get module functionality."""

import pytest

from src.pocketsmith.category_get import get_categories


class TestGetCategories:
    """Test category retrieval functions."""

    def test_get_categories_with_client(self, patch_get_user, mock_client):
        """Test getting categories with provided client."""
        mock_get_user = patch_get_user("category_get", user_id=123)

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

    def test_get_categories_with_api_key(
        self, patch_get_user, patch_client_class, mock_client
    ):
        """Test getting categories with API key (creates new client)."""
        mock_get_user = patch_get_user("category_get", user_id=456)
        mock_client_class = patch_client_class("category_get")

        mock_categories = [{"id": 5, "title": "Shopping", "is_income": False}]
        mock_client._make_request.return_value = mock_categories

        result = get_categories(api_key="test_key")

        assert result == mock_categories
        mock_client_class.assert_called_once_with("test_key")
        mock_get_user.assert_called_once_with(mock_client)
        mock_client._make_request.assert_called_once_with("users/456/categories")

    def test_get_categories_non_list_response(self, patch_get_user, mock_client):
        """Test handling non-list response from API."""
        patch_get_user("category_get", user_id=123)

        # API returns non-list response
        mock_client._make_request.return_value = {"error": "Forbidden"}

        result = get_categories(client=mock_client)

        assert result == []

    def test_get_categories_empty_list(self, patch_get_user, mock_client):
        """Test handling empty list response."""
        patch_get_user("category_get", user_id=123)
        mock_client._make_request.return_value = []

        result = get_categories(client=mock_client)

        assert result == []

    def test_get_categories_api_error(self, patch_get_user, mock_client):
        """Test handling API request error."""
        patch_get_user("category_get", user_id=123)
        mock_client._make_request.side_effect = Exception("Network timeout")

        with pytest.raises(Exception):
            get_categories(client=mock_client)

    def test_get_categories_get_user_fails(
        self, patch_get_user, mock_client
    ):
        """Test handling get_user failure."""
        mock_get_user = patch_get_user("category_get")
        mock_get_user.side_effect = KeyError("id")  # User dict missing 'id'

        with pytest.raises(KeyError):
            get_categories(client=mock_client)

    def test_get_categories_string_response(self, patch_get_user, mock_client):
        """Test handling string response from API."""
        patch_get_user("category_get", user_id=123)

        # API returns string instead of list
        mock_client._make_request.return_value = "Error message"

        result = get_categories(client=mock_client)

        assert result == []


class TestPropertyBasedTests:
    """Property-based tests for category functions."""

    def test_get_categories_various_user_ids(self, patch_get_user, mock_client):
        """Test different user IDs construct correct API paths."""
        mock_client._make_request.return_value = []
        mock_get_user = patch_get_user("category_get")

        for user_id in [1, 456, 789123]:
            mock_get_user.return_value = {"id": user_id}
            get_categories(client=mock_client)
            expected_path = f"users/{user_id}/categories"
            mock_client._make_request.assert_called_with(expected_path)

    def test_get_categories_response_handling(self, patch_get_user, mock_client):
        """Test category list responses are returned as-is."""
        patch_get_user("category_get", user_id=123)

        category_lists = [
            [],
            [{"id": 1, "title": "Food", "is_income": False}],
            [{"id": 1, "title": "Food"}, {"id": 2, "title": "Transport"}],
        ]

        for category_list in category_lists:
            mock_client._make_request.return_value = category_list
            result = get_categories(client=mock_client)
            assert result == category_list

    def test_get_categories_invalid_responses(self, patch_get_user, mock_client):
        """Test non-list responses return empty list."""
        patch_get_user("category_get", user_id=123)

        invalid_responses = ["error", {"error": "not found"}, 404, None]

        for invalid_response in invalid_responses:
            mock_client._make_request.return_value = invalid_response
            result = get_categories(client=mock_client)
            assert result == []
