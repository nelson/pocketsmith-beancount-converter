"""Changelog management for clone and pull operations."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple
import re
from dataclasses import dataclass


@dataclass
class ChangelogEntry:
    """Represents a single changelog entry."""

    timestamp: datetime
    operation: str
    details: List[str]

    def __str__(self) -> str:
        """Format the entry as a string."""
        # Format with timezone info if present, otherwise use naive format for backward compat
        if self.timestamp.tzinfo is not None:
            timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S%z")
        else:
            timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        parts = [f"[{timestamp_str}]", self.operation] + self.details
        return " ".join(parts)


class ChangelogManager:
    """Manages reading and writing changelog files."""

    def __init__(self, changelog_path: Path):
        """Initialize with the path to the changelog file."""
        self.changelog_path = changelog_path

    def write_clone_entry(
        self, from_date: Optional[str], to_date: Optional[str]
    ) -> None:
        """Write a CLONE entry to the changelog."""
        entry = ChangelogEntry(
            timestamp=datetime.now(timezone.utc),
            operation="CLONE",
            details=[from_date or "", to_date or ""],
        )
        self._append_entry(entry)

    def write_pull_entry(
        self, since: str, from_date: Optional[str], to_date: Optional[str]
    ) -> None:
        """Write a PULL entry to the changelog."""
        entry = ChangelogEntry(
            timestamp=datetime.now(timezone.utc),
            operation="PULL",
            details=[since, from_date or "", to_date or ""],
        )
        self._append_entry(entry)

    def write_push_entry(
        self, from_date: Optional[str], to_date: Optional[str]
    ) -> None:
        """Write a PUSH entry to the changelog."""
        entry = ChangelogEntry(
            timestamp=datetime.now(timezone.utc),
            operation="PUSH",
            details=[from_date or "", to_date or ""],
        )
        self._append_entry(entry)

    def write_overwrite_entry(
        self, transaction_id: str, key: str, old_value: str, new_value: str
    ) -> None:
        """Write an OVERWRITE entry to the changelog."""
        entry = ChangelogEntry(
            timestamp=datetime.now(timezone.utc),
            operation="OVERWRITE",
            details=[transaction_id, key, f"{old_value} → {new_value}"],
        )
        self._append_entry(entry)

    def write_update_entry(
        self, transaction_id: str, key: str, old_value: str, new_value: str
    ) -> None:
        """Write an UPDATE entry to the changelog."""
        entry = ChangelogEntry(
            timestamp=datetime.now(timezone.utc),
            operation="UPDATE",
            details=[transaction_id, key, f"{old_value} → {new_value}"],
        )
        self._append_entry(entry)

    def write_apply_entry(
        self, transaction_id: str, rule_id: int, key: str, new_value: str
    ) -> None:
        """Write an APPLY entry to the changelog for rule application."""
        entry = ChangelogEntry(
            timestamp=datetime.now(timezone.utc),
            operation="APPLY",
            details=[transaction_id, "RULE", str(rule_id), key, str(new_value)],
        )
        self._append_entry(entry)

    def get_last_sync_info(
        self,
    ) -> Optional[Tuple[datetime, Optional[str], Optional[str]]]:
        """Get the timestamp and date range from the most recent CLONE or PULL entry.

        Returns:
            Tuple of (timestamp, from_date, to_date) or None if no entries found.
        """
        if not self.changelog_path.exists():
            return None

        entries = self._read_entries()
        for entry in reversed(entries):
            if entry.operation in ("CLONE", "PULL"):
                # For CLONE entries: [timestamp] CLONE [FROM] [TO]
                # For PULL entries: [timestamp] PULL [SINCE] [FROM] [TO]
                if entry.operation == "CLONE":
                    from_date = (
                        entry.details[0]
                        if len(entry.details) > 0 and entry.details[0]
                        else None
                    )
                    to_date = (
                        entry.details[1]
                        if len(entry.details) > 1 and entry.details[1]
                        else None
                    )
                elif entry.operation == "PULL":
                    from_date = (
                        entry.details[1]
                        if len(entry.details) > 1 and entry.details[1]
                        else None
                    )
                    to_date = (
                        entry.details[2]
                        if len(entry.details) > 2 and entry.details[2]
                        else None
                    )

                return (entry.timestamp, from_date, to_date)

        return None

    def _append_entry(self, entry: ChangelogEntry) -> None:
        """Append an entry to the changelog file."""
        self.changelog_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.changelog_path, "a", encoding="utf-8") as f:
            f.write(str(entry) + "\n")

    def _read_entries(self) -> List[ChangelogEntry]:
        """Read all entries from the changelog file."""
        entries = []

        with open(self.changelog_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # Parse timestamp - support both naive and timezone-aware formats
                # New format: [2025-11-27 12:00:14+0000] PULL ...
                # Old format: [2025-11-27 12:00:14] PULL ...
                match = re.match(
                    r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:[+-]\d{4})?)\]\s+(\w+)\s*(.*)",
                    line,
                )
                if match:
                    timestamp_str, operation, details_str = match.groups()

                    # Parse timestamp with or without timezone
                    if "+" in timestamp_str or "-" in timestamp_str[-5:]:
                        # Has timezone (e.g., "2025-11-27 12:00:14+0000")
                        timestamp = datetime.strptime(
                            timestamp_str, "%Y-%m-%d %H:%M:%S%z"
                        )
                    else:
                        # Naive timestamp (old format)
                        timestamp = datetime.strptime(
                            timestamp_str, "%Y-%m-%d %H:%M:%S"
                        )

                    details = details_str.split() if details_str else []

                    entries.append(
                        ChangelogEntry(
                            timestamp=timestamp, operation=operation, details=details
                        )
                    )

        return entries


def determine_changelog_path(destination: Path, single_file: bool) -> Path:
    """Determine the changelog path based on the destination and mode.

    Args:
        destination: The destination path (file or directory)
        single_file: Whether single file mode is being used

    Returns:
        Path to the changelog file
    """
    if single_file:
        # For single file mode, use same name with .log extension
        return destination.with_suffix(".log")
    else:
        # For hierarchical mode, use main.log in the directory
        return destination / "main.log"
