"""Tests for the pull command."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from typer.testing import CliRunner

from main import app


class TestPullCommandValidation:
    """Test pull command input validation."""

    def test_pull_validates_date_options(self):
        """Test that pull validates date options."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"
            dest_path.mkdir()

            # Create changelog to make it look like a valid destination
            changelog_path = dest_path / "main.log"
            changelog_path.write_text(
                "[2024-01-01 10:00:00] CLONE 2024-01-01 2024-01-31\n"
            )

            # Test --to without --from
            result = runner.invoke(app, ["pull", str(dest_path), "--to", "2024-12-31"])
            assert result.exit_code != 0
            assert "Cannot specify --to without --from" in result.output

    def test_pull_validates_multiple_convenience_dates(self):
        """Test that pull validates multiple convenience date options."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"
            dest_path.mkdir()

            # Create changelog
            changelog_path = dest_path / "main.log"
            changelog_path.write_text(
                "[2024-01-01 10:00:00] CLONE 2024-01-01 2024-01-31\n"
            )

            # Test multiple convenience options
            result = runner.invoke(
                app, ["pull", str(dest_path), "--this-month", "--last-month"]
            )
            assert result.exit_code != 0
            assert "Cannot specify multiple date convenience options" in result.output

    def test_pull_rejects_nonexistent_destination(self):
        """Test that pull rejects non-existent destination."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "nonexistent"

            result = runner.invoke(app, ["pull", str(dest_path)])
            assert result.exit_code != 0
            assert "does not exist" in result.output

    def test_pull_rejects_destination_without_changelog(self):
        """Test that pull rejects destination without changelog."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"
            dest_path.mkdir()
            # No changelog file created

            result = runner.invoke(app, ["pull", str(dest_path)])
            assert result.exit_code != 0
            assert "No previous clone or pull found" in result.output


class TestPullCommandSingleFileMode:
    """Test pull command with single file mode."""

    @patch("src.cli.pull.PocketSmithClient")
    def test_pull_single_file_mode(self, mock_client_class):
        """Test pull command with single file destination."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "transactions.beancount"
            changelog_path = Path(temp_dir) / "transactions.log"

            # Create destination file and changelog
            dest_path.write_text("existing beancount content")
            changelog_path.write_text(
                "[2024-01-01 10:00:00] CLONE 2024-01-01 2024-01-31\n"
            )

            # Mock the API client
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = [
                {
                    "id": 2,
                    "payee": "New Transaction",
                    "amount": "20.00",
                    "date": "2024-01-15",
                    "currency_code": "USD",
                }
            ]

            result = runner.invoke(app, ["pull", str(dest_path)])

            assert result.exit_code == 0
            assert "Ledger" in result.output and "updated" in result.output
            assert "Changelog" in result.output and "updated" in result.output

            # Check that updated_since was used
            mock_client.get_transactions.assert_called()
            call_args = mock_client.get_transactions.call_args
            assert "updated_since" in call_args[1]


class TestPullCommandHierarchicalMode:
    """Test pull command with hierarchical mode."""

    @patch("src.cli.pull.PocketSmithClient")
    def test_pull_hierarchical_mode(self, mock_client_class):
        """Test pull command with hierarchical destination."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"
            dest_path.mkdir()

            # Create main beancount file and changelog
            main_file = dest_path / "main.beancount"
            main_file.write_text("existing beancount content")
            changelog_path = dest_path / "main.log"
            changelog_path.write_text(
                "[2024-01-01 10:00:00] CLONE 2024-01-01 2024-01-31\n"
            )

            # Mock the API client
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = []

            result = runner.invoke(app, ["pull", str(dest_path)])

            assert result.exit_code == 0
            assert "Ledger" in result.output and "updated" in result.output


class TestPullCommandDryRun:
    """Test pull command dry-run mode."""

    @patch("src.cli.pull.PocketSmithClient")
    def test_pull_dry_run_mode(self, mock_client_class):
        """Test that dry-run mode doesn't modify files."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "transactions.beancount"
            changelog_path = Path(temp_dir) / "transactions.log"

            # Create destination file and changelog
            original_content = "original content"
            dest_path.write_text(original_content)
            original_changelog = "[2024-01-01 10:00:00] CLONE 2024-01-01 2024-01-31\n"
            changelog_path.write_text(original_changelog)

            # Mock the API client
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = [
                {
                    "id": 2,
                    "payee": "New Transaction",
                    "amount": "20.00",
                    "date": "2024-01-15",
                    "currency_code": "USD",
                }
            ]

            result = runner.invoke(app, ["pull", str(dest_path), "--dry-run"])

            assert result.exit_code == 0
            assert "not updated (due to --dry-run)" in result.output

            # Files should not be modified
            assert dest_path.read_text() == original_content
            assert changelog_path.read_text() == original_changelog


