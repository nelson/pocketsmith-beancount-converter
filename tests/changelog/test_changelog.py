"""Tests for changelog.changelog module functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch
from datetime import datetime
from hypothesis import given, strategies as st

from src.changelog.changelog import (
    TransactionChangelog,
    print_changelog_summary,
)


class TestTransactionChangelog:
    """Test TransactionChangelog class functionality."""

    def test_init_with_default_output_dir(self):
        """Test initialization with default output directory."""
        changelog = TransactionChangelog()

        assert changelog.output_dir == Path("./output")
        assert changelog.changelog_file == Path("./output/changelog.txt")
        assert changelog.printer is not None

    def test_init_with_custom_output_dir(self):
        """Test initialization with custom output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            assert changelog.output_dir == Path(temp_dir)
            assert changelog.changelog_file == Path(temp_dir) / "changelog.txt"

    def test_init_creates_output_directory(self):
        """Test that initialization creates output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_dir = Path(temp_dir) / "nested" / "changelog"
            TransactionChangelog(str(custom_dir))

            assert custom_dir.exists()
            assert custom_dir.is_dir()

    def test_get_aest_timestamp(self):
        """Test AEST timestamp generation."""
        changelog = TransactionChangelog()

        with patch("src.changelog.changelog.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 10, 30, 45, 123456)
            mock_datetime.now.return_value = mock_now

            timestamp = changelog._get_aest_timestamp()

            # Should be in format "Jan 15 HH:MM:SS.mmm"
            assert timestamp.startswith("Jan 15")
            assert ":" in timestamp
            assert "." in timestamp

    def test_format_changelog_entry_create(self):
        """Test formatting CREATE changelog entry."""
        changelog = TransactionChangelog()

        with patch.object(
            changelog, "_get_aest_timestamp", return_value="Jan 15 10:30:45.123"
        ):
            entry = changelog._format_changelog_entry("CREATE", "123")

            assert entry == "Jan 15 10:30:45.123 CREATE 123"

    def test_format_changelog_entry_delete(self):
        """Test formatting DELETE changelog entry."""
        changelog = TransactionChangelog()

        with patch.object(
            changelog, "_get_aest_timestamp", return_value="Jan 15 10:30:45.123"
        ):
            entry = changelog._format_changelog_entry("DELETE", "123")

            assert entry == "Jan 15 10:30:45.123 DELETE 123"

    def test_format_changelog_entry_modify(self):
        """Test formatting MODIFY changelog entry."""
        changelog = TransactionChangelog()
        field_changes = {
            "amount": ("100.00", "150.00"),
            "payee": ("Old Merchant", "New Merchant"),
        }

        with patch.object(
            changelog, "_get_aest_timestamp", return_value="Jan 15 10:30:45.123"
        ):
            entry = changelog._format_changelog_entry("MODIFY", "123", field_changes)

            assert "Jan 15 10:30:45.123 MODIFY 123" in entry
            assert "amount: 100.00 -> 150.00" in entry
            assert "payee: Old Merchant -> New Merchant" in entry

    def test_format_changelog_entry_modify_tags(self):
        """Test formatting MODIFY entry with tags."""
        changelog = TransactionChangelog()
        field_changes = {"tags": (["old_tag"], ["new_tag", "another_tag"])}

        with patch.object(
            changelog, "_get_aest_timestamp", return_value="Jan 15 10:30:45.123"
        ):
            entry = changelog._format_changelog_entry("MODIFY", "123", field_changes)

            assert "tags: #old_tag -> #new_tag #another_tag" in entry

    def test_format_changelog_entry_modify_empty_tags(self):
        """Test formatting MODIFY entry with empty tags."""
        changelog = TransactionChangelog()
        field_changes = {"labels": ([], ["new_label"])}

        with patch.object(
            changelog, "_get_aest_timestamp", return_value="Jan 15 10:30:45.123"
        ):
            entry = changelog._format_changelog_entry("MODIFY", "123", field_changes)

            assert "labels: [] -> #new_label" in entry

    def test_log_transaction_create(self):
        """Test logging transaction creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)
            transaction = {"id": "123", "payee": "Test Merchant"}

            with patch.object(changelog, "_append_to_changelog") as mock_append:
                changelog.log_transaction_create(transaction)

                mock_append.assert_called_once()
                call_args = mock_append.call_args[0][0]
                assert "CREATE 123" in call_args

    def test_log_transaction_delete(self):
        """Test logging transaction deletion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            with patch.object(changelog, "_append_to_changelog") as mock_append:
                changelog.log_transaction_delete("123")

                mock_append.assert_called_once()
                call_args = mock_append.call_args[0][0]
                assert "DELETE 123" in call_args

    def test_log_transaction_modify(self):
        """Test logging transaction modification."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)
            field_changes = {"amount": ("100.00", "150.00")}

            with patch.object(changelog, "_append_to_changelog") as mock_append:
                changelog.log_transaction_modify("123", field_changes)

                mock_append.assert_called_once()
                call_args = mock_append.call_args[0][0]
                assert "MODIFY 123" in call_args
                assert "amount: 100.00 -> 150.00" in call_args

    def test_append_to_changelog(self):
        """Test appending entry to changelog file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)
            entry = "Test entry"

            changelog._append_to_changelog(entry)

            content = changelog.changelog_file.read_text()
            assert content == "Test entry\n"

    def test_append_to_changelog_multiple_entries(self):
        """Test appending multiple entries to changelog file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            changelog._append_to_changelog("First entry")
            changelog._append_to_changelog("Second entry")

            content = changelog.changelog_file.read_text()
            lines = content.strip().split("\n")
            assert len(lines) == 2
            assert lines[0] == "First entry"
            assert lines[1] == "Second entry"

    def test_get_changelog_path(self):
        """Test getting changelog file path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            path = changelog.get_changelog_path()
            expected_path = str(Path(temp_dir) / "changelog.txt")
            assert path == expected_path

    def test_compare_transactions_create(self):
        """Test comparing transactions and detecting creations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            old_transactions = []
            new_transactions = [{"id": "123", "payee": "New Merchant"}]

            with patch.object(changelog, "log_transaction_create") as mock_create:
                stats = changelog.compare_transactions(
                    old_transactions, new_transactions
                )

                assert stats["created"] == 1
                assert stats["deleted"] == 0
                assert stats["modified"] == 0
                mock_create.assert_called_once_with(
                    {"id": "123", "payee": "New Merchant"}
                )

    def test_compare_transactions_delete(self):
        """Test comparing transactions and detecting deletions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            old_transactions = [{"id": "123", "payee": "Old Merchant"}]
            new_transactions = []

            with patch.object(changelog, "log_transaction_delete") as mock_delete:
                stats = changelog.compare_transactions(
                    old_transactions, new_transactions
                )

                assert stats["created"] == 0
                assert stats["deleted"] == 1
                assert stats["modified"] == 0
                mock_delete.assert_called_once_with("123")

    def test_compare_transactions_modify(self):
        """Test comparing transactions and detecting modifications."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            old_transactions = [
                {"id": "123", "payee": "Old Merchant", "amount": "100.00"}
            ]
            new_transactions = [
                {"id": "123", "payee": "New Merchant", "amount": "100.00"}
            ]

            with patch.object(changelog, "log_transaction_modify") as mock_modify:
                stats = changelog.compare_transactions(
                    old_transactions, new_transactions
                )

                assert stats["created"] == 0
                assert stats["deleted"] == 0
                assert stats["modified"] == 1
                mock_modify.assert_called_once()

    def test_detect_changes_amount(self):
        """Test detecting changes in transaction amount."""
        changelog = TransactionChangelog()

        old_transaction = {"id": "123", "amount": "100.00"}
        new_transaction = {"id": "123", "amount": "150.00"}

        changes = changelog._detect_changes(old_transaction, new_transaction)

        assert "amount" in changes
        assert changes["amount"] == ("100.00", "150.00")

    def test_detect_changes_labels(self):
        """Test detecting changes in transaction labels."""
        changelog = TransactionChangelog()

        old_transaction = {"id": "123", "labels": ["old_label"]}
        new_transaction = {"id": "123", "labels": ["new_label", "another_label"]}

        changes = changelog._detect_changes(old_transaction, new_transaction)

        assert "labels" in changes
        assert changes["labels"] == (["old_label"], ["new_label", "another_label"])

    def test_detect_changes_category(self):
        """Test detecting changes in transaction category."""
        changelog = TransactionChangelog()

        old_transaction = {
            "id": "123",
            "category": {"id": "1", "title": "Old Category"},
        }
        new_transaction = {
            "id": "123",
            "category": {"id": "2", "title": "New Category"},
        }

        changes = changelog._detect_changes(old_transaction, new_transaction)

        assert "category" in changes
        assert changes["category"] == ("Old Category", "New Category")

    def test_detect_changes_no_changes(self):
        """Test detecting changes when transactions are identical."""
        changelog = TransactionChangelog()

        transaction = {"id": "123", "amount": "100.00", "payee": "Merchant"}

        changes = changelog._detect_changes(transaction, transaction)

        assert changes == {}

    def test_read_changelog_entries_empty_file(self):
        """Test reading entries from empty changelog file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            entries = changelog.read_changelog_entries()
            assert entries == []

    def test_read_changelog_entries_nonexistent_file(self):
        """Test reading entries from nonexistent changelog file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)
            # Don't create the file

            entries = changelog.read_changelog_entries()
            assert entries == []

    def test_read_changelog_entries_with_content(self):
        """Test reading entries from changelog file with content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            # Write some test entries
            changelog._append_to_changelog("Jan 15 10:30:45.123 CREATE 123")
            changelog._append_to_changelog(
                "Jan 15 10:31:00.456 MODIFY 124 amount: 100.00 -> 150.00"
            )
            changelog._append_to_changelog("")  # Empty line should be filtered

            entries = changelog.read_changelog_entries()

            assert len(entries) == 2
            assert "CREATE 123" in entries[0]
            assert "MODIFY 124" in entries[1]

    def test_read_changelog_entries_with_limit(self):
        """Test reading entries with limit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            # Write multiple entries
            for i in range(5):
                changelog._append_to_changelog(f"Entry {i}")

            entries = changelog.read_changelog_entries(limit=3)

            assert len(entries) == 3
            # Should return the last 3 entries
            assert "Entry 2" in entries[0]
            assert "Entry 3" in entries[1]
            assert "Entry 4" in entries[2]

    def test_print_recent_changes(self):
        """Test printing recent changelog entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            changelog._append_to_changelog("Test entry")

            with patch.object(
                changelog.printer, "print_changelog_entries"
            ) as mock_print:
                changelog.print_recent_changes(10)

                mock_print.assert_called_once()
                call_args = mock_print.call_args[0][0]
                assert "Test entry" in call_args

    def test_get_changelog_stats_empty(self):
        """Test getting stats from empty changelog."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            stats = changelog.get_changelog_stats()

            assert stats["CREATE"] == 0
            assert stats["DELETE"] == 0
            assert stats["MODIFY"] == 0
            assert stats["total"] == 0

    def test_get_changelog_stats_with_entries(self):
        """Test getting stats from changelog with entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            changelog._append_to_changelog("Jan 15 10:30:45.123 CREATE 123")
            changelog._append_to_changelog("Jan 15 10:31:00.456 CREATE 124")
            changelog._append_to_changelog(
                "Jan 15 10:32:00.789 MODIFY 123 amount: 100.00 -> 150.00"
            )
            changelog._append_to_changelog("Jan 15 10:33:00.012 DELETE 125")

            stats = changelog.get_changelog_stats()

            assert stats["CREATE"] == 2
            assert stats["DELETE"] == 1
            assert stats["MODIFY"] == 1
            assert stats["total"] == 4


class TestPrintChangelogSummary:
    """Test print_changelog_summary function."""

    def test_print_changelog_summary_empty(self, capsys):
        """Test printing summary for empty changelog."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            print_changelog_summary(changelog)

            captured = capsys.readouterr()
            assert "No changelog entries found" in captured.out

    def test_print_changelog_summary_with_entries(self, capsys):
        """Test printing summary for changelog with entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            # Add some test entries
            changelog._append_to_changelog("Jan 15 10:30:45.123 CREATE 123")
            changelog._append_to_changelog(
                "Jan 15 10:31:00.456 MODIFY 124 amount: 100.00 -> 150.00"
            )

            with patch.object(changelog, "print_recent_changes"):
                print_changelog_summary(changelog)

                captured = capsys.readouterr()
                assert "Changelog Summary:" in captured.out
                assert "Total entries: 2" in captured.out
                assert "Created: 1" in captured.out
                assert "Modified: 1" in captured.out
                assert "Deleted: 0" in captured.out


class TestPropertyBasedTests:
    """Property-based tests for changelog functionality."""

    @given(
        st.dictionaries(
            keys=st.sampled_from(["id", "payee", "amount", "memo", "labels", "tags"]),
            values=st.one_of(
                st.text(min_size=1, max_size=50),
                st.lists(st.text(min_size=1, max_size=20), max_size=10),
            ),
            min_size=1,
        )
    )
    def test_log_transaction_create_properties(self, transaction):
        """Property test: logging transaction creation should always work."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            # Should not raise exception
            changelog.log_transaction_create(transaction)

            # Should create an entry in the file
            content = changelog.changelog_file.read_text()
            assert "CREATE" in content

    @given(
        st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(categories=["Nd", "Lu", "Ll"]),
        )
    )
    def test_log_transaction_delete_properties(self, transaction_id):
        """Property test: logging transaction deletion should always work."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            changelog.log_transaction_delete(transaction_id)

            content = changelog.changelog_file.read_text()
            assert "DELETE" in content
            assert transaction_id in content

    @given(
        st.lists(
            st.dictionaries(
                keys=st.just("id"),
                values=st.text(
                    min_size=1,
                    max_size=20,
                    alphabet=st.characters(categories=["Nd", "Lu", "Ll"]),
                ),
            ),
            min_size=0,
            max_size=10,
        )
    )
    def test_compare_transactions_properties(self, transactions):
        """Property test: comparing transactions should return valid stats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            # Only unique transactions with valid IDs will be processed
            seen_ids = set()
            unique_valid_transactions = []
            for t in transactions:
                if t.get("id") and t["id"] not in seen_ids:
                    unique_valid_transactions.append(t)
                    seen_ids.add(t["id"])

            stats = changelog.compare_transactions([], transactions)

            # Should return dict with required keys
            assert isinstance(stats, dict)
            assert "created" in stats
            assert "deleted" in stats
            assert "modified" in stats

            # Stats should be non-negative integers
            assert stats["created"] >= 0
            assert stats["deleted"] >= 0
            assert stats["modified"] >= 0

            # Created count should match number of unique valid transactions
            assert stats["created"] == len(unique_valid_transactions)

    @given(
        st.text(
            min_size=0,
            max_size=200,
            alphabet=st.characters(
                blacklist_categories=["Cc", "Cs"], blacklist_characters="\r\n"
            ),
        )
    )
    def test_changelog_file_operations_properties(self, content):
        """Property test: file operations should handle any content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = TransactionChangelog(temp_dir)

            # Should be able to append any text content
            changelog._append_to_changelog(content)

            # Should be able to read it back
            entries = changelog.read_changelog_entries()

            if content.strip():  # Non-empty content
                assert len(entries) >= 0
                if entries:
                    # Content should be preserved in some form
                    assert content.strip() in entries[0] or content in entries[0]
