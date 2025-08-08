"""Tests for synchronization data models."""

import pytest
from datetime import datetime
from decimal import Decimal

from src.pocketsmith_beancount.sync_models import (
    FieldChange,
    SyncTransaction,
    SyncConflict,
    SyncResult,
    SyncSummary,
)
from src.pocketsmith_beancount.sync_enums import (
    ChangeType,
    ResolutionStrategy,
    SyncStatus,
    SyncDirection,
)


class TestFieldChange:
    """Test FieldChange data model."""

    def test_field_change_creation(self):
        """Test creating a FieldChange instance."""
        change = FieldChange(
            field_name="note",
            old_value="old note",
            new_value="new note",
            change_type=ChangeType.LOCAL_ONLY,
            strategy=ResolutionStrategy.LOCAL_CHANGES_ONLY,
        )

        assert change.field_name == "note"
        assert change.old_value == "old note"
        assert change.new_value == "new note"
        assert change.change_type == ChangeType.LOCAL_ONLY
        assert change.strategy == ResolutionStrategy.LOCAL_CHANGES_ONLY
        assert isinstance(change.timestamp, datetime)

    def test_field_change_empty_name_validation(self):
        """Test that empty field names are rejected."""
        with pytest.raises(ValueError, match="Field name cannot be empty"):
            FieldChange(
                field_name="",
                old_value="old",
                new_value="new",
                change_type=ChangeType.LOCAL_ONLY,
                strategy=ResolutionStrategy.LOCAL_CHANGES_ONLY,
            )

    def test_field_change_none_name_validation(self):
        """Test that None field names are rejected."""
        with pytest.raises(ValueError, match="Field name cannot be empty"):
            FieldChange(
                field_name=None,
                old_value="old",
                new_value="new",
                change_type=ChangeType.LOCAL_ONLY,
                strategy=ResolutionStrategy.LOCAL_CHANGES_ONLY,
            )


class TestSyncTransaction:
    """Test SyncTransaction data model."""

    def test_sync_transaction_creation(self):
        """Test creating a SyncTransaction instance."""
        transaction = SyncTransaction(
            id="12345",
            amount=Decimal("100.50"),
            date="2024-01-15",
            merchant="Test Merchant",
            note="Test note",
        )

        assert transaction.id == "12345"
        assert transaction.amount == Decimal("100.50")
        assert transaction.date == "2024-01-15"
        assert transaction.merchant == "Test Merchant"
        assert transaction.note == "Test note"
        assert transaction.labels == []  # Should default to empty list

    def test_sync_transaction_empty_id_validation(self):
        """Test that empty transaction IDs are rejected."""
        with pytest.raises(ValueError, match="Transaction ID cannot be empty"):
            SyncTransaction(id="")

    def test_sync_transaction_none_id_validation(self):
        """Test that None transaction IDs are rejected."""
        with pytest.raises(ValueError, match="Transaction ID cannot be empty"):
            SyncTransaction(id=None)

    def test_sync_transaction_labels_initialization(self):
        """Test that labels are properly initialized as lists."""
        # Test with None labels
        transaction1 = SyncTransaction(id="123", labels=None)
        assert transaction1.labels == []

        # Test with existing list
        transaction2 = SyncTransaction(id="123", labels=["tag1", "tag2"])
        assert transaction2.labels == ["tag1", "tag2"]

        # Test with non-list iterable
        transaction3 = SyncTransaction(id="123", labels=("tag1", "tag2"))
        assert transaction3.labels == ["tag1", "tag2"]


class TestSyncConflict:
    """Test SyncConflict data model."""

    def test_sync_conflict_creation(self):
        """Test creating a SyncConflict instance."""
        conflict = SyncConflict(
            transaction_id="12345",
            field_name="note",
            local_value="local note",
            remote_value="remote note",
            local_timestamp=datetime(2024, 1, 15, 10, 0, 0),
            remote_timestamp=datetime(2024, 1, 15, 11, 0, 0),
            strategy=ResolutionStrategy.REMOTE_WINS,
        )

        assert conflict.transaction_id == "12345"
        assert conflict.field_name == "note"
        assert conflict.local_value == "local note"
        assert conflict.remote_value == "remote note"
        assert conflict.strategy == ResolutionStrategy.REMOTE_WINS
        assert conflict.status == SyncStatus.CONFLICT
        assert "Conflict in field 'note' for transaction 12345" in conflict.message

    def test_sync_conflict_custom_message(self):
        """Test SyncConflict with custom message."""
        custom_message = "Custom conflict message"
        conflict = SyncConflict(
            transaction_id="12345",
            field_name="note",
            local_value="local",
            remote_value="remote",
            local_timestamp=None,
            remote_timestamp=None,
            strategy=ResolutionStrategy.REMOTE_WINS,
            message=custom_message,
        )

        assert conflict.message == custom_message