class TestPullCommandQuietMode:
    """Test pull command quiet mode."""

    @patch("src.cli.pull.PocketSmithClient")
    def test_pull_quiet_suppresses_output(self, mock_client_class):
        """Test that --quiet suppresses informational output."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "transactions.beancount"
            changelog_path = Path(temp_dir) / "transactions.log"

            # Create destination file and changelog
            dest_path.write_text("existing content")
            changelog_path.write_text(
                "[2024-01-01 10:00:00] CLONE 2024-01-01 2024-01-31\n"
            )

            # Mock the API client
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = []

            result = runner.invoke(app, ["pull", str(dest_path), "--quiet"])

            assert result.exit_code == 0
            # Should not contain informational messages
            assert "Connecting to PocketSmith API" not in result.output
            assert "Fetching transactions" not in result.output
            # Should not contain summary
            assert "Ledger" not in result.output or "updated" not in result.output


class TestPullCommandDateHandling:
    """Test pull command date handling."""

    @patch("src.cli.pull.PocketSmithClient")
    def test_pull_uses_last_sync_dates(self, mock_client_class):
        """Test that pull uses dates from last sync when no new dates provided."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "transactions.beancount"
            changelog_path = Path(temp_dir) / "transactions.log"

            # Create destination file and changelog
            dest_path.write_text("existing content")
            changelog_path.write_text(
                "[2024-01-01 10:00:00] CLONE 2024-01-01 2024-01-31\n"
            )

            # Mock the API client
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = []

            result = runner.invoke(app, ["pull", str(dest_path)])

            assert result.exit_code == 0

            # Should call get_transactions with original date range and updated_since
            mock_client.get_transactions.assert_called_once()
            call_args = mock_client.get_transactions.call_args
            assert call_args[1]["start_date"] == "2024-01-01"
            assert call_args[1]["end_date"] == "2024-01-31"
            assert "updated_since" in call_args[1]

    @patch("src.cli.pull.PocketSmithClient")
    def test_pull_uses_new_date_range(self, mock_client_class):
        """Test that pull uses new date range when provided."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "transactions.beancount"
            changelog_path = Path(temp_dir) / "transactions.log"

            # Create destination file and changelog
            dest_path.write_text("existing content")
            changelog_path.write_text(
                "[2024-01-01 10:00:00] CLONE 2024-01-01 2024-01-31\n"
            )

            # Mock the API client
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = []

            result = runner.invoke(
                app,
                ["pull", str(dest_path), "--from", "2024-02-01", "--to", "2024-02-29"],
            )

            assert result.exit_code == 0

            # Should call get_transactions with new date range and no updated_since
            mock_client.get_transactions.assert_called_once()
            call_args = mock_client.get_transactions.call_args
            assert call_args[1]["start_date"] == "2024-02-01"
            assert call_args[1]["end_date"] == "2024-02-29"
            assert "updated_since" not in call_args[1]


class TestPullCommandChangelogEntries:
    """Test pull command changelog entries."""

    @patch("src.cli.pull.PocketSmithClient")
    def test_pull_writes_pull_entry(self, mock_client_class):
        """Test that pull writes PULL entry to changelog."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "transactions.beancount"
            changelog_path = Path(temp_dir) / "transactions.log"

            # Create destination file and changelog
            dest_path.write_text("existing content")
            original_changelog = "[2024-01-01 10:00:00] CLONE 2024-01-01 2024-01-31\n"
            changelog_path.write_text(original_changelog)

            # Mock the API client
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = []

            result = runner.invoke(app, ["pull", str(dest_path)])

            assert result.exit_code == 0

            # Check changelog was updated
            changelog_content = changelog_path.read_text()
            lines = changelog_content.strip().split("\n")
            assert len(lines) == 2  # Original + new PULL entry
            assert "CLONE" in lines[0]
            assert "PULL" in lines[1]


class TestPullCommandHelp:
    """Test pull command help and documentation."""

    def test_pull_help_text(self):
        """Test that pull command shows helpful help text."""
        runner = CliRunner()

        result = runner.invoke(app, ["pull", "--help"])

        assert result.exit_code == 0
        assert "Update local Beancount ledger" in result.stdout
        assert "updated_since" in result.stdout
        assert "LEDGER" in result.stdout

    def test_pull_command_options_present(self):
        """Test that pull command has expected options configured."""
        # Get the pull command function directly from main module
        import main
        import inspect

        sig = inspect.signature(main.pull)
        params = list(sig.parameters.keys())

        assert "ledger" in params
        assert "dry_run" in params
        assert "quiet" in params
        assert "from_date" in params
        assert "to_date" in params
        assert "this_month" in params
        assert "last_month" in params
        assert "this_year" in params
        assert "last_year" in params


