"""Resolution engine for orchestrating field resolution strategies."""

import logging
from typing import Any, Dict, List, Tuple

from .sync_models import SyncTransaction, SyncResult
from .sync_enums import ChangeType, SyncStatus
from .sync_exceptions import FieldResolutionError
from .field_mapping import FieldMapping
from .field_resolver import FieldResolverFactory

logger = logging.getLogger(__name__)


class ResolutionEngine:
    """Engine for orchestrating field resolution using appropriate strategies."""

    def __init__(self) -> None:
        self.field_mapping = FieldMapping()
        self.resolver_factory = FieldResolverFactory()

    def resolve_transaction(
        self,
        local_data: Dict[str, Any],
        remote_data: Dict[str, Any],
        transaction_id: str,
    ) -> SyncResult:
        """
        Resolve conflicts between local and remote transaction data.

        Args:
            local_data: Local beancount transaction data
            remote_data: Remote PocketSmith transaction data
            transaction_id: ID of the transaction being resolved

        Returns:
            SyncResult with resolution details
        """
        result = SyncResult(transaction_id=transaction_id, status=SyncStatus.SUCCESS)

        try:
            # Create unified transaction object
            transaction = self._create_sync_transaction(
                local_data, remote_data, transaction_id
            )

            # Get all fields that need resolution
            all_fields = set(local_data.keys()) | set(remote_data.keys())

            # Check for unmapped fields
            unmapped_fields = self.field_mapping.validate_field_coverage(all_fields)
            if unmapped_fields:
                for field in unmapped_fields:
                    result.add_warning(
                        f"No resolution strategy defined for field: {field}"
                    )

            # Resolve each field
            resolved_data = {}
            write_back_needed = {}

            for field_name in all_fields:
                if field_name in unmapped_fields:
                    # Skip unmapped fields
                    continue

                try:
                    resolved_value, needs_write_back = self._resolve_field(
                        transaction, field_name, local_data, remote_data
                    )

                    resolved_data[field_name] = resolved_value
                    write_back_needed[field_name] = needs_write_back

                    # Track changes
                    local_value = local_data.get(field_name)
                    remote_value = remote_data.get(field_name)

                    if local_value != resolved_value or remote_value != resolved_value:
                        change_type = self._determine_change_type(
                            local_value, remote_value, resolved_value
                        )
                        strategy = self.field_mapping.get_strategy(field_name)

                        result.add_change(
                            field_name=field_name,
                            old_value=local_value
                            if change_type == ChangeType.LOCAL_ONLY
                            else remote_value,
                            new_value=resolved_value,
                            change_type=change_type,
                            strategy=strategy,
                        )

                except FieldResolutionError as e:
                    result.add_error(f"Failed to resolve field '{field_name}': {e}")
                    result.status = SyncStatus.ERROR
                except Exception as e:
                    result.add_error(
                        f"Unexpected error resolving field '{field_name}': {e}"
                    )
                    result.status = SyncStatus.ERROR

            # Store resolved data and write-back requirements
            result.resolved_data = resolved_data
            result.write_back_needed = write_back_needed

        except Exception as e:
            result.add_error(f"Failed to resolve transaction {transaction_id}: {e}")
            result.status = SyncStatus.ERROR

        return result

    def validate_resolution_completeness(self, all_fields: List[str]) -> List[str]:
        """Validate that all fields have resolution strategies defined."""
        unmapped_fields = []
        for field in all_fields:
            if field not in self.field_mapping.get_all_fields():
                unmapped_fields.append(field)
        return unmapped_fields

    def get_write_back_fields(self, result: SyncResult) -> Dict[str, Any]:
        """Extract fields that need to be written back to remote."""
        write_back_data = {}
        for field_name, needs_write_back in result.write_back_needed.items():
            if needs_write_back:
                if field_name in result.resolved_data:
                    write_back_data[field_name] = result.resolved_data[field_name]
        return write_back_data

    def _create_sync_transaction(
        self,
        local_data: Dict[str, Any],
        remote_data: Dict[str, Any],
        transaction_id: str,
    ) -> SyncTransaction:
        """Create a SyncTransaction from local and remote data."""
        return SyncTransaction(
            id=transaction_id,
            local_data=local_data,
            remote_data=remote_data,
            local_last_modified=local_data.get("last_modified"),
            remote_last_modified=remote_data.get("updated_at"),
            amount=remote_data.get("amount"),
            date=remote_data.get("date"),
            merchant=remote_data.get("merchant"),
            payee=remote_data.get("payee"),
            note=local_data.get("note") or remote_data.get("note"),
            memo=local_data.get("memo") or remote_data.get("memo"),
            category=remote_data.get("category"),
            labels=remote_data.get("labels", []),
            needs_review=remote_data.get("needs_review"),
            closing_balance=remote_data.get("closing_balance"),
            currency_code=remote_data.get("currency_code"),
            transaction_account=remote_data.get("transaction_account"),
        )

    def _resolve_field(
        self,
        transaction: SyncTransaction,
        field_name: str,
        local_data: Dict[str, Any],
        remote_data: Dict[str, Any],
    ) -> Tuple[Any, bool]:
        """
        Resolve a single field using the appropriate strategy.

        Returns:
            Tuple of (resolved_value, needs_write_back)
        """
        strategy = self.field_mapping.get_strategy(field_name)
        resolver = self.resolver_factory.get_resolver(strategy)

        local_value = local_data.get(field_name)
        remote_value = remote_data.get(field_name)

        # Get timestamps for comparison
        local_timestamp = local_data.get("last_modified")
        remote_timestamp = remote_data.get("updated_at")

        # Resolve the field
        resolved_value = resolver.resolve(
            transaction=transaction,
            field_name=field_name,
            local_value=local_value,
            remote_value=remote_value,
            local_timestamp=local_timestamp,
            remote_timestamp=remote_timestamp,
        )

        # Check if write-back is needed
        needs_write_back = resolver.should_write_back(
            transaction=transaction,
            field_name=field_name,
            resolved_value=resolved_value,
            original_remote_value=remote_value,
        )

        return resolved_value, needs_write_back

    def _determine_change_type(
        self, local_value: Any, remote_value: Any, resolved_value: Any
    ) -> ChangeType:
        """Determine the type of change based on values."""
        if local_value == remote_value:
            return ChangeType.NO_CHANGE
        elif resolved_value == local_value:
            return ChangeType.LOCAL_ONLY
        elif resolved_value == remote_value:
            return ChangeType.REMOTE_ONLY
        else:
            return ChangeType.BOTH_CHANGED
