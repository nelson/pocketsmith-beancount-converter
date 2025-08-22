"""Tests for the clone command."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from typer.testing import CliRunner
from datetime import date

from main import app


def pocketsmith_patches():
    """Decorator to patch all PocketSmith functions for testing."""
    return [
        patch("src.cli.clone.get_user"),
        patch("src.cli.clone.get_transaction_accounts"),
        patch("src.cli.clone.get_categories"),
        patch("src.cli.clone.get_transactions"),
        patch("src.cli.clone.PocketSmithClient"),
    ]


def setup_mocks(
    mock_client_class,
    mock_get_transactions,
    mock_get_categories,
    mock_get_transaction_accounts,
    mock_get_user,
    transactions=None,
):
    """Setup common mock configuration."""
    if transactions is None:
        transactions = []

    mock_client = Mock()
    mock_client_class.return_value = mock_client
    mock_get_user.return_value = {"login": "test_user"}
    mock_get_transaction_accounts.return_value = []
    mock_get_categories.return_value = []
    mock_get_transactions.return_value = transactions

    return mock_client, mock_get_transactions


class TestCloneCommandValidation:
    """Test clone command input validation."""

    def test_clone_validates_date_options(self):
        """Test that clone validates date options."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Test --to without --from
            result = runner.invoke(app, ["clone", str(dest_path), "--to", "2024-12-31"])
            assert result.exit_code != 0
            assert "Cannot specify --to without --from" in result.output

    def test_clone_validates_multiple_convenience_dates(self):
        """Test that clone validates multiple convenience date options."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Test multiple convenience options
            result = runner.invoke(
                app, ["clone", str(dest_path), "--this-month", "--last-month"]
            )
            assert result.exit_code != 0
            assert "Cannot specify multiple date convenience options" in result.output

    def test_clone_validates_convenience_with_explicit_dates(self):
        """Test that clone validates convenience dates with explicit dates."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Test convenience option with explicit date
            result = runner.invoke(
                app, ["clone", str(dest_path), "--this-month", "--from", "2024-01-01"]
            )
            assert result.exit_code != 0
            assert "Cannot combine convenience date options" in result.output


