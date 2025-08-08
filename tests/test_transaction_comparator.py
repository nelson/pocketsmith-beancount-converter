"""Tests for transaction comparison logic."""

import pytest
from datetime import datetime
from decimal import Decimal

from src.pocketsmith_beancount.transaction_comparator import (
    PocketSmithTransactionComparator,
)
from src.pocketsmith_beancount.sync_enums import ChangeType, ResolutionStrategy
from src.pocketsmith_beancount.sync_exceptions import TransactionComparisonError


class TestPocketSmithTransactionComparator:
    """Test PocketSmithTransactionComparator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.comparator = PocketSmithTransactionComparator()

    def test_compare_transactions_no_changes(self):
        """Test comparing identical transactions."""
        local_tx = {
            "id": "123",
            "amount": 100.0,
            "note": "Test transaction",
            "labels": ["tag1", "tag2"],
        }
        remote_tx = local_tx.copy()

        changes = self.comparator.compare_transactions(local_tx, remote_tx)
        assert len(changes) == 0

    def test_compare_transactions_with_changes(self):
        """Test comparing transactions with differences."""
        local_tx = {
            "id": "123",
            "amount": 100.0,
            "note": "Local note",
            "labels": ["tag1"],
            "last_modified": "2024-01-15T10:00:00Z",
        }
        remote_tx = {
            "id": "123",
            "amount": 100.0,
            "note": "Remote note",
            "labels": ["tag1", "tag2"],
            "updated_at": "2024-01-15T11:00:00Z",
        }

        changes = self.comparator.compare_transactions(local_tx, remote_tx)

        # Should detect changes in note and labels
        change_fields = {change.field_name for change in changes}
        assert "note" in change_fields
        assert "labels" in change_fields

    def test_compare_transactions_unmapped_fields_ignored(self):
        """Test that unmapped fields are ignored during comparison."""
        local_tx = {"id": "123", "amount": 100.0, "unknown_field": "local value"}
        remote_tx = {"id": "123", "amount": 100.0, "unknown_field": "remote value"}

        changes = self.comparator.compare_transactions(local_tx, remote_tx)

        # Should not detect changes in unmapped fields
        change_fields = {change.field_name for change in changes}
        assert "unknown_field" not in change_fields

    def test_detect_change_type_no_change(self):
        """Test detecting no change when values are equal."""
        change_type = self.comparator.detect_change_type(
            "note", "same value", "same value"
        )
        assert change_type == ChangeType.NO_CHANGE

    def test_detect_change_type_timestamp_field(self):
        """Test that timestamp fields always show remote changes."""
        change_type = self.comparator.detect_change_type(
            "updated_at", "2024-01-15T10:00:00Z", "2024-01-15T11:00:00Z"
        )
        assert change_type == ChangeType.REMOTE_ONLY

    def test_detect_change_type_immutable_field(self, caplog):
        """Test that immutable fields show remote changes with warning."""
        change_type = self.comparator.detect_change_type("amount", 100.0, 150.0)
        assert change_type == ChangeType.REMOTE_ONLY
        assert "Unexpected change in immutable field" in caplog.text

    def test_detect_change_type_with_timestamps_local_newer(self):
        """Test change detection when local timestamp is newer."""
        local_time = datetime(2024, 1, 15, 12, 0, 0)
        remote_time = datetime(2024, 1, 15, 10, 0, 0)

        change_type = self.comparator.detect_change_type(
            "note", "local note", "remote note", local_time, remote_time
        )
        assert change_type == ChangeType.LOCAL_ONLY

    def test_detect_change_type_with_timestamps_remote_newer(self):
        """Test change detection when remote timestamp is newer."""
        local_time = datetime(2024, 1, 15, 10, 0, 0)
        remote_time = datetime(2024, 1, 15, 12, 0, 0)

        change_type = self.comparator.detect_change_type(
            "note", "local note", "remote note", local_time, remote_time
        )
        assert change_type == ChangeType.REMOTE_ONLY

    def test_detect_change_type_with_same_timestamps(self):
        """Test change detection when timestamps are the same."""
        timestamp = datetime(2024, 1, 15, 10, 0, 0)

        change_type = self.comparator.detect_change_type(
            "note", "local note", "remote note", timestamp, timestamp
        )
        assert change_type == ChangeType.BOTH_CHANGED

    def test_detect_change_type_without_timestamps(self):
        """Test change detection without timestamp information."""
        change_type = self.comparator.detect_change_type(
            "note", "local note", "remote note"
        )
        assert change_type == ChangeType.BOTH_CHANGED

    def test_match_transactions_by_id_perfect_match(self):
        """Test matching when all transactions have matches."""
        local_txs = [{"id": "123", "amount": 100}, {"id": "456", "amount": 200}]
        remote_txs = [{"id": "123", "amount": 100}, {"id": "456", "amount": 200}]

        matched, local_only, remote_only = self.comparator.match_transactions_by_id(
            local_txs, remote_txs
        )

        assert len(matched) == 2
        assert len(local_only) == 0
        assert len(remote_only) == 0

    def test_match_transactions_by_id_with_orphans(self):
        """Test matching with orphaned transactions."""
        local_txs = [
            {"id": "123", "amount": 100},
            {"id": "456", "amount": 200},  # Local only
        ]
        remote_txs = [
            {"id": "123", "amount": 100},
            {"id": "789", "amount": 300},  # Remote only
        ]

        matched, local_only, remote_only = self.comparator.match_transactions_by_id(
            local_txs, remote_txs
        )

        assert len(matched) == 1
        assert len(local_only) == 1
        assert len(remote_only) == 1
        assert local_only[0]["id"] == "456"
        assert remote_only[0]["id"] == "789"

    def test_match_transactions_by_id_missing_ids(self, caplog):
        """Test matching when some transactions have missing IDs."""
        local_txs = [
            {"id": "123", "amount": 100},
            {"amount": 200},  # Missing ID
        ]
        remote_txs = [
            {"id": "123", "amount": 100},
        ]

        matched, local_only, remote_only = self.comparator.match_transactions_by_id(
            local_txs, remote_txs
        )

        assert len(matched) == 1
        assert len(local_only) == 0  # Transaction without ID is ignored
        assert len(remote_only) == 0
        assert "No transaction ID found" in caplog.text

    def test_extract_transaction_id_standard_id(self):
        """Test extracting standard ID field."""
        transaction = {"id": "123", "amount": 100}
        tx_id = self.comparator._extract_transaction_id(transaction)
        assert tx_id == "123"

    def test_extract_transaction_id_alternative_fields(self):
        """Test extracting ID from alternative field names."""
        transaction1 = {"transaction_id": "456", "amount": 100}
        tx_id1 = self.comparator._extract_transaction_id(transaction1)
        assert tx_id1 == "456"

        transaction2 = {"pocketsmith_id": "789", "amount": 100}
        tx_id2 = self.comparator._extract_transaction_id(transaction2)
        assert tx_id2 == "789"

    def test_extract_transaction_id_numeric_id(self):
        """Test extracting numeric ID (converted to string)."""
        transaction = {"id": 123, "amount": 100}
        tx_id = self.comparator._extract_transaction_id(transaction)
        assert tx_id == "123"

    def test_extract_transaction_id_missing(self, caplog):
        """Test extracting ID when none exists."""
        transaction = {"amount": 100}
        tx_id = self.comparator._extract_transaction_id(transaction)
        assert tx_id is None
        assert "No transaction ID found" in caplog.text

    def test_normalize_value_list_field(self):
        """Test normalizing list field values."""
        # Test with list
        normalized = self.comparator._normalize_value("labels", ["b", "a", "c"])
        assert normalized == ["a", "b", "c"]  # Should be sorted

        # Test with tuple
        normalized = self.comparator._normalize_value("labels", ("b", "a"))
        assert normalized == ["a", "b"]

        # Test with single value
        normalized = self.comparator._normalize_value("labels", "single")
        assert normalized == ["single"]

        # Test with empty/None
        normalized = self.comparator._normalize_value("labels", None)
        assert normalized is None

        normalized = self.comparator._normalize_value("labels", [])
        assert normalized == []

    def test_normalize_value_decimal_field(self):
        """Test normalizing decimal field values."""
        # Test with float
        normalized = self.comparator._normalize_value("amount", 100.50)
        assert normalized == Decimal("100.50")

        # Test with string
        normalized = self.comparator._normalize_value("amount", "100.50")
        assert normalized == Decimal("100.50")

        # Test with int
        normalized = self.comparator._normalize_value("amount", 100)
        assert normalized == Decimal("100")

        # Test with invalid value
        normalized = self.comparator._normalize_value("amount", "invalid")
        assert normalized == "invalid"  # Should return original on error

    def test_normalize_value_string_field(self):
        """Test normalizing string field values."""
        normalized = self.comparator._normalize_value("note", "  test note  ")
        assert normalized == "test note"  # Should strip whitespace

    def test_values_equal_basic_types(self):
        """Test value equality for basic types."""
        assert self.comparator._values_equal(None, None) is True
        assert self.comparator._values_equal(None, "value") is False
        assert self.comparator._values_equal("value", None) is False
        assert self.comparator._values_equal("same", "same") is True
        assert self.comparator._values_equal("different", "values") is False

    def test_values_equal_lists(self):
        """Test value equality for lists."""
        assert self.comparator._values_equal([1, 2, 3], [1, 2, 3]) is True
        assert self.comparator._values_equal([1, 2], [1, 2, 3]) is False
        assert self.comparator._values_equal([], []) is True

    def test_values_equal_decimals(self):
        """Test value equality for decimals."""
        assert (
            self.comparator._values_equal(Decimal("100.50"), Decimal("100.50")) is True
        )
        assert (
            self.comparator._values_equal(Decimal("100.50"), Decimal("100.51")) is False
        )

    def test_parse_timestamp_datetime_object(self):
        """Test parsing datetime object."""
        dt = datetime(2024, 1, 15, 10, 0, 0)
        parsed = self.comparator._parse_timestamp(dt)
        assert parsed == dt

    def test_parse_timestamp_iso_string(self):
        """Test parsing ISO format string."""
        parsed = self.comparator._parse_timestamp("2024-01-15T10:00:00Z")
        expected = datetime(2024, 1, 15, 10, 0, 0)
        assert parsed.replace(tzinfo=None) == expected

    def test_parse_timestamp_standard_string(self):
        """Test parsing standard datetime string."""
        parsed = self.comparator._parse_timestamp("2024-01-15 10:00:00")
        expected = datetime(2024, 1, 15, 10, 0, 0)
        assert parsed == expected

    def test_parse_timestamp_invalid_string(self, caplog):
        """Test parsing invalid timestamp string."""
        parsed = self.comparator._parse_timestamp("invalid timestamp")
        assert parsed is None
        assert "Could not parse timestamp" in caplog.text

    def test_parse_timestamp_none(self):
        """Test parsing None timestamp."""
        parsed = self.comparator._parse_timestamp(None)
        assert parsed is None

    def test_detect_significant_changes_writable_fields(self):
        """Test that changes to writable fields are always significant."""
        from src.pocketsmith_beancount.sync_models import FieldChange

        changes = [
            FieldChange(
                "note",
                "old",
                "new",
                ChangeType.LOCAL_ONLY,
                ResolutionStrategy.LOCAL_CHANGES_ONLY,
            ),
            FieldChange(
                "amount",
                100,
                200,
                ChangeType.REMOTE_ONLY,
                ResolutionStrategy.NEVER_CHANGE,
            ),
        ]

        significant = self.comparator.detect_significant_changes(changes)

        # Both should be significant (note is writable, amount is immutable)
        assert len(significant) == 2

    def test_detect_significant_changes_timestamp_fields(self):
        """Test that timestamp changes are considered significant."""
        from src.pocketsmith_beancount.sync_models import FieldChange

        changes = [
            FieldChange(
                "updated_at",
                "2024-01-15",
                "2024-01-16",
                ChangeType.REMOTE_ONLY,
                ResolutionStrategy.REMOTE_CHANGES_ONLY,
            )
        ]

        significant = self.comparator.detect_significant_changes(changes)
        assert len(significant) == 1

    def test_is_substantial_change_whitespace(self):
        """Test that whitespace-only changes are not substantial."""
        from src.pocketsmith_beancount.sync_models import FieldChange

        change = FieldChange(
            "note",
            "test note",
            "  test note  ",
            ChangeType.LOCAL_ONLY,
            ResolutionStrategy.LOCAL_CHANGES_ONLY,
        )

        assert self.comparator._is_substantial_change(change) is False

    def test_is_substantial_change_small_numeric_difference(self):
        """Test that small numeric differences are not substantial."""
        from src.pocketsmith_beancount.sync_models import FieldChange

        change = FieldChange(
            "amount",
            100.001,
            100.002,
            ChangeType.REMOTE_ONLY,
            ResolutionStrategy.NEVER_CHANGE,
        )

        assert self.comparator._is_substantial_change(change) is False

    def test_is_substantial_change_large_numeric_difference(self):
        """Test that large numeric differences are substantial."""
        from src.pocketsmith_beancount.sync_models import FieldChange

        change = FieldChange(
            "amount",
            100.0,
            200.0,
            ChangeType.REMOTE_ONLY,
            ResolutionStrategy.NEVER_CHANGE,
        )

        assert self.comparator._is_substantial_change(change) is True

    def test_compare_transactions_error_handling(self):
        """Test error handling during transaction comparison."""
        # Create a transaction that will cause an error
        local_tx = {"id": "123", "problematic_field": "value1"}
        remote_tx = {"id": "123", "problematic_field": "value2"}

        # Mock the field mapping to raise an exception
        original_get_all_fields = self.comparator.field_mapping.get_all_fields
        self.comparator.field_mapping.get_all_fields = lambda: {"problematic_field"}

        # Mock get_strategy to raise an exception
        def mock_get_strategy(field_name):
            if field_name == "problematic_field":
                raise ValueError("Test error")
            return ResolutionStrategy.NEVER_CHANGE

        self.comparator.field_mapping.get_strategy = mock_get_strategy

        try:
            with pytest.raises(
                TransactionComparisonError, match="Failed to compare field"
            ):
                self.comparator.compare_transactions(local_tx, remote_tx)
        finally:
            # Restore original method
            self.comparator.field_mapping.get_all_fields = original_get_all_fields
