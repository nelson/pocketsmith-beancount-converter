"""Tests for the changelog module."""

import tempfile
from pathlib import Path
from datetime import datetime

from src.cli.changelog import ChangelogManager, ChangelogEntry, determine_changelog_path


class TestChangelogEntry:
    """Test the ChangelogEntry dataclass."""

    def test_clone_entry_format(self):
        """Test formatting of CLONE entries."""
        entry = ChangelogEntry(
            timestamp=datetime(2024, 1, 15, 10, 30, 45),
            operation="CLONE",
            details=["2024-01-01", "2024-01-31"],
        )

        assert str(entry) == "[2024-01-15 10:30:45] CLONE 2024-01-01 2024-01-31"

    def test_clone_entry_with_null_dates(self):
        """Test CLONE entry with null dates."""
        entry = ChangelogEntry(
            timestamp=datetime(2024, 1, 15, 10, 30, 45),
            operation="CLONE",
            details=["", ""],
        )

        assert str(entry) == "[2024-01-15 10:30:45] CLONE  "

    def test_pull_entry_format(self):
        """Test formatting of PULL entries."""
        entry = ChangelogEntry(
            timestamp=datetime(2024, 1, 15, 10, 30, 45),
            operation="PULL",
            details=["2024-01-14T09:00:00", "2024-01-01", "2024-01-31"],
        )

        assert (
            str(entry)
            == "[2024-01-15 10:30:45] PULL 2024-01-14T09:00:00 2024-01-01 2024-01-31"
        )

    def test_overwrite_entry_format(self):
        """Test formatting of OVERWRITE entries."""
        entry = ChangelogEntry(
            timestamp=datetime(2024, 1, 15, 10, 30, 45),
            operation="OVERWRITE",
            details=["12345", "amount", "100.00 → 150.00"],
        )

        assert (
            str(entry) == "[2024-01-15 10:30:45] OVERWRITE 12345 amount 100.00 → 150.00"
        )


class TestChangelogManager:
    """Test the ChangelogManager class."""

    def test_write_clone_entry(self):
        """Test writing a CLONE entry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog_path = Path(temp_dir) / "test.log"
            manager = ChangelogManager(changelog_path)

            manager.write_clone_entry("2024-01-01", "2024-01-31")

            assert changelog_path.exists()
            content = changelog_path.read_text()
            assert "CLONE 2024-01-01 2024-01-31" in content

    def test_write_pull_entry(self):
        """Test writing a PULL entry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog_path = Path(temp_dir) / "test.log"
            manager = ChangelogManager(changelog_path)

            manager.write_pull_entry("2024-01-14T09:00:00", "2024-01-01", "2024-01-31")

            assert changelog_path.exists()
            content = changelog_path.read_text()
            assert "PULL 2024-01-14T09:00:00 2024-01-01 2024-01-31" in content

    def test_write_overwrite_entry(self):
        """Test writing an OVERWRITE entry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog_path = Path(temp_dir) / "test.log"
            manager = ChangelogManager(changelog_path)

            manager.write_overwrite_entry("12345", "amount", "100.00", "150.00")

            assert changelog_path.exists()
            content = changelog_path.read_text()
            assert "OVERWRITE 12345 amount 100.00 → 150.00" in content

    def test_write_update_entry(self):
        """Test writing an UPDATE entry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog_path = Path(temp_dir) / "test.log"
            manager = ChangelogManager(changelog_path)

            manager.write_update_entry("12345", "category", "Food", "Transport")

            assert changelog_path.exists()
            content = changelog_path.read_text()
            assert "UPDATE 12345 category Food → Transport" in content

    def test_get_last_sync_info_no_file(self):
        """Test getting sync info when no file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog_path = Path(temp_dir) / "test.log"
            manager = ChangelogManager(changelog_path)

            result = manager.get_last_sync_info()
            assert result is None

    def test_get_last_sync_info_from_clone(self):
        """Test getting sync info from CLONE entry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog_path = Path(temp_dir) / "test.log"
            manager = ChangelogManager(changelog_path)

            # Write a CLONE entry
            manager.write_clone_entry("2024-01-01", "2024-01-31")

            result = manager.get_last_sync_info()
            assert result is not None
            timestamp, from_date, to_date = result
            assert isinstance(timestamp, datetime)
            assert from_date == "2024-01-01"
            assert to_date == "2024-01-31"

    def test_get_last_sync_info_from_pull(self):
        """Test getting sync info from PULL entry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog_path = Path(temp_dir) / "test.log"
            manager = ChangelogManager(changelog_path)

            # Write entries
            manager.write_clone_entry("2024-01-01", "2024-01-31")
            manager.write_pull_entry("2024-01-14T09:00:00", "2024-02-01", "2024-02-29")

            result = manager.get_last_sync_info()
            assert result is not None
            timestamp, from_date, to_date = result
            assert isinstance(timestamp, datetime)
            assert from_date == "2024-02-01"
            assert to_date == "2024-02-29"

    def test_get_last_sync_info_ignores_overwrite(self):
        """Test that OVERWRITE entries are ignored for sync info."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog_path = Path(temp_dir) / "test.log"
            manager = ChangelogManager(changelog_path)

            # Write entries
            manager.write_clone_entry("2024-01-01", "2024-01-31")
            manager.write_overwrite_entry("12345", "amount", "100.00", "150.00")

            result = manager.get_last_sync_info()
            assert result is not None
            timestamp, from_date, to_date = result
            assert from_date == "2024-01-01"
            assert to_date == "2024-01-31"

    def test_multiple_entries_appended(self):
        """Test that multiple entries are properly appended."""
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog_path = Path(temp_dir) / "test.log"
            manager = ChangelogManager(changelog_path)

            manager.write_clone_entry("2024-01-01", "2024-01-31")
            manager.write_overwrite_entry("12345", "amount", "100.00", "150.00")
            manager.write_pull_entry("2024-01-14T09:00:00", "2024-01-01", "2024-01-31")

            content = changelog_path.read_text()
            lines = content.strip().split("\n")
            assert len(lines) == 3
            assert "CLONE" in lines[0]
            assert "OVERWRITE" in lines[1]
            assert "PULL" in lines[2]


class TestDetermineChangelogPath:
    """Test the determine_changelog_path function."""

    def test_single_file_mode(self):
        """Test changelog path for single file mode."""
        destination = Path("/tmp/transactions.beancount")
        result = determine_changelog_path(destination, single_file=True)
        assert result == Path("/tmp/transactions.log")

    def test_hierarchical_mode(self):
        """Test changelog path for hierarchical mode."""
        destination = Path("/tmp/output")
        result = determine_changelog_path(destination, single_file=False)
        assert result == Path("/tmp/output/main.log")

    def test_single_file_different_extension(self):
        """Test single file mode with different extension."""
        destination = Path("/tmp/data.bean")
        result = determine_changelog_path(destination, single_file=True)
        assert result == Path("/tmp/data.log")

    def test_single_file_no_extension(self):
        """Test single file mode with no extension."""
        destination = Path("/tmp/ledger")
        result = determine_changelog_path(destination, single_file=True)
        assert result == Path("/tmp/ledger.log")
