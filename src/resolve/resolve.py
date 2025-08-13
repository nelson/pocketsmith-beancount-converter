"""Resolution engine for orchestrating field resolution strategies."""

import logging
from typing import Dict, Any, Tuple, Set, List, Optional
from dataclasses import dataclass, field

from ..compare.model import Transaction
from .strategy import ResolutionStrategyType, get_strategy

logger = logging.getLogger(__name__)


@dataclass
class ResolutionResult:
    """Result of resolving conflicts in a transaction."""

    transaction_id: str
    resolved_transaction: Transaction
    write_back_needed: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)

    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)

    @property
    def has_write_backs(self) -> bool:
        """Check if any fields need to be written back."""
        return len(self.write_back_needed) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0


class FieldMappingConfig:
    """Configuration mapping fields to resolution strategies."""

    # Field to strategy mapping based on requirements
    FIELD_STRATEGIES: Dict[str, ResolutionStrategyType] = {
        # Strategy 1: Never Change - warn on conflicts, keep original
        "id": ResolutionStrategyType.NEVER_CHANGE,
        "amount": ResolutionStrategyType.NEVER_CHANGE,
        "date": ResolutionStrategyType.NEVER_CHANGE,
        "currency_code": ResolutionStrategyType.NEVER_CHANGE,
        "account": ResolutionStrategyType.NEVER_CHANGE,
        "merchant": ResolutionStrategyType.NEVER_CHANGE,
        "payee": ResolutionStrategyType.NEVER_CHANGE,
        "closing_balance": ResolutionStrategyType.NEVER_CHANGE,
        # Strategy 2: Local Changes Only - write local changes to remote
        "note": ResolutionStrategyType.LOCAL_CHANGES_ONLY,
        "memo": ResolutionStrategyType.LOCAL_CHANGES_ONLY,
        # Strategy 3: Remote Changes Only - overwrite local with remote
        "created_at": ResolutionStrategyType.REMOTE_CHANGES_ONLY,
        "updated_at": ResolutionStrategyType.REMOTE_CHANGES_ONLY,
        "last_modified": ResolutionStrategyType.REMOTE_CHANGES_ONLY,
        # Strategy 4: Remote Wins - remote takes precedence
        "category": ResolutionStrategyType.REMOTE_WINS,
        "needs_review": ResolutionStrategyType.REMOTE_WINS,
        # Strategy 5: Merge Lists - merge and deduplicate lists
        "labels": ResolutionStrategyType.MERGE_LISTS,
        "tags": ResolutionStrategyType.MERGE_LISTS,
    }

    # Fields that can be written back to remote API
    WRITABLE_FIELDS: Set[str] = {"note", "memo", "labels", "tags"}

    @classmethod
    def get_strategy_for_field(cls, field_name: str) -> ResolutionStrategyType:
        """Get the resolution strategy for a field."""
        if field_name not in cls.FIELD_STRATEGIES:
            logger.warning(f"No resolution strategy defined for field: {field_name}")
            # Default to remote wins for undefined fields
            return ResolutionStrategyType.REMOTE_WINS

        return cls.FIELD_STRATEGIES[field_name]

    @classmethod
    def is_writable_field(cls, field_name: str) -> bool:
        """Check if a field can be written back to remote."""
        return field_name in cls.WRITABLE_FIELDS

    @classmethod
    def get_all_mapped_fields(cls) -> Set[str]:
        """Get all mapped field names."""
        return set(cls.FIELD_STRATEGIES.keys())


class ResolutionEngine:
    """Engine for orchestrating field resolution using appropriate strategies."""

    def __init__(self, field_mapping: Optional[FieldMappingConfig] = None):
        self.field_mapping = field_mapping or FieldMappingConfig()

    def resolve_transaction(
        self,
        local_transaction: Transaction,
        remote_transaction: Transaction,
    ) -> ResolutionResult:
        """Resolve conflicts between local and remote transaction data."""
        result = ResolutionResult(
            transaction_id=local_transaction.id,
            resolved_transaction=local_transaction,  # Start with local
        )

        try:
            # Convert transactions to dictionaries for processing
            local_data = local_transaction.to_dict()
            remote_data = remote_transaction.to_dict()
            resolved_data = local_data.copy()

            # Get all fields from both transactions
            all_fields = set(local_data.keys()) | set(remote_data.keys())

            # Process each field
            for field_name in all_fields:
                try:
                    local_value = local_data.get(field_name)
                    remote_value = remote_data.get(field_name)

                    # Skip if values are identical
                    if local_value == remote_value:
                        continue

                    # Resolve the field
                    resolved_value, needs_write_back = self._resolve_field(
                        field_name,
                        local_value,
                        remote_value,
                        local_transaction,
                        remote_transaction,
                    )

                    # Update resolved data
                    resolved_data[field_name] = resolved_value

                    # Track write-back requirements
                    if needs_write_back and self.field_mapping.is_writable_field(
                        field_name
                    ):
                        result.write_back_needed[field_name] = resolved_value

                except Exception as e:
                    error_msg = f"Failed to resolve field '{field_name}': {e}"
                    result.add_error(error_msg)
                    logger.error(error_msg)

            # Create resolved transaction
            result.resolved_transaction = Transaction.from_dict(resolved_data)

        except Exception as e:
            error_msg = f"Failed to resolve transaction {local_transaction.id}: {e}"
            result.add_error(error_msg)
            logger.error(error_msg)

        return result

    def _resolve_field(
        self,
        field_name: str,
        local_value: Any,
        remote_value: Any,
        local_transaction: Transaction,
        remote_transaction: Transaction,
    ) -> Tuple[Any, bool]:
        """Resolve a single field using the appropriate strategy."""
        strategy_type = self.field_mapping.get_strategy_for_field(field_name)
        strategy = get_strategy(strategy_type)

        # Get timestamps for comparison
        local_timestamp = local_transaction.updated_at
        remote_timestamp = remote_transaction.updated_at

        # Resolve the field
        resolved_value = strategy.resolve(
            field_name=field_name,
            local_value=local_value,
            remote_value=remote_value,
            local_timestamp=local_timestamp,
            remote_timestamp=remote_timestamp,
        )

        # Check if write-back is needed
        needs_write_back = strategy.should_write_back(
            field_name=field_name,
            resolved_value=resolved_value,
            original_remote_value=remote_value,
        )

        return resolved_value, needs_write_back


def resolve_transaction(
    local_transaction: Transaction,
    remote_transaction: Transaction,
) -> ResolutionResult:
    """Convenience function to resolve a transaction using default settings."""
    engine = ResolutionEngine()
    return engine.resolve_transaction(local_transaction, remote_transaction)


def resolve_field(
    field_name: str,
    local_value: Any,
    remote_value: Any,
    strategy_type: Optional[ResolutionStrategyType] = None,
) -> Tuple[Any, bool]:
    """Convenience function to resolve a single field."""
    if strategy_type is None:
        strategy_type = FieldMappingConfig.get_strategy_for_field(field_name)

    strategy = get_strategy(strategy_type)

    resolved_value = strategy.resolve(
        field_name=field_name,
        local_value=local_value,
        remote_value=remote_value,
    )

    needs_write_back = strategy.should_write_back(
        field_name=field_name,
        resolved_value=resolved_value,
        original_remote_value=remote_value,
    )

    return resolved_value, needs_write_back
