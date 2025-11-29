"""Tests for the diff command."""

from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from click.exceptions import Exit

from src.cli.diff import diff_command, DiffComparator
from src.cli.date_options import DateOptions


class TestDiffComparator:
    """Test the DiffComparator class."""

    def test_compare_for_diff_identical_transactions(self):
        """Test comparison when transactions are identical."""
        comparator = DiffComparator()

        local_transactions = {
            "1": {
                "id": 1,
                "amount": "100.00",
                "payee": "Test Merchant",
                "category_id": 1,
                "labels": ["tag1", "tag2"],
                "note": "Test note",
            }
        }

        remote_transactions = [
            {
                "id": 1,
                "amount": "100.00",
                "payee": "Test Merchant",
                "category_id": 1,
                "labels": ["tag1", "tag2"],
                "note": "Test note",
            }
        ]

        comparator.compare_for_diff(local_transactions, remote_transactions)

        assert comparator.identical_count == 1
        assert comparator.different_count == 0
        assert comparator.not_fetched_count == 0
        assert len(comparator.differences) == 0

    def test_compare_for_diff_different_transactions(self):
        """Test comparison when transactions differ."""
        comparator = DiffComparator()

        local_transactions = {
            "1": {
                "id": 1,
                "amount": "100.00",
                "payee": "Local Merchant",
                "category_id": 1,
                "labels": ["local-tag"],
                "note": "Local note",
            }
        }

        remote_transactions = [
            {
                "id": 1,
                "amount": "100.00",
                "payee": "Remote Merchant",  # Different
                "category_id": 2,  # Different
                "labels": ["remote-tag"],  # Different
                "note": "Remote note",  # Different
            }
        ]

        comparator.compare_for_diff(local_transactions, remote_transactions)

        assert comparator.identical_count == 0
        assert comparator.different_count == 1
        assert comparator.not_fetched_count == 0
        assert len(comparator.differences) == 1

        # Check differences detected
        diff = comparator.differences[0]
        assert diff["id"] == "1"
        assert len(diff["changes"]) == 4  # payee, category, labels, note

    def test_compare_for_diff_not_fetched_transactions(self):
        """Test comparison with transactions not fetched from remote."""
        comparator = DiffComparator()

        local_transactions = {
            "1": {"id": 1, "payee": "Transaction 1"},
            "2": {"id": 2, "payee": "Transaction 2"},
        }

        remote_transactions = [
            {"id": 1, "payee": "Transaction 1"}  # Only transaction 1 fetched
        ]

        comparator.compare_for_diff(local_transactions, remote_transactions)

        assert comparator.identical_count == 1
        assert comparator.different_count == 0
        assert comparator.not_fetched_count == 1

    def test_compare_normalizes_payee_backslash(self):
        """Test that stray backslashes in payees are ignored."""
        comparator = DiffComparator()
        local_transactions = {
            "1": {
                "id": 1,
                "payee": "EFTPOS SMP*HERO SUSHI STRATHF STRATHFIELD02 AU",
            }
        }
        remote_transactions = [
            {
                "id": 1,
                "payee": "EFTPOS SMP*HERO SUSHI STRATHF \\STRATHFIELD02 AU",
            }
        ]

        comparator.compare_for_diff(local_transactions, remote_transactions)

        assert comparator.different_count == 0
        assert comparator.identical_count == 1

    def test_format_summary(self):
        """Test formatting summary output."""
        comparator = DiffComparator()
        comparator.total_fetched = 10
        comparator.different_count = 3
        comparator.identical_count = 7
        comparator.not_fetched_count = 2

        summary = comparator.format_summary("2024-01-01", "2024-01-31")

        assert (
            "10 existing transactions were fetched between dates 2024-01-01 to 2024-01-31"
            in summary
        )
        assert "3 transactions were different on the local ledger" in summary
        assert "7 transactions were identical to the local ledger" in summary
        assert (
            "2 transactions on the local ledger were not fetched from remote" in summary
        )

    def test_format_ids(self):
        """Test formatting transaction IDs output."""
        comparator = DiffComparator()
        comparator.differences = [
            {"id": "123", "changes": []},
            {"id": "456", "changes": []},
            {"id": "789", "changes": []},
        ]

        ids_output = comparator.format_ids()

        assert "123" in ids_output
        assert "456" in ids_output
        assert "789" in ids_output

    def test_format_changelog(self):
        """Test formatting changelog output."""
        comparator = DiffComparator()
        comparator.differences = [
            {
                "id": "123",
                "changes": [
                    ("payee", "Old Payee", "New Payee"),
                    ("category", "1", "2"),
                ],
            }
        ]

        changelog_output = comparator.format_changelog()

        assert "DIFF 123 payee Old Payee <> New Payee" in changelog_output
        assert "DIFF 123 category 1 <> 2" in changelog_output

    def test_format_diff(self):
        """Test formatting diff-style output."""
        comparator = DiffComparator()
        comparator.set_category_lookup({"24918120": "Expenses:Eating-Out"})
        comparator.differences = [
            {
                "id": "123",
                "local": {
                    "source_filename": "/tmp/2025/2025-11.beancount",
                    "source_lineno": 42,
                },
                "changes": [
                    ("payee", "Local Payee", "Remote Payee"),
                    ("category", "24918120", "null"),
                ],
            }
        ]

        ledger_path = Path("/tmp/test.beancount")
        diff_output = comparator.format_diff(ledger_path, single_file=False)

        assert "peabody diff 123" in diff_output
        assert (
            "--- remote:: GET https://api.pocketsmith.com/v2/transactions/123"
            in diff_output
        )
        assert "+++ local:: FILE /tmp/2025/2025-11.beancount:42" in diff_output
        assert "-   payee: Remote Payee" in diff_output
        assert "+   payee: Local Payee" in diff_output
        assert "-   category: null" in diff_output
        assert "+   category: Expenses:Eating-Out" in diff_output


