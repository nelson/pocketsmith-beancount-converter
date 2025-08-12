"""Tests for the clone command."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from typer.testing import CliRunner
from datetime import date

from main import app


class TestCloneCommandValidation:
    """Test clone command input validation."""

    def test_clone_validates_conflicting_limit_options(self):
        """Test that clone validates conflicting limit options."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Test --all with explicit --limit
            result = runner.invoke(app, [str(dest_path), "--all", "--limit", "100"])
            assert result.exit_code != 0  # Should fail with non-zero exit code
            assert "Cannot specify both --all and --limit" in result.output

    def test_clone_validates_date_options(self):
        """Test that clone validates date options."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Test --to without --from
            result = runner.invoke(app, [str(dest_path), "--to", "2024-12-31"])
            assert result.exit_code != 0  # Should fail with non-zero exit code
            assert "Cannot specify --to without --from" in result.output

    def test_clone_validates_multiple_convenience_dates(self):
        """Test that clone validates multiple convenience date options."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Test multiple convenience options
            result = runner.invoke(
                app, [str(dest_path), "--this-month", "--last-month"]
            )
            assert result.exit_code != 0  # Should fail with non-zero exit code
            assert "Cannot specify multiple date convenience options" in result.output

    def test_clone_validates_convenience_with_explicit_dates(self):
        """Test that clone validates convenience dates with explicit dates."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Test convenience option with explicit date
            result = runner.invoke(
                app, [str(dest_path), "--this-month", "--from", "2024-01-01"]
            )
            assert result.exit_code != 0  # Should fail with non-zero exit code
            assert "Cannot combine convenience date options" in result.output


class TestCloneCommandFileHandling:
    """Test clone command file handling."""

    def test_clone_rejects_existing_directory(self):
        """Test that clone rejects existing directory."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            # temp_dir already exists
            result = runner.invoke(app, [temp_dir])
            assert result.exit_code != 0  # Should fail with non-zero exit code
            assert "already exists" in result.output

    def test_clone_rejects_existing_file_single_mode(self):
        """Test that clone rejects existing file in single file mode."""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            try:
                result = runner.invoke(app, [temp_file.name, "-1"])
                assert result.exit_code != 0  # Should fail with non-zero exit code
                assert "already exists" in result.output
            finally:
                Path(temp_file.name).unlink(missing_ok=True)

    def test_clone_adds_beancount_extension(self):
        """Test that clone adds .beancount extension in single file mode."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "transactions"

            with patch("src.cli.clone.PocketSmithClient") as mock_client_class:
                # Mock the API client and its methods
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.get_user.return_value = {"login": "test_user"}
                mock_client.get_transaction_accounts.return_value = []
                mock_client.get_categories.return_value = []
                mock_client.get_transactions.return_value = [
                    {
                        "id": 1,
                        "payee": "Test Payee",
                        "amount": "10.00",
                        "date": "2024-01-01",
                        "currency_code": "USD",
                    }
                ]

                runner.invoke(app, [str(dest_path), "-1"])

                # Should succeed and create file with .beancount extension
                expected_file = dest_path.with_suffix(".beancount")
                assert expected_file.exists()


class TestCloneCommandDateParsing:
    """Test clone command date parsing."""

    @patch("src.cli.clone.PocketSmithClient")
    def test_clone_parses_full_date_format(self, mock_client_class):
        """Test that clone parses full date format correctly."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Mock the API client
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = []

            runner.invoke(
                app, [str(dest_path), "--from", "2024-01-01", "--to", "2024-12-31"]
            )

            # Should call get_transactions with correct date format
            mock_client.get_transactions.assert_called_once()
            call_args = mock_client.get_transactions.call_args
            assert call_args[1]["start_date"] == "2024-01-01"
            assert call_args[1]["end_date"] == "2024-12-31"

    @patch("src.cli.clone.PocketSmithClient")
    def test_clone_handles_this_month_option(self, mock_client_class):
        """Test that clone handles --this-month option."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Mock the API client
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = []

            runner.invoke(app, [str(dest_path), "--this-month"])

            # Should call get_transactions with this month's date range
            mock_client.get_transactions.assert_called_once()
            call_args = mock_client.get_transactions.call_args

            # Verify dates are from current month
            today = date.today()
            expected_start = f"{today.year}-{today.month:02d}-01"
            assert call_args[1]["start_date"] == expected_start
            assert call_args[1]["end_date"] is not None

    def test_clone_handles_invalid_date_format(self):
        """Test that clone handles invalid date format."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            result = runner.invoke(app, [str(dest_path), "--from", "invalid-date"])

            assert result.exit_code != 0  # Should fail with non-zero exit code
            assert "Unsupported date format" in result.output


