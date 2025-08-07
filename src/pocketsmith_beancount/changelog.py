from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import pytz


class TransactionChangelog:
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir or "./output")
        self.changelog_file = self.output_dir / "changelog.txt"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_aest_timestamp(self) -> str:
        """Get current timestamp in AEST with millisecond precision."""
        aest_tz = pytz.timezone("Australia/Sydney")
        now = datetime.now(aest_tz)
        return now.strftime("%b %d %H:%M:%S.%f")[
            :-3
        ]  # Remove last 3 digits for milliseconds

    def _format_changelog_entry(
        self,
        operation: str,
        transaction_id: str,
        field_changes: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Format a single changelog entry in compact format."""
        timestamp = self._get_aest_timestamp()

        if operation == "CREATE":
            return f"{timestamp} CREATE {transaction_id}"
        elif operation == "DELETE":
            return f"{timestamp} DELETE {transaction_id}"
        elif operation == "MODIFY" and field_changes:
            # Format field changes as "field: old_value -> new_value"
            changes = []
            for field, (old_value, new_value) in field_changes.items():
                # Handle special formatting for different field types
                if field == "tags":
                    old_str = (
                        "[]"
                        if not old_value
                        else " ".join(f"#{tag}" for tag in old_value)
                    )
                    new_str = (
                        "[]"
                        if not new_value
                        else " ".join(f"#{tag}" for tag in new_value)
                    )
                    changes.append(f"{field}: {old_str} -> {new_str}")
                elif field == "amount":
                    changes.append(f"{field}: {old_value} -> {new_value}")
                else:
                    changes.append(f"{field}: {old_value} -> {new_value}")

            change_str = ", ".join(changes)
            return f"{timestamp} MODIFY {transaction_id} {change_str}"
        else:
            return f"{timestamp} {operation} {transaction_id}"

    def log_transaction_create(self, transaction: Dict[str, Any]) -> None:
        """Log creation of a new transaction."""
        transaction_id = transaction.get("id", "unknown")
        entry = self._format_changelog_entry("CREATE", str(transaction_id))
        self._append_to_changelog(entry)

    def log_transaction_delete(self, transaction_id: str) -> None:
        """Log deletion of a transaction."""
        entry = self._format_changelog_entry("DELETE", transaction_id)
        self._append_to_changelog(entry)

    def log_transaction_modify(
        self, transaction_id: str, field_changes: Dict[str, tuple[Any, Any]]
    ) -> None:
        """Log modification of a transaction with field-level changes."""
        entry = self._format_changelog_entry("MODIFY", transaction_id, field_changes)
        self._append_to_changelog(entry)

    def _append_to_changelog(self, entry: str) -> None:
        """Append an entry to the changelog file."""
        with open(self.changelog_file, "a", encoding="utf-8") as f:
            f.write(entry + "\n")

    def get_changelog_path(self) -> str:
        """Get the path to the changelog file."""
        return str(self.changelog_file)

    def compare_transactions(
        self,
        old_transactions: List[Dict[str, Any]],
        new_transactions: List[Dict[str, Any]],
    ) -> None:
        """Compare two sets of transactions and log changes."""
        # Create lookup dictionaries by transaction ID
        old_by_id = {str(t.get("id")): t for t in old_transactions if t.get("id")}
        new_by_id = {str(t.get("id")): t for t in new_transactions if t.get("id")}

        # Find created transactions
        for transaction_id, transaction in new_by_id.items():
            if transaction_id not in old_by_id:
                self.log_transaction_create(transaction)

        # Find deleted transactions
        for transaction_id in old_by_id:
            if transaction_id not in new_by_id:
                self.log_transaction_delete(transaction_id)

        # Find modified transactions
        for transaction_id, new_transaction in new_by_id.items():
            if transaction_id in old_by_id:
                old_transaction = old_by_id[transaction_id]
                changes = self._detect_changes(old_transaction, new_transaction)
                if changes:
                    self.log_transaction_modify(transaction_id, changes)

    def _detect_changes(
        self, old_transaction: Dict[str, Any], new_transaction: Dict[str, Any]
    ) -> Dict[str, tuple[Any, Any]]:
        """Detect changes between two transaction objects."""
        changes = {}

        # Fields to monitor for changes
        monitored_fields = [
            "amount",
            "merchant",
            "payee",
            "note",
            "memo",
            "labels",
            "needs_review",
            "category",
        ]

        for field in monitored_fields:
            old_value = old_transaction.get(field)
            new_value = new_transaction.get(field)

            # Special handling for different field types
            if field == "labels":
                # Compare lists
                old_labels = old_value or []
                new_labels = new_value or []
                if set(old_labels) != set(new_labels):
                    changes[field] = (old_labels, new_labels)
            elif field == "category":
                # Compare category objects by ID
                old_cat_id = old_value.get("id") if old_value else None
                new_cat_id = new_value.get("id") if new_value else None
                if old_cat_id != new_cat_id:
                    old_cat_name = old_value.get("title") if old_value else "None"
                    new_cat_name = new_value.get("title") if new_value else "None"
                    changes[field] = (old_cat_name, new_cat_name)
            else:
                # Direct comparison for other fields
                if old_value != new_value:
                    changes[field] = (old_value, new_value)

        return changes