class TestDiffCommand:
    """Test the diff command."""

    @patch("src.cli.diff.handle_default_ledger")
    @patch("src.cli.diff.PocketSmithClient")
    @patch("src.cli.diff.read_local_transactions")
    def test_diff_default_file_detection(
        self, mock_read_local, mock_client_class, mock_handle_default
    ):
        """Test diff command with default file detection."""
        # Mock default file detection
        mock_destination = Mock(spec=Path)
        mock_destination.exists.return_value = True
        mock_handle_default.return_value = (mock_destination, "test source")

        # Mock empty local transactions
        mock_read_local.return_value = {}

        # Mock API client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_user.return_value = {"login": "test_user"}
        mock_client.get_transactions.return_value = []

        with patch("src.cli.diff.determine_single_file_mode") as mock_determine_mode:
            mock_determine_mode.return_value = True

            with patch("src.cli.diff.ChangelogManager") as mock_changelog_class:
                mock_changelog = Mock()
                mock_changelog_class.return_value = mock_changelog
                mock_changelog.get_last_sync_info.return_value = (
                    None,
                    "2024-01-01",
                    "2024-01-31",
                )

                # Should not raise error
                date_options = DateOptions()
                diff_command(
                    destination=None,  # No destination provided
                    date_options=date_options,
                    format="summary",
                )

                mock_handle_default.assert_called_once_with(None)

    @patch("src.cli.diff.PocketSmithClient")
    @patch("src.cli.diff.read_local_transactions")
    def test_diff_summary_format(self, mock_read_local, mock_client_class):
        """Test diff command with summary format."""
        # Mock local transactions
        mock_read_local.return_value = {"1": {"id": 1, "payee": "Local"}}

        # Mock API client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_user.return_value = {"login": "test_user"}
        mock_client.get_transactions.return_value = [
            {"id": 1, "payee": "Remote"}  # Different payee
        ]

        mock_destination = Mock(spec=Path)
        mock_destination.exists.return_value = True

        with patch("src.cli.diff.determine_single_file_mode") as mock_determine_mode:
            mock_determine_mode.return_value = True

            with patch("src.cli.diff.ChangelogManager") as mock_changelog_class:
                mock_changelog = Mock()
                mock_changelog_class.return_value = mock_changelog
                mock_changelog.get_last_sync_info.return_value = (
                    None,
                    "2024-01-01",
                    "2024-01-31",
                )

                with patch("src.cli.diff.typer.echo") as mock_echo:
                    date_options = DateOptions()
                    diff_command(
                        destination=mock_destination,
                        format="summary",
                        date_options=date_options,
                    )

                    # Should output summary
                    mock_echo.assert_called_once()
                    output = mock_echo.call_args[0][0]
                    assert "existing transactions were fetched" in output

    @patch("src.cli.diff.PocketSmithClient")
    @patch("src.cli.diff.read_local_transactions")
    def test_diff_ids_format(self, mock_read_local, mock_client_class):
        """Test diff command with ids format."""
        # Mock local transactions
        mock_read_local.return_value = {
            "1": {"id": 1, "payee": "Local1"},
            "2": {"id": 2, "payee": "Local2"},
        }

        # Mock API client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_user.return_value = {"login": "test_user"}
        mock_client.get_transactions.return_value = [
            {"id": 1, "payee": "Remote1"},  # Different
            {"id": 2, "payee": "Local2"},  # Same
        ]

        mock_destination = Mock(spec=Path)
        mock_destination.exists.return_value = True

        with patch("src.cli.diff.determine_single_file_mode") as mock_determine_mode:
            mock_determine_mode.return_value = True

            with patch("src.cli.diff.ChangelogManager") as mock_changelog_class:
                mock_changelog = Mock()
                mock_changelog_class.return_value = mock_changelog
                mock_changelog.get_last_sync_info.return_value = (
                    None,
                    "2024-01-01",
                    "2024-01-31",
                )

                with patch("src.cli.diff.typer.echo") as mock_echo:
                    date_options = DateOptions()
                    diff_command(
                        destination=mock_destination,
                        format="ids",
                        date_options=date_options,
                    )

                    # Should output only ID 1 (which is different)
                    mock_echo.assert_called_once()
                    output = mock_echo.call_args[0][0]
                    assert "1" in output
                    assert "2" not in output

    @patch("src.cli.diff.PocketSmithClient")
    @patch("src.cli.diff.read_local_transactions")
    def test_diff_changelog_format(self, mock_read_local, mock_client_class):
        """Test diff command with changelog format."""
        # Mock local transactions
        mock_read_local.return_value = {"1": {"id": 1, "payee": "Local Payee"}}

        # Mock API client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_user.return_value = {"login": "test_user"}
        mock_client.get_transactions.return_value = [
            {"id": 1, "payee": "Remote Payee"}  # Different payee
        ]

        mock_destination = Mock(spec=Path)
        mock_destination.exists.return_value = True

        with patch("src.cli.diff.determine_single_file_mode") as mock_determine_mode:
            mock_determine_mode.return_value = True

            with patch("src.cli.diff.ChangelogManager") as mock_changelog_class:
                mock_changelog = Mock()
                mock_changelog_class.return_value = mock_changelog
                mock_changelog.get_last_sync_info.return_value = (
                    None,
                    "2024-01-01",
                    "2024-01-31",
                )

                with patch("src.cli.diff.typer.echo") as mock_echo:
                    date_options = DateOptions()
                    diff_command(
                        destination=mock_destination,
                        format="changelog",
                        date_options=date_options,
                    )

                    # Should output changelog format
                    mock_echo.assert_called_once()
                    output = mock_echo.call_args[0][0]
                    assert "DIFF 1 payee Local Payee <> Remote Payee" in output

    @patch("src.cli.diff.PocketSmithClient")
    @patch("src.cli.diff.read_local_transactions")
    def test_diff_diff_format(self, mock_read_local, mock_client_class):
        """Test diff command with diff format."""
        # Mock local transactions
        mock_read_local.return_value = {"1": {"id": 1, "payee": "Local Payee"}}

        # Mock API client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_user.return_value = {"login": "test_user"}
        mock_client.get_transactions.return_value = [
            {"id": 1, "payee": "Remote Payee"}  # Different payee
        ]

        mock_destination = Mock(spec=Path)
        mock_destination.exists.return_value = True

        with patch("src.cli.diff.determine_single_file_mode") as mock_determine_mode:
            mock_determine_mode.return_value = True

            with patch("src.cli.diff.ChangelogManager") as mock_changelog_class:
                mock_changelog = Mock()
                mock_changelog_class.return_value = mock_changelog
                mock_changelog.get_last_sync_info.return_value = (
                    None,
                    "2024-01-01",
                    "2024-01-31",
                )

                with patch("src.cli.diff.typer.echo") as mock_echo:
                    date_options = DateOptions()
                    diff_command(
                        destination=mock_destination,
                        format="diff",
                        date_options=date_options,
                    )

                    # Should output diff format
                    mock_echo.assert_called_once()
                    output = mock_echo.call_args[0][0]
                    assert "peabody diff 1" in output
                    assert (
                        "--- remote:: GET https://api.pocketsmith.com/v2/transactions/1"
                        in output
                    )
                    assert "+++ local:: FILE" in output

    @patch("src.cli.diff.PocketSmithClient")
    @patch("src.cli.diff.read_local_transactions")
    def test_diff_with_date_range(self, mock_read_local, mock_client_class):
        """Test diff command with specific date range."""
        # Mock local transactions
        mock_read_local.return_value = {}

        # Mock API client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_user.return_value = {"login": "test_user"}
        mock_client.get_transactions.return_value = []

        mock_destination = Mock(spec=Path)
        mock_destination.exists.return_value = True

        with patch("src.cli.diff.determine_single_file_mode") as mock_determine_mode:
            mock_determine_mode.return_value = True

            date_options = DateOptions(from_date="2024-02-01", to_date="2024-02-29")
            diff_command(
                destination=mock_destination,
                format="summary",
                date_options=date_options,
            )

            # Should call get_transactions with specific date range
            mock_client.get_transactions.assert_called_once()
            call_args = mock_client.get_transactions.call_args
            assert call_args[1]["start_date"] == "2024-02-01"
            assert call_args[1]["end_date"] == "2024-02-29"

    @patch("src.cli.diff.PocketSmithClient")
    def test_diff_api_connection_error(self, mock_client_class):
        """Test diff command handles API connection errors."""
        # Mock API client to raise error
        mock_client_class.side_effect = Exception("API connection failed")

        mock_destination = Mock(spec=Path)
        mock_destination.exists.return_value = True

        with patch("src.cli.diff.determine_single_file_mode") as mock_determine_mode:
            mock_determine_mode.return_value = True

            with patch("src.cli.diff.ChangelogManager") as mock_changelog_class:
                mock_changelog = Mock()
                mock_changelog_class.return_value = mock_changelog
                mock_changelog.get_last_sync_info.return_value = (
                    None,
                    "2024-01-01",
                    "2024-01-31",
                )

                with pytest.raises(Exit):
                    date_options = DateOptions()
                    diff_command(
                        destination=mock_destination,
                        format="summary",
                        date_options=date_options,
                    )

    def test_diff_nonexistent_destination_error(self):
        """Test diff command handles non-existent destination."""
        mock_destination = Mock(spec=Path)
        mock_destination.exists.return_value = False

        with pytest.raises(Exit):
            date_options = DateOptions()
            diff_command(
                destination=mock_destination,
                format="summary",
                date_options=date_options,
            )

    @patch("src.cli.diff.PocketSmithClient")
    @patch("src.cli.diff.read_local_transactions")
    def test_diff_invalid_format_error(self, mock_read_local, mock_client_class):
        """Test diff command handles invalid format."""
        # Mock local transactions
        mock_read_local.return_value = {}

        # Mock API client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_user.return_value = {"login": "test_user"}
        mock_client.get_transactions.return_value = []

        mock_destination = Mock(spec=Path)
        mock_destination.exists.return_value = True

        with patch("src.cli.diff.determine_single_file_mode") as mock_determine_mode:
            mock_determine_mode.return_value = True

            with patch("src.cli.diff.ChangelogManager") as mock_changelog_class:
                mock_changelog = Mock()
                mock_changelog_class.return_value = mock_changelog
                mock_changelog.get_last_sync_info.return_value = (
                    None,
                    "2024-01-01",
                    "2024-01-31",
                )

                with pytest.raises(Exit):
                    date_options = DateOptions()
                    diff_command(
                        destination=mock_destination,
                        format="invalid_format",  # Invalid format
                        date_options=date_options,
                    )