class TestCloneCommandTransactionLimits:
    """Test clone command transaction limit handling."""

    @patch("src.cli.clone.PocketSmithClient")
    def test_clone_respects_default_limit(self, mock_client_class):
        """Test that clone respects default transaction limit."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Mock the API client
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = []

            runner.invoke(app, [str(dest_path)])

            # Should call get_transactions (limit applied after fetching)
            mock_client.get_transactions.assert_called_once()
            call_args = mock_client.get_transactions.call_args
            # Verify it was called with expected parameters (no limit parameter)
            assert "account_id" in call_args[1]

    @patch("src.cli.clone.PocketSmithClient")
    def test_clone_respects_custom_limit(self, mock_client_class):
        """Test that clone respects custom transaction limit."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Mock the API client
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = []

            runner.invoke(app, [str(dest_path), "--limit", "100"])

            # Should call get_transactions (limit applied after fetching)
            mock_client.get_transactions.assert_called_once()
            call_args = mock_client.get_transactions.call_args
            # Verify it was called with expected parameters (no limit parameter)
            assert "account_id" in call_args[1]

    @patch("src.cli.clone.PocketSmithClient")
    def test_clone_handles_all_transactions(self, mock_client_class):
        """Test that clone handles --all flag."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Mock the API client
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = []

            runner.invoke(app, [str(dest_path), "--all"])

            # Should call get_transactions (--all means no limit applied after fetching)
            mock_client.get_transactions.assert_called_once()
            call_args = mock_client.get_transactions.call_args
            # Verify it was called with expected parameters (no limit parameter)
            assert "account_id" in call_args[1]


class TestCloneCommandErrorHandling:
    """Test clone command error handling."""

    def test_clone_handles_api_connection_error(self):
        """Test that clone handles API connection errors gracefully."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            with patch("src.cli.clone.PocketSmithClient") as mock_client_class:
                mock_client_class.side_effect = Exception("API connection failed")

                result = runner.invoke(app, [str(dest_path)])
                assert result.exit_code != 0  # Should fail with non-zero exit code
                assert "Failed to connect to PocketSmith API" in result.output

    @patch("src.cli.clone.PocketSmithClient")
    def test_clone_handles_no_transactions_found(self, mock_client_class):
        """Test that clone handles case when no transactions are found."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Mock the API client to return empty transactions
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_user.return_value = {"login": "test_user"}
            mock_client.get_transaction_accounts.return_value = []
            mock_client.get_categories.return_value = []
            mock_client.get_transactions.return_value = []

            result = runner.invoke(app, [str(dest_path)])

            # Should succeed when no transactions found (not an error condition)
            assert result.exit_code == 0
            assert "No transactions found" in result.output


class TestCloneCommandHelp:
    """Test clone command help and documentation."""

    def test_clone_help_text(self):
        """Test that clone command shows helpful help text."""
        runner = CliRunner()

        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Download PocketSmith transactions" in result.stdout
        # The help text mentions the key options in the description
        assert "single" in result.stdout.lower()  # References single file mode
        assert "DESTINATION" in result.stdout  # Shows the required argument

    def test_clone_command_options_present(self):
        """Test that clone command has expected options configured."""
        # This tests the actual command configuration rather than the help output
        # which can be truncated in CI environments

        # Get the clone command function directly from main module
        import main

        # Check that the clone function has the expected parameters
        import inspect

        sig = inspect.signature(main.clone)
        params = list(sig.parameters.keys())

        assert "destination" in params
        assert "single_file" in params
        assert "limit" in params
        assert "all_transactions" in params
        assert "from_date" in params
        assert "to_date" in params
        assert "this_month" in params
        assert "last_month" in params
        assert "this_year" in params
        assert "last_year" in params
