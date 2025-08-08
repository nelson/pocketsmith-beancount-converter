"""Field mapping configuration for synchronization strategies."""

from typing import Dict, Set
from .sync_enums import ResolutionStrategy


class FieldMapping:
    """Configuration mapping each field to its resolution strategy."""

    # Field to strategy mapping based on requirements
    FIELD_STRATEGIES: Dict[str, ResolutionStrategy] = {
        # Strategy 1: Never Change - warn on conflicts, keep original
        "amount": ResolutionStrategy.NEVER_CHANGE,
        "merchant": ResolutionStrategy.NEVER_CHANGE,
        "payee": ResolutionStrategy.NEVER_CHANGE,
        "date": ResolutionStrategy.NEVER_CHANGE,
        "closing_balance": ResolutionStrategy.NEVER_CHANGE,
        "currency_code": ResolutionStrategy.NEVER_CHANGE,
        "transaction_account": ResolutionStrategy.NEVER_CHANGE,
        "id": ResolutionStrategy.NEVER_CHANGE,
        # Strategy 2: Local Changes Only - write local changes to remote
        "note": ResolutionStrategy.LOCAL_CHANGES_ONLY,
        "memo": ResolutionStrategy.LOCAL_CHANGES_ONLY,
        # Strategy 3: Remote Changes Only - overwrite local with remote
        "updated_at": ResolutionStrategy.REMOTE_CHANGES_ONLY,
        "created_at": ResolutionStrategy.REMOTE_CHANGES_ONLY,
        "last_modified": ResolutionStrategy.REMOTE_CHANGES_ONLY,
        # Strategy 4: Remote Wins - remote takes precedence
        "category": ResolutionStrategy.REMOTE_WINS,
        "needs_review": ResolutionStrategy.REMOTE_WINS,
        # Strategy 5: Merge Lists - merge and deduplicate lists
        "labels": ResolutionStrategy.MERGE_LISTS,
        "tags": ResolutionStrategy.MERGE_LISTS,
    }

    # Fields that are considered immutable (should never change)
    IMMUTABLE_FIELDS: Set[str] = {
        "id",
        "amount",
        "date",
        "currency_code",
        "transaction_account",
    }

    # Fields that can be written back to remote API
    WRITABLE_FIELDS: Set[str] = {"note", "memo", "labels", "tags"}

    # Fields that are lists and need special handling
    LIST_FIELDS: Set[str] = {"labels", "tags"}

    # Fields that are timestamps
    TIMESTAMP_FIELDS: Set[str] = {"updated_at", "created_at", "last_modified"}

    @classmethod
    def get_strategy(cls, field_name: str) -> ResolutionStrategy:
        """
        Get the resolution strategy for a field.

        Args:
            field_name: Name of the field

        Returns:
            Resolution strategy for the field

        Raises:
            ValueError: If field is not mapped to a strategy
        """
        if field_name not in cls.FIELD_STRATEGIES:
            raise ValueError(f"No resolution strategy defined for field: {field_name}")

        return cls.FIELD_STRATEGIES[field_name]

    @classmethod
    def is_immutable(cls, field_name: str) -> bool:
        """Check if a field is considered immutable."""
        return field_name in cls.IMMUTABLE_FIELDS

    @classmethod
    def is_writable(cls, field_name: str) -> bool:
        """Check if a field can be written back to remote API."""
        return field_name in cls.WRITABLE_FIELDS

    @classmethod
    def is_list_field(cls, field_name: str) -> bool:
        """Check if a field contains list data."""
        return field_name in cls.LIST_FIELDS

    @classmethod
    def is_timestamp_field(cls, field_name: str) -> bool:
        """Check if a field contains timestamp data."""
        return field_name in cls.TIMESTAMP_FIELDS

    @classmethod
    def get_all_fields(cls) -> Set[str]:
        """Get all mapped field names."""
        return set(cls.FIELD_STRATEGIES.keys())

    @classmethod
    def get_fields_by_strategy(cls, strategy: ResolutionStrategy) -> Set[str]:
        """Get all fields that use a specific resolution strategy."""
        return {
            field
            for field, field_strategy in cls.FIELD_STRATEGIES.items()
            if field_strategy == strategy
        }

    @classmethod
    def validate_field_coverage(cls, transaction_fields: Set[str]) -> Set[str]:
        """
        Validate that all transaction fields have resolution strategies.

        Args:
            transaction_fields: Set of field names from a transaction

        Returns:
            Set of unmapped field names
        """
        mapped_fields = set(cls.FIELD_STRATEGIES.keys())
        return transaction_fields - mapped_fields
