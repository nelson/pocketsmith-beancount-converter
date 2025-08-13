"""Tests for pocketsmith.common module functionality."""

import pytest
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st

from src.pocketsmith.common import (
    PocketSmithClient,
    PocketSmithAPIError,
    RateLimiter,
    validate_update_data,
    convert_to_api_format,
)


class TestPocketSmithAPIError:
    """Test PocketSmithAPIError exception class."""

    def test_pocketsmith_api_error_creation(self):
        """Test creating PocketSmithAPIError with message."""
        error = PocketSmithAPIError("Test API error")
        assert str(error) == "Test API error"
        assert isinstance(error, Exception)

    def test_pocketsmith_api_error_with_status_code(self):
        """Test creating PocketSmithAPIError with status code."""
        error = PocketSmithAPIError("API error", status_code=404)
        assert str(error) == "API error"
        assert error.status_code == 404

    def test_pocketsmith_api_error_with_response_body(self):
        """Test creating PocketSmithAPIError with response body."""
        error = PocketSmithAPIError("API error", response_body='{"error": "Not found"}')
        assert error.response_body == '{"error": "Not found"}'

    def test_pocketsmith_api_error_with_transaction_id(self):
        """Test creating PocketSmithAPIError with transaction ID."""
        error = PocketSmithAPIError("API error", transaction_id="12345")
        assert error.transaction_id == "12345"


class TestRateLimiter:
    """Test RateLimiter functionality."""

    def test_rate_limiter_init_default(self):
        """Test RateLimiter initialization with defaults."""
        limiter = RateLimiter()
        assert limiter.requests_per_second == 2.0
        assert limiter.min_interval == 0.5  # 1.0 / 2.0
        assert limiter.last_request_time == 0.0

    def test_rate_limiter_init_custom(self):
        """Test RateLimiter initialization with custom values."""
        limiter = RateLimiter(requests_per_second=5.0)
        assert limiter.requests_per_second == 5.0
        assert limiter.min_interval == 0.2  # 1.0 / 5.0

    @patch("time.sleep")
    @patch("time.time")
    def test_wait_if_needed_requires_wait(self, mock_time, mock_sleep):
        """Test wait_if_needed when rate limiting is required."""
        limiter = RateLimiter(requests_per_second=2.0)
        limiter.last_request_time = 10.0

        # Mock time progression: current time is too close to last request
        mock_time.side_effect = [10.3, 10.3, 10.8]  # current, current, after sleep

        limiter.wait_if_needed()

        # Should have slept for 0.2 seconds (0.5 - 0.3)
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert (
            abs(sleep_time - 0.2) < 0.01
        )  # Allow for small floating point differences

    @patch("time.sleep")
    @patch("time.time")
    def test_wait_if_needed_no_wait_required(self, mock_time, mock_sleep):
        """Test wait_if_needed when no waiting is required."""
        limiter = RateLimiter(requests_per_second=2.0)
        limiter.last_request_time = 10.0

        # Mock time: enough time has passed
        mock_time.side_effect = [11.0, 11.0]

        limiter.wait_if_needed()

        # Should not have slept
        mock_sleep.assert_not_called()


class TestPocketSmithClient:
    """Test PocketSmithClient functionality."""

    def test_client_init_with_api_key(self):
        """Test client initialization with API key."""
        client = PocketSmithClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client.base_url == "https://api.pocketsmith.com/v2"
        assert client.headers["X-Developer-Key"] == "test_key"
        assert client.headers["Accept"] == "application/json"

    def test_client_init_without_api_key(self):
        """Test client initialization without API key raises error."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                PocketSmithClient()
            assert "PocketSmith API key is required" in str(exc_info.value)

    def test_client_init_with_env_api_key(self):
        """Test client initialization with environment API key."""
        with patch.dict("os.environ", {"POCKETSMITH_API_KEY": "env_key"}):
            client = PocketSmithClient()
            assert client.api_key == "env_key"

    def test_client_init_custom_base_url(self):
        """Test client initialization with custom base URL."""
        client = PocketSmithClient(
            api_key="test_key", base_url="https://custom.api.com/v1"
        )
        assert client.base_url == "https://custom.api.com/v1"

    @patch("requests.get")
    def test_make_request_success(self, mock_get):
        """Test successful GET request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"id": "123", "name": "Test"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = PocketSmithClient(api_key="test_key")
        result = client._make_request("test-endpoint")

        assert result == {"id": "123", "name": "Test"}

        # Verify request was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        expected_url = "https://api.pocketsmith.com/v2/test-endpoint"
        assert call_args[0][0] == expected_url
        assert call_args[1]["headers"]["X-Developer-Key"] == "test_key"

    @patch("requests.get")
    def test_make_request_with_params(self, mock_get):
        """Test GET request with parameters."""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = PocketSmithClient(api_key="test_key")
        client._make_request("test-endpoint", params={"limit": 10, "page": 1})

        call_args = mock_get.call_args
        assert call_args[1]["params"] == {"limit": 10, "page": 1}

    @patch("requests.put")
    def test_make_put_request_success(self, mock_put):
        """Test successful PUT request."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "123", "updated": True}
        mock_response.raise_for_status.return_value = None
        mock_put.return_value = mock_response

        client = PocketSmithClient(api_key="test_key")
        data = {"name": "Updated Transaction"}
        result = client._make_put_request("transactions/123", data=data)

        assert result == {"id": "123", "updated": True}
        call_args = mock_put.call_args
        assert call_args[1]["json"] == data
        assert call_args[1]["headers"]["Content-Type"] == "application/json"

    @patch("requests.patch")
    def test_make_patch_request_success(self, mock_patch):
        """Test successful PATCH request."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "123", "patched": True}
        mock_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_response

        client = PocketSmithClient(api_key="test_key")
        data = {"note": "Updated note"}
        result = client._make_patch_request("transactions/123", data=data)

        assert result == {"id": "123", "patched": True}
        call_args = mock_patch.call_args
        assert call_args[1]["json"] == data

    def test_parse_link_header_valid(self):
        """Test parsing valid Link headers."""
        client = PocketSmithClient(api_key="test_key")
        link_header = '<https://api.pocketsmith.com/v2/transactions?page=2>; rel="next", <https://api.pocketsmith.com/v2/transactions?page=1>; rel="prev"'

        links = client._parse_link_header(link_header)

        assert "next" in links
        assert "prev" in links
        assert links["next"] == "https://api.pocketsmith.com/v2/transactions?page=2"
        assert links["prev"] == "https://api.pocketsmith.com/v2/transactions?page=1"

    def test_parse_link_header_empty(self):
        """Test parsing empty Link header."""
        client = PocketSmithClient(api_key="test_key")
        links = client._parse_link_header("")
        assert links == {}

        links = client._parse_link_header(None)
        assert links == {}

    def test_parse_link_header_malformed(self):
        """Test parsing malformed Link header."""
        client = PocketSmithClient(api_key="test_key")
        # Malformed header without proper format
        link_header = "not-a-valid-link-header"
        links = client._parse_link_header(link_header)
        assert links == {}


