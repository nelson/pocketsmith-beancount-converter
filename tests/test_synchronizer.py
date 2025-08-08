"""Tests for synchronization orchestrator."""

import pytest
from unittest.mock import Mock

from src.pocketsmith_beancount.synchronizer import (
    PocketSmithSynchronizer,
    ConsoleSyncLogger,
)
from src.pocketsmith_beancount.api_writer import MockAPIWriter
from src.pocketsmith_beancount.sync_models import SyncResult
from src.pocketsmith_beancount.sync_enums import SyncStatus
from src.pocketsmith_beancount.sync_exceptions import (
    SynchronizationError,
    DataIntegrityError,
)


class TestPocketSmithSynchronizer:
    """Test PocketSmithSynchronizer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_api_writer = MockAPIWriter()
        self.mock_changelog = Mock()
        self.synchronizer = PocketSmithSynchronizer(
            api_writer=self.mock_api_writer, changelog=self.mock_changelog
        )

    def test_init(self):
        """Test synchronizer initialization."""
        assert self.synchronizer.api_writer == self.mock_api_writer
        assert self.synchronizer.changelog == self.mock_changelog
        assert self.synchronizer.comparator is not None
        assert self.synchronizer.resolution_engine is not None
        assert self.synchronizer.sync_logger is not None

    def test_synchronize_no_transactions(self):
        """Test synchronization with no transactions."""
        results = self.synchronizer.synchronize([], [])
        assert len(results) == 0

    def test_synchronize_identical_transactions(self):
        """Test synchronization with identical transactions."""
        local_txs = [
            {"id": "123", "amount": 100.0, "note": "test", "date": "2024-01-15"}
        ]
        remote_txs = [
            {"id": "123", "amount": 100.0, "note": "test", "date": "2024-01-15"}
        ]

        results = self.synchronizer.synchronize(local_txs, remote_txs)

        assert len(results) == 1
        assert results[0].transaction_id == "123"
        assert results[0].status == SyncStatus.SUCCESS
        assert not results[
            0
        ].has_changes  # No changes expected for identical transactions

    def test_synchronize_with_local_changes(self):
        """Test synchronization with local changes that need write-back."""
        local_txs = [{"id": "123", "amount": 100.0, "note": "local note"}]
        remote_txs = [
            {"id": "123", "amount": 100.0, "note": "remote note", "date": "2024-01-15"}
        ]

        results = self.synchronizer.synchronize(local_txs, remote_txs)

        assert len(results) == 1
        result = results[0]
        assert result.transaction_id == "123"
        assert result.status == SyncStatus.SUCCESS

        # Check that API writer was called for write-back
        updates_made = self.mock_api_writer.get_updates_made()
        assert len(updates_made) > 0
        assert updates_made[0]["transaction_id"] == "123"

    def test_synchronize_dry_run(self):
        """Test synchronization in dry run mode."""
        local_txs = [{"id": "123", "amount": 100.0, "note": "local note"}]
        remote_txs = [
            {"id": "123", "amount": 100.0, "note": "remote note", "date": "2024-01-15"}
        ]

        results = self.synchronizer.synchronize(local_txs, remote_txs, dry_run=True)

        assert len(results) == 1

        # Check that API writer was called in dry run mode
        updates_made = self.mock_api_writer.get_updates_made()
        assert len(updates_made) > 0
        assert updates_made[0]["dry_run"] is True

    def test_synchronize_with_orphaned_transactions(self):
        """Test synchronization with orphaned transactions."""
        local_txs = [
            {"id": "123", "amount": 100.0, "note": "matched"},
            {"id": "456", "amount": 200.0, "note": "local only"},
        ]
        remote_txs = [
            {"id": "123", "amount": 100.0, "note": "matched", "date": "2024-01-15"},
            {"id": "789", "amount": 300.0, "note": "remote only", "date": "2024-01-16"},
        ]

        results = self.synchronizer.synchronize(local_txs, remote_txs)

        assert len(results) == 3  # 1 matched + 1 local-only + 1 remote-only

        # Find results by transaction ID
        results_by_id = {r.transaction_id: r for r in results}

        assert "123" in results_by_id  # Matched transaction
        assert "456" in results_by_id  # Local-only transaction
        assert "789" in results_by_id  # Remote-only transaction

        # Local-only and remote-only should be skipped for now
        assert results_by_id["456"].status == SyncStatus.SKIPPED
        assert results_by_id["789"].status == SyncStatus.SKIPPED

    def test_synchronize_with_api_write_failure(self):
        """Test synchronization when API write-back fails."""
        # Configure mock API writer to fail
        self.mock_api_writer.set_should_fail(True)

        local_txs = [{"id": "123", "amount": 100.0, "note": "local note"}]
        remote_txs = [
            {"id": "123", "amount": 100.0, "note": "remote note", "date": "2024-01-15"}
        ]

        results = self.synchronizer.synchronize(local_txs, remote_txs)

        assert len(results) == 1
        result = results[0]
        assert result.status == SyncStatus.ERROR
        assert result.has_errors

    def test_synchronize_with_changelog_logging(self):
        """Test that changes are logged to changelog."""
        local_txs = [{"id": "123", "amount": 100.0, "note": "local note"}]
        remote_txs = [
            {"id": "123", "amount": 100.0, "note": "remote note", "date": "2024-01-15"}
        ]

        self.synchronizer.synchronize(local_txs, remote_txs)

        # Check that changelog was called
        assert self.mock_changelog.log_transaction_modify.called
        call_args = self.mock_changelog.log_transaction_modify.call_args
        assert call_args[0][0] == "123"  # transaction_id
        assert isinstance(call_args[0][1], dict)  # field_changes

    def test_prepare_sync_valid_data(self):
        """Test sync preparation with valid data."""
        local_txs = [{"id": "123", "amount": 100.0}]
        remote_txs = [{"id": "123", "amount": 100.0, "date": "2024-01-15"}]

        result = self.synchronizer.prepare_sync(local_txs, remote_txs)
        assert result is True

    def test_prepare_sync_invalid_local_data(self):
        """Test sync preparation with invalid local data."""
        local_txs = ["invalid_data"]  # Should be dict, not string
        remote_txs = [{"id": "123", "amount": 100.0}]

        result = self.synchronizer.prepare_sync(local_txs, remote_txs)
        assert result is False

    def test_prepare_sync_missing_transaction_id(self):
        """Test sync preparation with missing transaction ID."""
        local_txs = [{"amount": 100.0}]  # Missing ID
        remote_txs = [{"id": "123", "amount": 100.0}]

        result = self.synchronizer.prepare_sync(local_txs, remote_txs)
        assert result is False

    def test_prepare_sync_missing_required_remote_fields(self):
        """Test sync preparation with missing required remote fields."""
        local_txs = [{"id": "123", "amount": 100.0}]
        remote_txs = [{"id": "123"}]  # Missing amount and date

        result = self.synchronizer.prepare_sync(local_txs, remote_txs)
        assert result is False

    def test_validate_transaction_data_valid(self):
        """Test transaction data validation with valid data."""
        transactions = [
            {"id": "123", "amount": 100.0, "date": "2024-01-15"},
            {"id": "456", "amount": 200.0, "date": "2024-01-16"},
        ]

        # Should not raise exception
        self.synchronizer._validate_transaction_data(transactions, "remote")

    def test_validate_transaction_data_invalid_type(self):
        """Test transaction data validation with invalid type."""
        transactions = ["not_a_dict"]

        with pytest.raises(DataIntegrityError, match="not a dictionary"):
            self.synchronizer._validate_transaction_data(transactions, "local")

    def test_validate_transaction_data_missing_id(self):
        """Test transaction data validation with missing ID."""
        transactions = [{"amount": 100.0}]

        with pytest.raises(DataIntegrityError, match="Missing transaction ID"):
            self.synchronizer._validate_transaction_data(transactions, "local")

    def test_validate_transaction_data_missing_amount_remote(self):
        """Test transaction data validation with missing amount in remote data."""
        transactions = [{"id": "123", "date": "2024-01-15"}]

        with pytest.raises(DataIntegrityError, match="Missing amount field"):
            self.synchronizer._validate_transaction_data(transactions, "remote")

    def test_validate_transaction_data_missing_date_remote(self):
        """Test transaction data validation with missing date in remote data."""
        transactions = [{"id": "123", "amount": 100.0}]

        with pytest.raises(DataIntegrityError, match="Missing date field"):
            self.synchronizer._validate_transaction_data(transactions, "remote")

    def test_sync_transaction_pair_success(self):
        """Test syncing a transaction pair successfully."""
        local_tx = {"id": "123", "amount": 100.0, "note": "local note"}
        remote_tx = {"id": "123", "amount": 100.0, "note": "remote note"}

        result = self.synchronizer._sync_transaction_pair(
            local_tx, remote_tx, dry_run=False
        )

        assert result.transaction_id == "123"
        assert result.status == SyncStatus.SUCCESS

    def test_sync_transaction_pair_with_error(self):
        """Test syncing a transaction pair with error."""
        # Create invalid transaction data that will cause resolution to fail
        local_tx = {"id": "123"}
        remote_tx = {"id": "123"}

        # Mock resolution engine to raise exception
        self.synchronizer.resolution_engine.resolve_transaction = Mock(
            side_effect=Exception("Resolution failed")
        )

        result = self.synchronizer._sync_transaction_pair(
            local_tx, remote_tx, dry_run=False
        )

        assert result.transaction_id == "123"
        assert result.status == SyncStatus.ERROR
        assert result.has_errors

    def test_handle_local_only_transaction(self):
        """Test handling local-only transaction."""
        local_tx = {"id": "123", "amount": 100.0, "note": "local only"}

        result = self.synchronizer._handle_local_only_transaction(
            local_tx, dry_run=False
        )

        assert result.transaction_id == "123"
        assert result.status == SyncStatus.SKIPPED
        assert result.has_warnings

    def test_handle_remote_only_transaction(self):
        """Test handling remote-only transaction."""
        remote_tx = {"id": "123", "amount": 100.0, "note": "remote only"}

        result = self.synchronizer._handle_remote_only_transaction(
            remote_tx, dry_run=False
        )

        assert result.transaction_id == "123"
        assert result.status == SyncStatus.SKIPPED
        assert result.has_warnings

    def test_synchronize_preparation_failure(self):
        """Test synchronization when preparation fails."""
        # Create invalid data that will fail preparation
        local_txs = ["invalid"]
        remote_txs = [{"id": "123", "amount": 100.0}]

        with pytest.raises(
            SynchronizationError, match="Synchronization preparation failed"
        ):
            self.synchronizer.synchronize(local_txs, remote_txs)


class TestConsoleSyncLogger:
    """Test ConsoleSyncLogger."""

    def setup_method(self):
        """Set up test fixtures."""
        self.logger = ConsoleSyncLogger()

    def test_log_sync_start(self, caplog):
        """Test logging sync start."""
        import logging

        caplog.set_level(logging.INFO)

        self.logger.log_sync_start(10, dry_run=False)
        assert "Starting synchronization (LIVE) for 10 transactions" in caplog.text

        caplog.clear()
        self.logger.log_sync_start(5, dry_run=True)
        assert "Starting synchronization (DRY RUN) for 5 transactions" in caplog.text

    def test_log_sync_complete(self, caplog):
        """Test logging sync completion."""
        import logging

        caplog.set_level(logging.INFO)

        summary = {
            "successful_syncs": 8,
            "total_transactions": 10,
            "success_rate": 80.0,
            "changes_made": 5,
            "duration": 2.5,
            "dry_run": False,
            "conflicts_detected": 1,
            "errors_encountered": 1,
        }

        self.logger.log_sync_complete(summary)

        assert "Synchronization complete (LIVE)" in caplog.text
        assert "8/10 successful (80.0%)" in caplog.text
        assert "5 changes made" in caplog.text
        assert "duration: 2.50s" in caplog.text
        assert "Detected 1 conflicts" in caplog.text
        assert "Encountered 1 errors" in caplog.text

    def test_log_transaction_sync_success_with_changes(self, caplog):
        """Test logging successful transaction sync with changes."""
        import logging

        caplog.set_level(logging.INFO)

        from src.pocketsmith_beancount.sync_enums import ChangeType, ResolutionStrategy

        result = SyncResult(transaction_id="123", status=SyncStatus.SUCCESS)
        result.add_change(
            "note",
            "old note",
            "new note",
            ChangeType.LOCAL_ONLY,
            ResolutionStrategy.LOCAL_CHANGES_ONLY,
        )

        self.logger.log_transaction_sync(result)

        assert "Synced transaction 123" in caplog.text
        assert "note: old note -> new note" in caplog.text

    def test_log_transaction_sync_error(self, caplog):
        """Test logging transaction sync error."""
        result = SyncResult(transaction_id="123", status=SyncStatus.ERROR)
        result.add_error("Test error message")

        self.logger.log_transaction_sync(result)

        assert "Failed to sync transaction 123" in caplog.text
        assert "Test error message" in caplog.text

    def test_log_transaction_sync_skipped(self, caplog):
        """Test logging skipped transaction sync."""
        import logging

        caplog.set_level(logging.DEBUG)

        result = SyncResult(transaction_id="123", status=SyncStatus.SKIPPED)
        result.add_warning("Test warning message")

        self.logger.log_transaction_sync(result)

        assert "Skipped transaction 123" in caplog.text
        assert "Test warning message" in caplog.text

    def test_log_conflict(self, caplog):
        """Test logging sync conflict."""
        import logging

        caplog.set_level(logging.WARNING)

        from src.pocketsmith_beancount.sync_models import SyncConflict
        from src.pocketsmith_beancount.sync_enums import ResolutionStrategy

        conflict = SyncConflict(
            transaction_id="123",
            field_name="note",
            local_value="local note",
            remote_value="remote note",
            local_timestamp=None,
            remote_timestamp=None,
            strategy=ResolutionStrategy.LOCAL_CHANGES_ONLY,
        )

        self.logger.log_conflict(conflict)

        assert "CONFLICT in transaction 123" in caplog.text
        assert "field 'note'" in caplog.text
        assert "local='local note' vs remote='remote note'" in caplog.text
        assert "strategy: LOCAL_CHANGES_ONLY" in caplog.text

    def test_log_error_with_transaction_id(self, caplog):
        """Test logging error with transaction ID."""
        self.logger.log_error("Test error", transaction_id="123")
        assert "Transaction 123: Test error" in caplog.text

    def test_log_error_without_transaction_id(self, caplog):
        """Test logging error without transaction ID."""
        self.logger.log_error("Test error")
        assert "Test error" in caplog.text
        assert "Transaction" not in caplog.text

    def test_log_warning_with_transaction_id(self, caplog):
        """Test logging warning with transaction ID."""
        self.logger.log_warning("Test warning", transaction_id="123")
        assert "Transaction 123: Test warning" in caplog.text

    def test_log_warning_without_transaction_id(self, caplog):
        """Test logging warning without transaction ID."""
        self.logger.log_warning("Test warning")
        assert "Test warning" in caplog.text
        assert "Transaction" not in caplog.text
