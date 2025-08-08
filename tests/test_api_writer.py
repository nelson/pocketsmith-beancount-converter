"""Tests for API write-back functionality."""

import pytest
from unittest.mock import Mock, patch
import requests

from src.pocketsmith_beancount.api_writer import (
    PocketSmithAPIWriter,
    RateLimiter,
    MockAPIWriter,
)
from src.pocketsmith_beancount.sync_exceptions import APIWriteBackError


class TestPocketSmithAPIWriter:
    """Test PocketSmithAPIWriter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.api_writer = PocketSmithAPIWriter("test_api_key")

    def test_init(self):
        """Test API writer initialization."""
        assert self.api_writer.api_key == "test_api_key"
        assert self.api_writer.base_url == "https://api.pocketsmith.com/v2"
        assert "X-Developer-Key" in self.api_writer.headers
        assert self.api_writer.headers["X-Developer-Key"] == "test_api_key"

    @patch("src.pocketsmith_beancount.api_writer.requests.put")
    def test_update_transaction_success(self, mock_put):
        """Test successful transaction update."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123", "note": "updated note"}
        mock_put.return_value = mock_response

        updates = {"note": "updated note"}
        result = self.api_writer.update_transaction("123", updates)

        assert result is True
        mock_put.assert_called_once()

        # Check the API call was made correctly
        call_args = mock_put.call_args
        assert "transactions/123" in call_args[0][0]  # URL is first positional arg
        assert call_args[1]["json"] == {"note": "updated note"}

    @patch("src.pocketsmith_beancount.api_writer.requests.put")
    def test_update_transaction_dry_run(self, mock_put):
        """Test transaction update in dry run mode."""
        updates = {"note": "updated note"}
        result = self.api_writer.update_transaction("123", updates, dry_run=True)

        assert result is True
        mock_put.assert_not_called()  # Should not make actual API call

    @patch("src.pocketsmith_beancount.api_writer.requests.put")
    def test_update_transaction_api_error(self, mock_put):
        """Test transaction update with API error."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_put.return_value = mock_response

        updates = {"note": "updated note"}

        with pytest.raises(APIWriteBackError, match="Failed to update transaction 123"):
            self.api_writer.update_transaction("123", updates)

    @patch("src.pocketsmith_beancount.api_writer.requests.put")
    @patch("src.pocketsmith_beancount.api_writer.time.sleep")
    def test_update_transaction_rate_limited(self, mock_sleep, mock_put):
        """Test transaction update with rate limiting."""
        # First call returns 429, second call succeeds
        rate_limited_response = Mock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {"Retry-After": "30"}

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"id": "123"}

        mock_put.side_effect = [rate_limited_response, success_response]

        updates = {"note": "updated note"}
        result = self.api_writer.update_transaction("123", updates)

        assert result is True
        assert mock_put.call_count == 2  # Should retry after rate limit
        mock_sleep.assert_called_once_with(30)  # Should sleep for retry-after time

    @patch("src.pocketsmith_beancount.api_writer.requests.put")
    def test_update_transaction_network_error(self, mock_put):
        """Test transaction update with network error."""
        mock_put.side_effect = requests.RequestException("Network error")

        updates = {"note": "updated note"}

        with pytest.raises(
            APIWriteBackError, match="Network error updating transaction"
        ):
            self.api_writer.update_transaction("123", updates)

    def test_validate_update_data_valid(self):
        """Test validation with valid update data."""
        updates = {"note": "valid note", "labels": ["tag1", "tag2"]}
        result = self.api_writer.validate_update_data("123", updates)
        assert result is True

    def test_validate_update_data_empty_transaction_id(self):
        """Test validation with empty transaction ID."""
        updates = {"note": "valid note"}
        result = self.api_writer.validate_update_data("", updates)
        assert result is False

    def test_validate_update_data_empty_updates(self):
        """Test validation with empty updates."""
        result = self.api_writer.validate_update_data("123", {})
        assert result is False

    def test_validate_update_data_non_writable_field(self):
        """Test validation with non-writable field."""
        updates = {"amount": 100.0}  # amount is not writable
        result = self.api_writer.validate_update_data("123", updates)
        assert result is False

    def test_convert_to_api_format_note(self):
        """Test converting note field to API format."""
        updates = {"note": "test note"}
        api_updates = self.api_writer._convert_to_api_format(updates)
        assert api_updates == {"note": "test note"}

    def test_convert_to_api_format_labels(self):
        """Test converting labels field to API format."""
        updates = {"labels": ["tag1", "tag2"]}
        api_updates = self.api_writer._convert_to_api_format(updates)
        assert api_updates == {"labels": ["tag1", "tag2"]}

    def test_convert_to_api_format_tags_to_labels(self):
        """Test converting tags field to labels in API format."""
        updates = {"tags": ["tag1", "tag2"]}
        api_updates = self.api_writer._convert_to_api_format(updates)
        assert api_updates == {"labels": ["tag1", "tag2"]}

    def test_convert_value_to_api_format_labels_list(self):
        """Test converting labels list to API format."""
        result = self.api_writer._convert_value_to_api_format(
            "labels", ["tag1", "tag2"]
        )
        assert result == ["tag1", "tag2"]

    def test_convert_value_to_api_format_labels_single(self):
        """Test converting single label to API format."""
        result = self.api_writer._convert_value_to_api_format("labels", "single_tag")
        assert result == ["single_tag"]

    def test_convert_value_to_api_format_labels_empty(self):
        """Test converting empty labels to API format."""
        result = self.api_writer._convert_value_to_api_format("labels", None)
        assert result == []

        result = self.api_writer._convert_value_to_api_format("labels", [])
        assert result == []

    def test_convert_value_to_api_format_note(self):
        """Test converting note to API format."""
        result = self.api_writer._convert_value_to_api_format("note", "test note")
        assert result == "test note"

        result = self.api_writer._convert_value_to_api_format("note", None)
        assert result == ""

    def test_validate_field_value_labels_valid(self):
        """Test validating valid labels."""
        assert self.api_writer._validate_field_value("labels", ["tag1", "tag2"]) is True
        assert self.api_writer._validate_field_value("labels", "single_tag") is True
        assert self.api_writer._validate_field_value("labels", None) is True

    def test_validate_field_value_labels_invalid(self):
        """Test validating invalid labels."""
        assert (
            self.api_writer._validate_field_value("labels", [{"invalid": "object"}])
            is False
        )

    def test_validate_field_value_note_valid(self):
        """Test validating valid notes."""
        assert self.api_writer._validate_field_value("note", "valid note") is True
        assert self.api_writer._validate_field_value("note", None) is True

    def test_batch_update_transactions_success(self):
        """Test successful batch update."""
        # Mock the update_transaction method
        self.api_writer.update_transaction = Mock(return_value=True)

        updates = [
            {"transaction_id": "123", "note": "note 1"},
            {"transaction_id": "456", "note": "note 2"},
        ]

        results = self.api_writer.batch_update_transactions(updates)

        assert results == [True, True]
        assert self.api_writer.update_transaction.call_count == 2

    def test_batch_update_transactions_partial_failure(self):
        """Test batch update with partial failures."""

        # Mock update_transaction to fail for second transaction
        def mock_update(tx_id, updates, dry_run=False):
            if tx_id == "456":
                raise APIWriteBackError("Mock failure")
            return True

        self.api_writer.update_transaction = Mock(side_effect=mock_update)

        updates = [
            {"transaction_id": "123", "note": "note 1"},
            {"transaction_id": "456", "note": "note 2"},
        ]

        results = self.api_writer.batch_update_transactions(updates)

        assert results == [True, False]

    def test_batch_update_transactions_missing_id(self):
        """Test batch update with missing transaction ID."""
        updates = [{"note": "note without ID"}]

        results = self.api_writer.batch_update_transactions(updates)

        assert results == [False]


class TestRateLimiter:
    """Test RateLimiter."""

    def test_init(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(requests_per_second=2.0)
        assert limiter.requests_per_second == 2.0
        assert limiter.min_interval == 0.5

    @patch("src.pocketsmith_beancount.api_writer.time.sleep")
    @patch("src.pocketsmith_beancount.api_writer.time.time")
    def test_wait_if_needed_rate_limited(self, mock_time, mock_sleep):
        """Test waiting when rate limited."""
        limiter = RateLimiter(requests_per_second=2.0)  # 0.5 second intervals

        # Simulate time progression
        mock_time.side_effect = [
            1.2,  # current time for time_since_last calculation
            1.7,  # time after sleep for updating last_request_time
        ]
        limiter.last_request_time = 1.0  # Last request was at time 1.0

        limiter.wait_if_needed()

        # time_since_last = 1.2 - 1.0 = 0.2
        # sleep_time = 0.5 - 0.2 = 0.3
        # Check that sleep was called once with approximately 0.3
        mock_sleep.assert_called_once()
        call_args = mock_sleep.call_args[0]
        assert abs(call_args[0] - 0.3) < 0.001  # Allow small floating point differences

    @patch("src.pocketsmith_beancount.api_writer.time.sleep")
    @patch("src.pocketsmith_beancount.api_writer.time.time")
    def test_wait_if_needed_no_limit(self, mock_time, mock_sleep):
        """Test no waiting when not rate limited."""
        limiter = RateLimiter(requests_per_second=2.0)  # 0.5 second intervals

        # Simulate time progression - enough time has passed
        mock_time.side_effect = [2.0, 2.0]  # current time, update last_request_time
        limiter.last_request_time = 1.0  # Last request was 1 second ago

        limiter.wait_if_needed()

        # Should not sleep
        mock_sleep.assert_not_called()


class TestMockAPIWriter:
    """Test MockAPIWriter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_writer = MockAPIWriter()

    def test_update_transaction_success(self):
        """Test successful mock update."""
        updates = {"note": "test note"}
        result = self.mock_writer.update_transaction("123", updates)

        assert result is True
        updates_made = self.mock_writer.get_updates_made()
        assert len(updates_made) == 1
        assert updates_made[0]["transaction_id"] == "123"
        assert updates_made[0]["updates"] == updates
        assert updates_made[0]["dry_run"] is False

    def test_update_transaction_dry_run(self):
        """Test mock update in dry run mode."""
        updates = {"note": "test note"}
        result = self.mock_writer.update_transaction("123", updates, dry_run=True)

        assert result is True
        updates_made = self.mock_writer.get_updates_made()
        assert updates_made[0]["dry_run"] is True

    def test_update_transaction_configured_failure(self):
        """Test mock update with configured failure."""
        self.mock_writer.set_should_fail(True)

        updates = {"note": "test note"}
        with pytest.raises(APIWriteBackError):
            self.mock_writer.update_transaction("123", updates)

    def test_update_transaction_specific_failure(self):
        """Test mock update with failure for specific transaction."""
        self.mock_writer.set_fail_for_transaction("456")

        # This should succeed
        result1 = self.mock_writer.update_transaction("123", {"note": "note 1"})
        assert result1 is True

        # This should fail
        with pytest.raises(APIWriteBackError):
            self.mock_writer.update_transaction("456", {"note": "note 2"})

    def test_batch_update_transactions(self):
        """Test mock batch update."""
        updates = [
            {"transaction_id": "123", "note": "note 1"},
            {"transaction_id": "456", "note": "note 2"},
        ]

        results = self.mock_writer.batch_update_transactions(updates)

        assert results == [True, True]
        updates_made = self.mock_writer.get_updates_made()
        assert len(updates_made) == 2

    def test_clear_updates(self):
        """Test clearing updates made."""
        self.mock_writer.update_transaction("123", {"note": "test"})
        assert len(self.mock_writer.get_updates_made()) == 1

        self.mock_writer.clear_updates()
        assert len(self.mock_writer.get_updates_made()) == 0

    def test_validate_update_data(self):
        """Test mock validation."""
        result = self.mock_writer.validate_update_data("123", {"note": "test"})
        assert result is True