class TestCloneCommandFileHandling:
    """Test clone command file handling."""

    def test_clone_rejects_existing_directory(self):
        """Test that clone rejects existing directory."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            # temp_dir already exists
            result = runner.invoke(app, ["clone", temp_dir])
            assert result.exit_code != 0
            assert "already exists" in result.output

    def test_clone_rejects_existing_file_single_mode(self):
        """Test that clone rejects existing file in single file mode."""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            try:
                result = runner.invoke(app, ["clone", temp_file.name, "-1"])
                assert result.exit_code != 0
                assert "already exists" in result.output
            finally:
                Path(temp_file.name).unlink(missing_ok=True)

    @patch("src.cli.clone.get_user")
    @patch("src.cli.clone.get_transaction_accounts")
    @patch("src.cli.clone.get_categories")
    @patch("src.cli.clone.get_transactions")
    @patch("src.cli.clone.PocketSmithClient")
    def test_clone_creates_changelog_single_file(
        self,
        mock_client_class,
        mock_get_transactions,
        mock_get_categories,
        mock_get_transaction_accounts,
        mock_get_user,
    ):
        """Test that clone creates changelog in single file mode."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "transactions.beancount"

            # Setup mocks
            mock_client, mock_get_transactions = setup_mocks(
                mock_client_class,
                mock_get_transactions,
                mock_get_categories,
                mock_get_transaction_accounts,
                mock_get_user,
                [
                    {
                        "id": 1,
                        "payee": "Test Payee",
                        "amount": "10.00",
                        "date": "2024-01-01",
                        "currency_code": "USD",
                    }
                ],
            )

            result = runner.invoke(app, ["clone", str(dest_path), "-1"])

            assert result.exit_code == 0
            assert dest_path.exists()

            # Check changelog was created
            changelog_path = dest_path.with_suffix(".log")
            assert changelog_path.exists()

            content = changelog_path.read_text()
            assert "CLONE" in content

    @patch("src.cli.clone.get_user")
    @patch("src.cli.clone.get_transaction_accounts")
    @patch("src.cli.clone.get_categories")
    @patch("src.cli.clone.get_transactions")
    @patch("src.cli.clone.PocketSmithClient")
    def test_clone_creates_changelog_hierarchical(
        self,
        mock_client_class,
        mock_get_transactions,
        mock_get_categories,
        mock_get_transaction_accounts,
        mock_get_user,
    ):
        """Test that clone creates changelog in hierarchical mode."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Setup mocks
            mock_client, mock_get_transactions = setup_mocks(
                mock_client_class,
                mock_get_transactions,
                mock_get_categories,
                mock_get_transaction_accounts,
                mock_get_user,
                [
                    {
                        "id": 1,
                        "payee": "Test Payee",
                        "amount": "10.00",
                        "date": "2024-01-01",
                        "currency_code": "USD",
                    }
                ],
            )

            result = runner.invoke(app, ["clone", str(dest_path)])

            assert result.exit_code == 0
            assert dest_path.exists()
            assert dest_path.is_dir()

            # Check changelog was created
            changelog_path = dest_path / "main.log"
            assert changelog_path.exists()

            content = changelog_path.read_text()
            assert "CLONE" in content


class TestCloneCommandDateParsing:
    """Test clone command date parsing."""

    @patch("src.cli.clone.get_user")
    @patch("src.cli.clone.get_transaction_accounts")
    @patch("src.cli.clone.get_categories")
    @patch("src.cli.clone.get_transactions")
    @patch("src.cli.clone.PocketSmithClient")
    def test_clone_parses_full_date_format(
        self,
        mock_client_class,
        mock_get_transactions,
        mock_get_categories,
        mock_get_transaction_accounts,
        mock_get_user,
    ):
        """Test that clone parses full date format correctly."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Setup mocks
            mock_client, mock_get_transactions = setup_mocks(
                mock_client_class,
                mock_get_transactions,
                mock_get_categories,
                mock_get_transaction_accounts,
                mock_get_user,
                [],
            )

            runner.invoke(
                app,
                ["clone", str(dest_path), "--from", "2024-01-01", "--to", "2024-12-31"],
            )

            # Should call get_transactions with correct date format
            mock_get_transactions.assert_called_once()
            call_args = mock_get_transactions.call_args
            # The function is called with client as first arg, then keyword args
            assert call_args[1]["start_date"] == "2024-01-01"
            assert call_args[1]["end_date"] == "2024-12-31"

    @patch("src.cli.clone.get_user")
    @patch("src.cli.clone.get_transaction_accounts")
    @patch("src.cli.clone.get_categories")
    @patch("src.cli.clone.get_transactions")
    @patch("src.cli.clone.PocketSmithClient")
    def test_clone_handles_this_month_option(
        self,
        mock_client_class,
        mock_get_transactions,
        mock_get_categories,
        mock_get_transaction_accounts,
        mock_get_user,
    ):
        """Test that clone handles --this-month option."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Setup mocks
            mock_client, mock_get_transactions = setup_mocks(
                mock_client_class,
                mock_get_transactions,
                mock_get_categories,
                mock_get_transaction_accounts,
                mock_get_user,
                [],
            )

            runner.invoke(app, ["clone", str(dest_path), "--this-month"])

            # Should call get_transactions with this month's date range
            mock_get_transactions.assert_called_once()
            call_args = mock_get_transactions.call_args

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

            result = runner.invoke(
                app, ["clone", str(dest_path), "--from", "invalid-date"]
            )

            assert result.exit_code != 0
            assert "Unsupported date format" in result.output


class TestCloneCommandQuietMode:
    """Test clone command quiet mode."""

    @patch("src.cli.clone.get_user")
    @patch("src.cli.clone.get_transaction_accounts")
    @patch("src.cli.clone.get_categories")
    @patch("src.cli.clone.get_transactions")
    @patch("src.cli.clone.PocketSmithClient")
    def test_clone_quiet_suppresses_output(
        self,
        mock_client_class,
        mock_get_transactions,
        mock_get_categories,
        mock_get_transaction_accounts,
        mock_get_user,
    ):
        """Test that --quiet suppresses informational output."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Setup mocks
            mock_client, mock_get_transactions = setup_mocks(
                mock_client_class,
                mock_get_transactions,
                mock_get_categories,
                mock_get_transaction_accounts,
                mock_get_user,
                [
                    {
                        "id": 1,
                        "payee": "Test Payee",
                        "amount": "10.00",
                        "date": "2024-01-01",
                        "currency_code": "USD",
                    }
                ],
            )

            result = runner.invoke(app, ["clone", str(dest_path), "--quiet"])

            assert result.exit_code == 0
            # Should not contain informational messages
            assert "Connecting to PocketSmith API" not in result.output
            assert "Fetching transactions" not in result.output
            # Should not contain summary
            assert "Ledger written to" not in result.output

    @patch("src.cli.clone.get_user")
    @patch("src.cli.clone.get_transaction_accounts")
    @patch("src.cli.clone.get_categories")
    @patch("src.cli.clone.get_transactions")
    @patch("src.cli.clone.PocketSmithClient")
    def test_clone_normal_shows_summary(
        self,
        mock_client_class,
        mock_get_transactions,
        mock_get_categories,
        mock_get_transaction_accounts,
        mock_get_user,
    ):
        """Test that normal mode shows summary output."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Setup mocks
            mock_client, mock_get_transactions = setup_mocks(
                mock_client_class,
                mock_get_transactions,
                mock_get_categories,
                mock_get_transaction_accounts,
                mock_get_user,
                [
                    {
                        "id": 1,
                        "payee": "Test Payee",
                        "amount": "10.00",
                        "date": "2024-01-01",
                        "currency_code": "USD",
                    }
                ],
            )

            result = runner.invoke(app, ["clone", str(dest_path)])

            assert result.exit_code == 0
            # Should contain summary
            assert "Ledger written to" in result.output
            assert "Changelog written to" in result.output
            assert "transactions cloned between dates" in result.output

    @patch("src.cli.clone.get_user")
    @patch("src.cli.clone.get_transaction_accounts")
    @patch("src.cli.clone.get_categories")
    @patch("src.cli.clone.get_transactions")
    @patch("src.cli.clone.PocketSmithClient")
    def test_clone_summary_shows_null_dates(
        self,
        mock_client_class,
        mock_get_transactions,
        mock_get_categories,
        mock_get_transaction_accounts,
        mock_get_user,
    ):
        """Test that summary shows (null) for unspecified dates."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Setup mocks
            mock_client, mock_get_transactions = setup_mocks(
                mock_client_class,
                mock_get_transactions,
                mock_get_categories,
                mock_get_transaction_accounts,
                mock_get_user,
                [],
            )

            result = runner.invoke(app, ["clone", str(dest_path)])

            assert result.exit_code == 0
            assert "(null) to (null)" in result.output