class TestPullCommandTransactionComparison:
    """Test pull command transaction comparison logic."""

    @patch("src.cli.pull.read_existing_transactions")
    @patch("src.cli.pull.PocketSmithClient")
    def test_pull_detects_new_transactions(self, mock_client_class, mock_read_existing):
        """Test that pull correctly detects new transactions."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "transactions.beancount"
            changelog_path = Path(temp_dir) / "transactions.log"

            # Create destination file and changelog
            dest_path.write_text("existing content")
            changelog_path.write_text(
                "[2024-01-01 10:00:00] CLONE 2024-01-01 2024-01-31\n"
            )

            # Mock existing transactions (empty)
            mock_read_existing.return_value = {}

            # Mock the API client with new transaction
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = [
                {
                    "id": 2,
                    "payee": "New Transaction",
                    "amount": "20.00",
                    "date": "2024-01-15",
                    "currency_code": "USD",
                }
            ]

            result = runner.invoke(app, ["pull", str(dest_path)])

            assert result.exit_code == 0
            assert "1 new transactions were added" in result.output

    @patch("src.cli.pull.read_existing_transactions")
    @patch("src.cli.pull.PocketSmithClient")
    def test_pull_detects_updated_transactions(
        self, mock_client_class, mock_read_existing
    ):
        """Test that pull correctly detects updated transactions."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "transactions.beancount"
            changelog_path = Path(temp_dir) / "transactions.log"

            # Create destination file and changelog
            dest_path.write_text("existing content")
            changelog_path.write_text(
                "[2024-01-01 10:00:00] CLONE 2024-01-01 2024-01-31\n"
            )

            # Mock existing transactions
            mock_read_existing.return_value = {
                "1": {
                    "id": 1,
                    "payee": "Original Payee",
                    "amount": "10.00",
                    "note": "Original note",
                }
            }

            # Mock the API client with updated transaction
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = [
                {
                    "id": 1,
                    "payee": "Updated Payee",  # Changed
                    "amount": "10.00",
                    "note": "Original note",
                    "date": "2024-01-15",
                    "currency_code": "USD",
                }
            ]

            result = runner.invoke(app, ["pull", str(dest_path)])

            assert result.exit_code == 0
            # Should detect the update
            assert "1 receiving updates" in result.output

            # Check changelog contains UPDATE entry (not OVERWRITE)
            changelog_content = changelog_path.read_text()
            assert "UPDATE" in changelog_content

    @patch("src.cli.pull.read_existing_transactions")
    @patch("src.cli.pull.PocketSmithClient")
    def test_pull_verbose_mode_shows_updates(
        self, mock_client_class, mock_read_existing
    ):
        """Test that verbose mode shows UPDATE entries."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "transactions.beancount"
            changelog_path = Path(temp_dir) / "transactions.log"

            # Create destination file and changelog
            dest_path.write_text("existing content")
            changelog_path.write_text(
                "[2024-01-01 10:00:00] CLONE 2024-01-01 2024-01-31\n"
            )

            # Mock existing transactions
            mock_read_existing.return_value = {
                "1": {
                    "id": 1,
                    "payee": "Original Payee",
                    "amount": "10.00",
                    "category_id": 1,
                }
            }

            # Mock the API client with updated transaction
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = [
                {
                    "id": 1,
                    "payee": "Updated Payee",  # Changed
                    "amount": "10.00",
                    "category_id": 2,  # Also changed
                    "date": "2024-01-15",
                    "currency_code": "USD",
                }
            ]

            result = runner.invoke(app, ["pull", str(dest_path), "--verbose"])

            assert result.exit_code == 0
            # Should show UPDATE entries in output
            assert "UPDATE 1 payee Original Payee → Updated Payee" in result.output
            assert "UPDATE 1 category 1 → 2" in result.output

    @patch("src.cli.pull.read_existing_transactions")
    @patch("src.cli.pull.PocketSmithClient")
    def test_pull_dry_run_verbose_shows_preview(
        self, mock_client_class, mock_read_existing
    ):
        """Test that dry-run with verbose shows what would be updated."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "transactions.beancount"
            changelog_path = Path(temp_dir) / "transactions.log"

            # Create destination file and changelog
            original_content = "original content"
            dest_path.write_text(original_content)
            original_changelog = "[2024-01-01 10:00:00] CLONE 2024-01-01 2024-01-31\n"
            changelog_path.write_text(original_changelog)

            # Mock existing transactions
            mock_read_existing.return_value = {
                "1": {
                    "id": 1,
                    "payee": "Original Payee",
                    "amount": "10.00",
                }
            }

            # Mock the API client with updated transaction
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = [
                {
                    "id": 1,
                    "payee": "Updated Payee",  # Changed
                    "amount": "10.00",
                    "date": "2024-01-15",
                    "currency_code": "USD",
                }
            ]

            result = runner.invoke(
                app, ["pull", str(dest_path), "--dry-run", "--verbose"]
            )

            assert result.exit_code == 0
            # Should show what would be updated
            assert "UPDATE 1 payee Original Payee → Updated Payee" in result.output
            assert "not updated (due to --dry-run)" in result.output

            # Files should not be modified
            assert dest_path.read_text() == original_content
            assert changelog_path.read_text() == original_changelog