class TestSyncResult:
    """Test SyncResult data model."""

    def test_sync_result_creation(self):
        """Test creating a SyncResult instance."""
        result = SyncResult(transaction_id="12345", status=SyncStatus.SUCCESS)

        assert result.transaction_id == "12345"
        assert result.status == SyncStatus.SUCCESS
        assert result.changes == []
        assert result.conflicts == []
        assert result.errors == []
        assert result.warnings == []
        assert result.sync_direction == SyncDirection.NO_SYNC
        assert isinstance(result.timestamp, datetime)

    def test_sync_result_properties(self):
        """Test SyncResult boolean properties."""
        result = SyncResult(transaction_id="123", status=SyncStatus.SUCCESS)

        # Initially no changes, conflicts, errors, or warnings
        assert not result.has_changes
        assert not result.has_conflicts
        assert not result.has_errors
        assert not result.has_warnings

        # Add a change
        result.add_change(
            "note",
            "old",
            "new",
            ChangeType.LOCAL_ONLY,
            ResolutionStrategy.LOCAL_CHANGES_ONLY,
        )
        assert result.has_changes

        # Add a conflict
        result.add_conflict("amount", 100, 200, ResolutionStrategy.NEVER_CHANGE)
        assert result.has_conflicts

        # Add an error
        result.add_error("Test error")
        assert result.has_errors

        # Add a warning
        result.add_warning("Test warning")
        assert result.has_warnings

    def test_sync_result_add_change(self):
        """Test adding changes to SyncResult."""
        result = SyncResult(transaction_id="123", status=SyncStatus.SUCCESS)

        result.add_change(
            "note",
            "old note",
            "new note",
            ChangeType.LOCAL_ONLY,
            ResolutionStrategy.LOCAL_CHANGES_ONLY,
        )

        assert len(result.changes) == 1
        change = result.changes[0]
        assert change.field_name == "note"
        assert change.old_value == "old note"
        assert change.new_value == "new note"
        assert change.change_type == ChangeType.LOCAL_ONLY
        assert change.strategy == ResolutionStrategy.LOCAL_CHANGES_ONLY

    def test_sync_result_add_conflict(self):
        """Test adding conflicts to SyncResult."""
        result = SyncResult(transaction_id="123", status=SyncStatus.SUCCESS)

        result.add_conflict(
            "amount",
            100,
            200,
            ResolutionStrategy.NEVER_CHANGE,
            message="Amount conflict",
        )

        assert len(result.conflicts) == 1
        conflict = result.conflicts[0]
        assert conflict.transaction_id == "123"
        assert conflict.field_name == "amount"
        assert conflict.local_value == 100
        assert conflict.remote_value == 200
        assert conflict.strategy == ResolutionStrategy.NEVER_CHANGE
        assert conflict.message == "Amount conflict"


class TestSyncSummary:
    """Test SyncSummary data model."""

    def test_sync_summary_creation(self):
        """Test creating a SyncSummary instance."""
        summary = SyncSummary()

        assert summary.total_transactions == 0
        assert summary.successful_syncs == 0
        assert summary.conflicts_detected == 0
        assert summary.errors_encountered == 0
        assert summary.warnings_generated == 0
        assert summary.changes_made == 0
        assert summary.local_to_remote_updates == 0
        assert summary.remote_to_local_updates == 0
        assert summary.dry_run is False

    def test_sync_summary_properties(self):
        """Test SyncSummary calculated properties."""
        summary = SyncSummary()

        # Test duration with no timestamps
        assert summary.duration is None

        # Test duration with timestamps
        start_time = datetime(2024, 1, 15, 10, 0, 0)
        end_time = datetime(2024, 1, 15, 10, 0, 5)  # 5 seconds later
        summary.start_time = start_time
        summary.end_time = end_time
        assert summary.duration == 5.0

        # Test success rate with no transactions
        assert summary.success_rate == 0.0

        # Test success rate with transactions
        summary.total_transactions = 10
        summary.successful_syncs = 8
        assert summary.success_rate == 80.0

    def test_sync_summary_add_result(self):
        """Test adding results to SyncSummary."""
        summary = SyncSummary()

        # Create a successful result with changes
        result = SyncResult(
            transaction_id="123",
            status=SyncStatus.SUCCESS,
            sync_direction=SyncDirection.LOCAL_TO_REMOTE,
        )
        result.add_change(
            "note",
            "old",
            "new",
            ChangeType.LOCAL_ONLY,
            ResolutionStrategy.LOCAL_CHANGES_ONLY,
        )
        result.add_warning("Test warning")

        summary.add_result(result)

        assert summary.total_transactions == 1
        assert summary.successful_syncs == 1
        assert summary.changes_made == 1
        assert summary.warnings_generated == 1
        assert summary.local_to_remote_updates == 1

        # Create a result with conflicts and errors
        result2 = SyncResult(
            transaction_id="456",
            status=SyncStatus.CONFLICT,
            sync_direction=SyncDirection.REMOTE_TO_LOCAL,
        )
        result2.add_conflict("amount", 100, 200, ResolutionStrategy.NEVER_CHANGE)
        result2.add_error("Test error")

        summary.add_result(result2)

        assert summary.total_transactions == 2
        assert summary.successful_syncs == 1  # Still 1
        assert summary.conflicts_detected == 1
        assert summary.errors_encountered == 1
        assert summary.remote_to_local_updates == 1
