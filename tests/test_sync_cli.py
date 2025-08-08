"""Tests for sync CLI handler."""

from unittest.mock import patch

from src.pocketsmith_beancount.sync_cli import SyncCLIHandler
from src.pocketsmith_beancount.sync_models import SyncResult, FieldChange
from src.pocketsmith_beancount.sync_enums import (
    SyncStatus,
    ChangeType,
    ResolutionStrategy,
)


class TestSyncCLIHandler:
    """Test SyncCLIHandler."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cli_handler = SyncCLIHandler(verbose=False)
        self.verbose_cli_handler = SyncCLIHandler(verbose=True)

    @patch("builtins.input", return_value="y")
    def test_confirm_sync_operation_yes(self, mock_input, capsys):
        """Test confirming sync operation with yes."""
        result = self.cli_handler.confirm_sync_operation(10, 20, dry_run=False)

        assert result is True
        captured = capsys.readouterr()
        assert "LIVE Synchronization Summary" in captured.out
        assert "Local transactions: 10" in captured.out
        assert "Remote transactions: 20" in captured.out
        assert "Total to process: 30" in captured.out
        assert "WARNING: This will make actual changes" in captured.out

    @patch("builtins.input", return_value="n")
    def test_confirm_sync_operation_no(self, mock_input, capsys):
        """Test confirming sync operation with no."""
        result = self.cli_handler.confirm_sync_operation(5, 10, dry_run=True)

        assert result is False
        captured = capsys.readouterr()
        assert "DRY RUN Synchronization Summary" in captured.out
        assert "This is a dry run - no actual changes will be made" in captured.out

    @patch("builtins.input", side_effect=["invalid", "y"])
    def test_confirm_sync_operation_invalid_then_yes(self, mock_input, capsys):
        """Test confirming sync operation with invalid input then yes."""
        result = self.cli_handler.confirm_sync_operation(1, 1)

        assert result is True
        captured = capsys.readouterr()
        assert "Please enter 'y' or 'n'" in captured.out

    def test_display_sync_progress_verbose(self, capsys):
        """Test displaying sync progress in verbose mode."""
        self.verbose_cli_handler.display_sync_progress(5, 10, "123")

        captured = capsys.readouterr()
        assert "[5/10] (50.0%) Processing transaction 123" in captured.out

    def test_display_sync_progress_non_verbose(self, capsys):
        """Test displaying sync progress in non-verbose mode."""
        self.cli_handler.display_sync_progress(5, 10, "123")

        captured = capsys.readouterr()
        assert captured.out == ""  # Should not display anything in non-verbose mode

    def test_display_sync_results_empty(self, capsys):
        """Test displaying results with no transactions."""
        self.cli_handler.display_sync_results([])

        captured = capsys.readouterr()
        assert "No transactions were processed" in captured.out

    def test_display_sync_results_successful(self, capsys):
        """Test displaying successful sync results."""
        results = [
            SyncResult(transaction_id="123", status=SyncStatus.SUCCESS),
            SyncResult(transaction_id="456", status=SyncStatus.SUCCESS),
        ]

        # Add some changes
        results[0].add_change(
            "note",
            "old",
            "new",
            ChangeType.LOCAL_ONLY,
            ResolutionStrategy.LOCAL_CHANGES_ONLY,
        )

        self.cli_handler.display_sync_results(results, dry_run=False)

        captured = capsys.readouterr()
        assert "LIVE Synchronization Results" in captured.out
        assert "Total transactions processed: 2" in captured.out
        assert "Successful: 2" in captured.out
        assert "Changes made: 1" in captured.out
        assert "Success rate: 100.0%" in captured.out
        assert "✅ Synchronization completed. 1 changes were made" in captured.out

    def test_display_sync_results_with_errors(self, capsys):
        """Test displaying sync results with errors."""
        results = [
            SyncResult(transaction_id="123", status=SyncStatus.ERROR),
            SyncResult(transaction_id="456", status=SyncStatus.SUCCESS),
        ]

        results[0].add_error("Test error message")

        self.cli_handler.display_sync_results(results)

        captured = capsys.readouterr()
        assert "Errors: 1" in captured.out
        assert "Transaction 123:" in captured.out
        assert "Test error message" in captured.out
        assert "⚠️  1 transactions had errors" in captured.out

    def test_display_sync_results_with_conflicts(self, capsys):
        """Test displaying sync results with conflicts."""
        results = [SyncResult(transaction_id="123", status=SyncStatus.SUCCESS)]

        results[0].add_conflict(
            "note", "local note", "remote note", ResolutionStrategy.LOCAL_CHANGES_ONLY
        )

        self.cli_handler.display_sync_results(results)

        captured = capsys.readouterr()
        assert "Conflicts detected: 1" in captured.out
        assert "Transaction 123:" in captured.out
        assert "local='local note' vs remote='remote note'" in captured.out
        assert "⚠️  1 conflicts were detected" in captured.out

    def test_display_sync_results_dry_run_with_changes(self, capsys):
        """Test displaying dry run results with changes."""
        results = [SyncResult(transaction_id="123", status=SyncStatus.SUCCESS)]
        results[0].add_change(
            "note",
            "old",
            "new",
            ChangeType.LOCAL_ONLY,
            ResolutionStrategy.LOCAL_CHANGES_ONLY,
        )

        self.cli_handler.display_sync_results(results, dry_run=True)

        captured = capsys.readouterr()
        assert "DRY RUN Synchronization Results" in captured.out
        assert "✅ Dry run completed. 1 changes would be made" in captured.out

    def test_display_sync_results_no_changes(self, capsys):
        """Test displaying results with no changes."""
        results = [SyncResult(transaction_id="123", status=SyncStatus.SUCCESS)]

        self.cli_handler.display_sync_results(results)

        captured = capsys.readouterr()
        assert "Changes made: 0" in captured.out
        assert "✅ All transactions are already in sync" in captured.out

    def test_display_sync_results_verbose(self, capsys):
        """Test displaying results in verbose mode."""
        results = [SyncResult(transaction_id="123", status=SyncStatus.SUCCESS)]
        results[0].add_change(
            "note",
            "old",
            "new",
            ChangeType.LOCAL_ONLY,
            ResolutionStrategy.LOCAL_CHANGES_ONLY,
        )

        self.verbose_cli_handler.display_sync_results(results)

        captured = capsys.readouterr()
        assert "Detailed Results:" in captured.out
        assert "Transaction 123:" in captured.out
        assert "note: 'old' -> 'new'" in captured.out

    def test_display_error(self, capsys):
        """Test displaying error message."""
        self.cli_handler.display_error("Test error message")

        captured = capsys.readouterr()
        assert "❌ Error: Test error message" in captured.err

    @patch("traceback.print_exc")
    def test_display_error_with_traceback(self, mock_traceback, capsys):
        """Test displaying error with traceback."""
        self.cli_handler.display_error("Test error", show_traceback=True)

        captured = capsys.readouterr()
        assert "❌ Error: Test error" in captured.err
        mock_traceback.assert_called_once()

    def test_display_warning(self, capsys):
        """Test displaying warning message."""
        self.cli_handler.display_warning("Test warning")

        captured = capsys.readouterr()
        assert "⚠️  Warning: Test warning" in captured.out

    def test_display_info(self, capsys):
        """Test displaying info message."""
        self.cli_handler.display_info("Test info")

        captured = capsys.readouterr()
        assert "ℹ️  Test info" in captured.out

    def test_format_field_changes_empty(self):
        """Test formatting empty field changes."""
        result = self.cli_handler.format_field_changes([])
        assert result == "No changes"

    def test_format_field_changes_few(self):
        """Test formatting few field changes."""
        changes = [
            FieldChange(
                "note",
                "old1",
                "new1",
                ChangeType.LOCAL_ONLY,
                ResolutionStrategy.LOCAL_CHANGES_ONLY,
            ),
            FieldChange(
                "labels",
                [],
                ["tag1"],
                ChangeType.LOCAL_ONLY,
                ResolutionStrategy.MERGE_LISTS,
            ),
        ]

        result = self.cli_handler.format_field_changes(changes)
        assert "note: old1 -> new1" in result
        assert "labels: [] -> ['tag1']" in result

    def test_format_field_changes_many(self):
        """Test formatting many field changes."""
        changes = [
            FieldChange(
                "note",
                "old1",
                "new1",
                ChangeType.LOCAL_ONLY,
                ResolutionStrategy.LOCAL_CHANGES_ONLY,
            ),
            FieldChange(
                "labels",
                [],
                ["tag1"],
                ChangeType.LOCAL_ONLY,
                ResolutionStrategy.MERGE_LISTS,
            ),
            FieldChange(
                "category",
                "cat1",
                "cat2",
                ChangeType.REMOTE_ONLY,
                ResolutionStrategy.REMOTE_WINS,
            ),
            FieldChange(
                "amount",
                100,
                200,
                ChangeType.REMOTE_ONLY,
                ResolutionStrategy.NEVER_CHANGE,
            ),
        ]

        result = self.cli_handler.format_field_changes(changes)
        assert "... and 1 more" in result

    @patch("builtins.input", return_value="yes")
    def test_get_user_choice_valid(self, mock_input):
        """Test getting valid user choice."""
        result = self.cli_handler.get_user_choice("Choose", ["yes", "no"], default="no")
        assert result == "yes"

    @patch("builtins.input", return_value="")
    def test_get_user_choice_default(self, mock_input):
        """Test getting default user choice."""
        result = self.cli_handler.get_user_choice("Choose", ["yes", "no"], default="no")
        assert result == "no"

    @patch("builtins.input", side_effect=["invalid", "yes"])
    def test_get_user_choice_invalid_then_valid(self, mock_input, capsys):
        """Test getting user choice with invalid input then valid."""
        result = self.cli_handler.get_user_choice("Choose", ["yes", "no"])

        assert result == "yes"
        captured = capsys.readouterr()
        assert "Please enter one of: yes, no" in captured.out

    def test_display_sync_configuration(self, capsys):
        """Test displaying sync configuration."""
        config = {"dry_run": True, "batch_size": 100, "verbose": False}

        self.cli_handler.display_sync_configuration(config)

        captured = capsys.readouterr()
        assert "Synchronization Configuration:" in captured.out
        assert "dry_run: True" in captured.out
        assert "batch_size: 100" in captured.out
        assert "verbose: False" in captured.out