class TestValidateUpdateData:
    """Test update data validation functionality."""

    def test_validate_empty_updates(self):
        """Test validation of empty updates."""
        assert not validate_update_data({})
        assert not validate_update_data(None)

    def test_validate_valid_updates(self):
        """Test validation of valid update data."""
        updates = {
            "note": "Updated note",
            "labels": ["tag1", "tag2"],
            "memo": "Updated memo",
        }
        assert validate_update_data(updates)

    def test_validate_invalid_labels(self):
        """Test validation rejects invalid label types."""
        updates = {"labels": {"invalid": "type"}}
        assert not validate_update_data(updates)

    def test_validate_invalid_note(self):
        """Test validation rejects invalid note types."""
        updates = {"note": 12345}  # Should be string
        assert not validate_update_data(updates)


class TestConvertToApiFormat:
    """Test API format conversion functionality."""

    def test_convert_basic_fields(self):
        """Test conversion of basic fields."""
        updates = {"note": "Test note", "memo": "Test memo"}

        result = convert_to_api_format(updates)

        assert result["note"] == "Test note"
        assert result["memo"] == "Test memo"

    def test_convert_labels_list(self):
        """Test conversion of labels as list."""
        updates = {"labels": ["tag1", "tag2", "tag3"]}

        result = convert_to_api_format(updates)

        assert result["labels"] == ["tag1", "tag2", "tag3"]

    def test_convert_tags_to_labels(self):
        """Test conversion of tags field to labels in API."""
        updates = {"tags": ["tag1", "tag2"]}

        result = convert_to_api_format(updates)

        assert result["labels"] == ["tag1", "tag2"]
        assert "tags" not in result

    def test_convert_labels_single_value(self):
        """Test conversion of single label value to list."""
        updates = {"labels": "single-tag"}

        result = convert_to_api_format(updates)

        assert result["labels"] == ["single-tag"]

    def test_convert_empty_labels(self):
        """Test conversion of empty/None labels."""
        updates = {"labels": None}

        result = convert_to_api_format(updates)

        assert result["labels"] == []

    def test_convert_note_to_string(self):
        """Test conversion of note to string."""
        updates = {"note": None}

        result = convert_to_api_format(updates)

        assert result["note"] == ""


class TestPropertyBasedTests:
    """Property-based tests for common functionality."""

    @given(st.floats(min_value=0.1, max_value=100.0))
    def test_rate_limiter_requests_per_second_property(self, rps):
        """Property test: rate limiter should respect requests_per_second setting."""
        limiter = RateLimiter(requests_per_second=rps)

        assert limiter.requests_per_second == rps
        expected_interval = 1.0 / rps
        assert abs(limiter.min_interval - expected_interval) < 0.0001

    @given(st.text(min_size=1, max_size=100))
    def test_client_api_key_property(self, api_key):
        """Property test: client should store and use any valid API key."""
        client = PocketSmithClient(api_key=api_key)
        assert client.api_key == api_key
        assert client.headers["X-Developer-Key"] == api_key

    @given(
        st.dictionaries(
            keys=st.sampled_from(["note", "memo", "labels", "tags"]),
            values=st.one_of(
                st.text(max_size=100),
                st.lists(st.text(max_size=20), max_size=10),
                st.none(),
            ),
            min_size=1,
            max_size=4,
        )
    )
    def test_convert_to_api_format_property(self, updates):
        """Property test: API format conversion should handle various inputs."""
        result = convert_to_api_format(updates)

        # Should always return a dict
        assert isinstance(result, dict)

        # Should not contain 'tags' key (converted to 'labels')
        assert "tags" not in result

        # Labels should always be lists
        if "labels" in result:
            assert isinstance(result["labels"], list)

        # Notes should always be strings
        if "note" in result:
            assert isinstance(result["note"], str)
        if "memo" in result:
            assert isinstance(result["memo"], str)
