"""Core comparison logic for transactions."""

from typing import List, Any, Tuple
import logging

from .model import Transaction, TransactionComparison, FieldChange, ChangeType

logger = logging.getLogger(__name__)


def compare_transactions(
    local_transaction: Transaction,
    remote_transaction: Transaction,
) -> TransactionComparison:
    """Compare two transactions and detect changes."""
    changes = detect_changes(local_transaction, remote_transaction)

    return TransactionComparison(
        transaction_id=local_transaction.id,
        local_transaction=local_transaction,
        remote_transaction=remote_transaction,
        changes=changes,
    )


def detect_changes(
    local_transaction: Transaction,
    remote_transaction: Transaction,
) -> List[FieldChange]:
    """Detect changes between two transactions."""
    changes = []

    # Convert transactions to dictionaries for comparison
    local_data = local_transaction.to_dict()
    remote_data = remote_transaction.to_dict()

    # Get all fields from both transactions
    all_fields = set(local_data.keys()) | set(remote_data.keys())

    for field_name in all_fields:
        local_value = local_data.get(field_name)
        remote_value = remote_data.get(field_name)

        change_type = _determine_change_type(
            field_name, local_value, remote_value, local_transaction, remote_transaction
        )

        if change_type != ChangeType.NO_CHANGE:
            change = FieldChange(
                field_name=field_name,
                old_value=local_value,
                new_value=remote_value,
                change_type=change_type,
            )
            changes.append(change)

    return changes


def match_transactions_by_id(
    local_transactions: List[Transaction],
    remote_transactions: List[Transaction],
) -> Tuple[List[Tuple[Transaction, Transaction]], List[Transaction], List[Transaction]]:
    """Match transactions by ID and identify unmatched ones."""

    # Create lookup dictionaries that handle duplicates
    from collections import defaultdict

    local_by_id = defaultdict(list)
    remote_by_id = defaultdict(list)

    for tx in local_transactions:
        local_by_id[tx.id].append(tx)
    for tx in remote_transactions:
        remote_by_id[tx.id].append(tx)

    # Find matches and unmatched
    matched_pairs = []
    local_only = []
    remote_only = []

    # Find matched transactions
    all_ids = set(local_by_id.keys()) | set(remote_by_id.keys())
    for tx_id in all_ids:
        local_txs = local_by_id.get(tx_id, [])
        remote_txs = remote_by_id.get(tx_id, [])

        if local_txs and remote_txs:
            # Match pairs (match first local with first remote, etc.)
            min_matches = min(len(local_txs), len(remote_txs))
            for i in range(min_matches):
                matched_pairs.append((local_txs[i], remote_txs[i]))

            # Add remaining unmatched transactions
            local_only.extend(local_txs[min_matches:])
            remote_only.extend(remote_txs[min_matches:])
        elif local_txs:
            # Only local transactions with this ID
            local_only.extend(local_txs)
        elif remote_txs:
            # Only remote transactions with this ID
            remote_only.extend(remote_txs)

    logger.info(
        f"Transaction matching: {len(matched_pairs)} matched, "
        f"{len(local_only)} local-only, {len(remote_only)} remote-only"
    )

    return matched_pairs, local_only, remote_only


def compare_transaction_lists(
    local_transactions: List[Transaction],
    remote_transactions: List[Transaction],
) -> List[TransactionComparison]:
    """Compare two lists of transactions and return comparison results."""

    matched_pairs, local_only, remote_only = match_transactions_by_id(
        local_transactions, remote_transactions
    )

    comparisons = []

    # Compare matched transactions
    for local_tx, remote_tx in matched_pairs:
        comparison = compare_transactions(local_tx, remote_tx)
        comparisons.append(comparison)

    # Handle local-only transactions
    for local_tx in local_only:
        comparison = TransactionComparison(
            transaction_id=local_tx.id,
            local_transaction=local_tx,
            remote_transaction=None,
            changes=[
                FieldChange(
                    field_name="_status",
                    old_value="exists",
                    new_value="missing_remote",
                    change_type=ChangeType.LOCAL_ONLY,
                )
            ],
        )
        comparisons.append(comparison)

    # Handle remote-only transactions
    for remote_tx in remote_only:
        comparison = TransactionComparison(
            transaction_id=remote_tx.id,
            local_transaction=None,
            remote_transaction=remote_tx,
            changes=[
                FieldChange(
                    field_name="_status",
                    old_value="missing_local",
                    new_value="exists",
                    change_type=ChangeType.REMOTE_ONLY,
                )
            ],
        )
        comparisons.append(comparison)

    return comparisons


def _determine_change_type(
    field_name: str,
    local_value: Any,
    remote_value: Any,
    local_transaction: Transaction,
    remote_transaction: Transaction,
) -> ChangeType:
    """Determine the type of change for a specific field."""

    # Normalize values for comparison
    local_normalized = _normalize_value(field_name, local_value)
    remote_normalized = _normalize_value(field_name, remote_value)

    # If values are the same, no change
    if _values_equal(local_normalized, remote_normalized):
        return ChangeType.NO_CHANGE

    # For timestamp fields, always consider remote as source of truth
    if field_name in ["created_at", "updated_at", "last_modified"]:
        return ChangeType.REMOTE_ONLY

    # For immutable fields, any difference is unexpected
    if field_name in ["id", "amount", "date", "currency_code"]:
        logger.warning(f"Unexpected change in immutable field '{field_name}'")
        return ChangeType.REMOTE_ONLY  # Trust remote for immutable fields

    # Use timestamps to determine change direction if available
    local_updated = local_transaction.updated_at
    remote_updated = remote_transaction.updated_at

    if local_updated and remote_updated:
        if local_updated > remote_updated:
            return ChangeType.LOCAL_ONLY
        elif remote_updated > local_updated:
            return ChangeType.REMOTE_ONLY
        else:
            # Same timestamp but different values - both changed
            return ChangeType.BOTH_CHANGED

    # Without timestamp information, we can't determine direction
    return ChangeType.BOTH_CHANGED


def _normalize_value(field_name: str, value: Any) -> Any:
    """Normalize a value for comparison."""
    if value is None:
        return None

    # Handle list fields
    if field_name in ["labels", "tags"]:
        if isinstance(value, (list, tuple)):
            # Sort lists for consistent comparison
            return sorted(list(value))
        elif value:
            return [value]
        else:
            return []

    # Handle string fields - strip whitespace
    if isinstance(value, str):
        return value.strip()

    return value


def _values_equal(value1: Any, value2: Any) -> bool:
    """Check if two normalized values are equal."""
    # Handle None values
    if value1 is None and value2 is None:
        return True
    if value1 is None or value2 is None:
        return False

    # Handle list comparison
    if isinstance(value1, list) and isinstance(value2, list):
        return value1 == value2

    # Default comparison
    return bool(value1 == value2)
