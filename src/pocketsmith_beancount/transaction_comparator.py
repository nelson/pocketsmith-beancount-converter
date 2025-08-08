"""Transaction comparison and change detection logic."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal, InvalidOperation

from .sync_interfaces import TransactionComparator
from .sync_models import FieldChange
from .sync_enums import ChangeType
from .sync_exceptions import TransactionComparisonError
from .field_mapping import FieldMapping

logger = logging.getLogger(__name__)


class PocketSmithTransactionComparator(TransactionComparator):
    """Implementation of transaction comparison for PocketSmith data."""

    def __init__(self, field_mapping: Optional[FieldMapping] = None) -> None:
        self.field_mapping = field_mapping or FieldMapping()

    def compare_transactions(
        self, local_transaction: Dict[str, Any], remote_transaction: Dict[str, Any]
    ) -> List[FieldChange]:
        """
        Compare local and remote transactions and detect changes.

        Args:
            local_transaction: Local beancount transaction data
            remote_transaction: Remote PocketSmith transaction data

        Returns:
            List of detected field changes
        """
        changes = []

        # Get all fields from both transactions
        all_fields = set(local_transaction.keys()) | set(remote_transaction.keys())

        # Get timestamps for change detection
        local_timestamp = self._parse_timestamp(local_transaction.get("last_modified"))
        remote_timestamp = self._parse_timestamp(remote_transaction.get("updated_at"))

        for field_name in all_fields:
            try:
                # Skip unmapped fields
                if field_name not in self.field_mapping.get_all_fields():
                    continue

                local_value = local_transaction.get(field_name)
                remote_value = remote_transaction.get(field_name)

                # Detect change type
                change_type = self.detect_change_type(
                    field_name,
                    local_value,
                    remote_value,
                    local_timestamp,
                    remote_timestamp,
                )

                # Only create FieldChange if there's actually a change
                if change_type != ChangeType.NO_CHANGE:
                    strategy = self.field_mapping.get_strategy(field_name)

                    change = FieldChange(
                        field_name=field_name,
                        old_value=local_value
                        if change_type == ChangeType.LOCAL_ONLY
                        else remote_value,
                        new_value=remote_value
                        if change_type == ChangeType.REMOTE_ONLY
                        else local_value,
                        change_type=change_type,
                        strategy=strategy,
                    )
                    changes.append(change)

                    logger.debug(
                        f"Detected {change_type.name} change in field '{field_name}': "
                        f"local='{local_value}' vs remote='{remote_value}'"
                    )

            except Exception as e:
                logger.error(f"Error comparing field '{field_name}': {e}")
                raise TransactionComparisonError(
                    f"Failed to compare field '{field_name}': {e}",
                    local_id=local_transaction.get("id"),
                    remote_id=remote_transaction.get("id"),
                )

        return changes

    def detect_change_type(
        self,
        field_name: str,
        local_value: Any,
        remote_value: Any,
        local_timestamp: Optional[datetime] = None,
        remote_timestamp: Optional[datetime] = None,
    ) -> ChangeType:
        """
        Determine the type of change for a specific field.

        Args:
            field_name: Name of the field
            local_value: Local field value
            remote_value: Remote field value
            local_timestamp: Local modification timestamp
            remote_timestamp: Remote modification timestamp

        Returns:
            Type of change detected
        """
        # Normalize values for comparison
        local_normalized = self._normalize_value(field_name, local_value)
        remote_normalized = self._normalize_value(field_name, remote_value)

        # If values are the same, no change
        if self._values_equal(local_normalized, remote_normalized):
            return ChangeType.NO_CHANGE

        # For timestamp fields, always consider remote as source of truth
        if self.field_mapping.is_timestamp_field(field_name):
            return ChangeType.REMOTE_ONLY

        # For immutable fields, any difference is unexpected
        if self.field_mapping.is_immutable(field_name):
            logger.warning(f"Unexpected change in immutable field '{field_name}'")
            return ChangeType.REMOTE_ONLY  # Trust remote for immutable fields

        # Use timestamps to determine change direction if available
        if local_timestamp and remote_timestamp:
            if local_timestamp > remote_timestamp:
                return ChangeType.LOCAL_ONLY
            elif remote_timestamp > local_timestamp:
                return ChangeType.REMOTE_ONLY
            else:
                # Same timestamp but different values - both changed
                return ChangeType.BOTH_CHANGED

        # Without timestamp information, we can't determine direction
        # Default to both changed to be safe
        return ChangeType.BOTH_CHANGED

    def match_transactions_by_id(
        self,
        local_transactions: List[Dict[str, Any]],
        remote_transactions: List[Dict[str, Any]],
    ) -> Tuple[
        List[Tuple[Dict[str, Any], Dict[str, Any]]],
        List[Dict[str, Any]],
        List[Dict[str, Any]],
    ]:
        """
        Match transactions by ID and identify orphaned transactions.

        Args:
            local_transactions: List of local transaction data
            remote_transactions: List of remote transaction data

        Returns:
            Tuple of (matched_pairs, local_only, remote_only)
        """
        # Create lookup dictionaries
        local_by_id = {}
        remote_by_id = {}

        for local_tx in local_transactions:
            tx_id = self._extract_transaction_id(local_tx)
            if tx_id:
                local_by_id[tx_id] = local_tx

        for remote_tx in remote_transactions:
            tx_id = self._extract_transaction_id(remote_tx)
            if tx_id:
                remote_by_id[tx_id] = remote_tx

        # Find matches and orphans
        matched_pairs = []
        local_only = []
        remote_only = []

        # Find matched transactions
        for tx_id in set(local_by_id.keys()) & set(remote_by_id.keys()):
            matched_pairs.append((local_by_id[tx_id], remote_by_id[tx_id]))

        # Find local-only transactions
        for tx_id in set(local_by_id.keys()) - set(remote_by_id.keys()):
            local_only.append(local_by_id[tx_id])

        # Find remote-only transactions
        for tx_id in set(remote_by_id.keys()) - set(local_by_id.keys()):
            remote_only.append(remote_by_id[tx_id])

        logger.info(
            f"Transaction matching: {len(matched_pairs)} matched, "
            f"{len(local_only)} local-only, {len(remote_only)} remote-only"
        )

        return matched_pairs, local_only, remote_only

    def _extract_transaction_id(self, transaction: Dict[str, Any]) -> Optional[str]:
        """Extract transaction ID from transaction data."""
        # Try different possible ID field names
        for id_field in ["id", "transaction_id", "pocketsmith_id"]:
            if id_field in transaction:
                tx_id = transaction[id_field]
                if tx_id is not None:
                    return str(tx_id)

        logger.warning(f"No transaction ID found in transaction: {transaction}")
        return None

    def _normalize_value(self, field_name: str, value: Any) -> Any:
        """Normalize a value for comparison."""
        if value is None:
            return None

        # Handle list fields
        if self.field_mapping.is_list_field(field_name):
            if isinstance(value, (list, tuple)):
                # Sort lists for consistent comparison
                return sorted(list(value))
            elif value:
                return [value]
            else:
                return []

        # Handle decimal/numeric fields
        if field_name in ["amount", "closing_balance"]:
            if isinstance(value, (int, float, str)):
                try:
                    return Decimal(str(value))
                except (ValueError, TypeError, InvalidOperation):
                    return value

        # Handle string fields - strip whitespace
        if isinstance(value, str):
            return value.strip()

        return value

    def _values_equal(self, value1: Any, value2: Any) -> bool:
        """Check if two normalized values are equal."""
        # Handle None values
        if value1 is None and value2 is None:
            return True
        if value1 is None or value2 is None:
            return False

        # Handle list comparison
        if isinstance(value1, list) and isinstance(value2, list):
            return value1 == value2

        # Handle decimal comparison
        if isinstance(value1, Decimal) and isinstance(value2, Decimal):
            return value1 == value2

        # Handle string comparison (case-insensitive for some fields)
        if isinstance(value1, str) and isinstance(value2, str):
            return value1 == value2

        # Default comparison
        return bool(value1 == value2)

    def _parse_timestamp(self, timestamp_value: Any) -> Optional[datetime]:
        """Parse timestamp value into datetime object."""
        if timestamp_value is None:
            return None

        if isinstance(timestamp_value, datetime):
            return timestamp_value

        if isinstance(timestamp_value, str):
            try:
                # Try ISO format first
                if timestamp_value.endswith("Z"):
                    timestamp_value = timestamp_value[:-1] + "+00:00"
                return datetime.fromisoformat(timestamp_value)
            except ValueError:
                try:
                    # Try other common formats
                    return datetime.strptime(timestamp_value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    logger.warning(f"Could not parse timestamp: {timestamp_value}")
                    return None

        return None

    def detect_significant_changes(
        self, changes: List[FieldChange]
    ) -> List[FieldChange]:
        """
        Filter changes to only include significant ones.

        Args:
            changes: List of all detected changes

        Returns:
            List of significant changes only
        """
        significant_changes = []

        for change in changes:
            # Always consider changes to writable fields as significant
            if self.field_mapping.is_writable(change.field_name):
                significant_changes.append(change)
                continue

            # Consider changes to immutable fields as significant (warnings)
            if self.field_mapping.is_immutable(change.field_name):
                significant_changes.append(change)
                continue

            # Consider timestamp changes as significant for tracking
            if self.field_mapping.is_timestamp_field(change.field_name):
                significant_changes.append(change)
                continue

            # For other fields, check if the change is substantial
            if self._is_substantial_change(change):
                significant_changes.append(change)

        return significant_changes

    def _is_substantial_change(self, change: FieldChange) -> bool:
        """Determine if a change is substantial enough to care about."""
        # For string fields, ignore trivial whitespace changes
        if isinstance(change.old_value, str) and isinstance(change.new_value, str):
            if change.old_value.strip() == change.new_value.strip():
                return False

        # For numeric fields, ignore very small differences (rounding errors)
        if isinstance(change.old_value, (int, float, Decimal)) and isinstance(
            change.new_value, (int, float, Decimal)
        ):
            try:
                old_decimal = Decimal(str(change.old_value))
                new_decimal = Decimal(str(change.new_value))
                diff = abs(old_decimal - new_decimal)
                # Ignore differences smaller than 0.01
                if diff < Decimal("0.01"):
                    return False
            except (ValueError, TypeError):
                pass

        return True