class TestCloneCommandHelp:
    """Test clone command help and documentation."""

    def test_clone_help_text(self):
        """Test that clone command shows helpful help text."""
        runner = CliRunner()

        result = runner.invoke(app, ["clone", "--help"])

        assert result.exit_code == 0
        assert "Download PocketSmith transactions" in result.stdout
        # The help text mentions the key options in the description
        assert "single" in result.stdout.lower()  # References single file mode
        assert "LEDGER" in result.stdout  # Shows the required argument

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

        assert "ledger" in params
        assert "single_file" in params
        assert "from_date" in params
        assert "to_date" in params
        assert "this_month" in params
        assert "last_month" in params
        assert "this_year" in params
        assert "last_year" in params
        assert "quiet" in params

        # Should NOT have limit or all_transactions
        assert "limit" not in params
        assert "all_transactions" not in params


class TestCloneCommandNoTransactions:
    """Test clone command behavior when no transactions are found."""

    @patch("src.cli.clone.get_user")
    @patch("src.cli.clone.get_transaction_accounts")
    @patch("src.cli.clone.get_categories")
    @patch("src.cli.clone.get_transactions")
    @patch("src.cli.clone.PocketSmithClient")
    def test_clone_handles_no_transactions(
        self,
        mock_client_class,
        mock_get_transactions,
        mock_get_categories,
        mock_get_transaction_accounts,
        mock_get_user,
    ):
        """Test that clone handles no transactions gracefully."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "output"

            # Setup mocks
            mock_client, mock_get_transactions = setup_mocks(
                mock_client_class,
                mock_get_transactions,
                mock_get_categories,
                mock_get_transaction_accounts,
                mock_get_user,
                [],
            )

            result = runner.invoke(app, ["clone", str(dest_path)])

            assert result.exit_code == 0
            assert "0 transactions cloned" in result.output

            # Should still create changelog
            changelog_path = dest_path / "main.log"
            assert changelog_path.exists()

            content = changelog_path.read_text()
            assert "CLONE" in content
