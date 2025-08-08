"""Field resolution strategies for synchronization."""

import logging
from typing import Any, List, Optional, Set

from .sync_interfaces import FieldResolver
from .sync_models import SyncTransaction
from .sync_enums import ResolutionStrategy
from .sync_exceptions import FieldResolutionError

logger = logging.getLogger(__name__)


class Strategy1NeverChange(FieldResolver):
    """Strategy 1: Fields that should never change - warn on conflicts."""

    @property
    def strategy(self) -> ResolutionStrategy:
        return ResolutionStrategy.NEVER_CHANGE

    def resolve(
        self,
        transaction: SyncTransaction,
        field_name: str,
        local_value: Any,
        remote_value: Any,
        local_timestamp: Optional[Any] = None,
        remote_timestamp: Optional[Any] = None,
    ) -> Any:
        """
        Resolve by keeping the original value and warning on conflicts.

        For immutable fields, we expect them to never change. If they do,
        we log a warning and keep the remote value as authoritative.
        """
        if local_value != remote_value:
            logger.warning(
                f"Unexpected change detected in immutable field '{field_name}' "
                f"for transaction {transaction.id}: local='{local_value}' vs remote='{remote_value}'. "
                f"Using remote value as authoritative."
            )

        # Always use remote value as authoritative for immutable fields
        return remote_value

    def should_write_back(
        self,
        transaction: SyncTransaction,
        field_name: str,
        resolved_value: Any,
        original_remote_value: Any,
    ) -> bool:
        """Never write back for immutable fields."""
        return False


class Strategy2LocalChangesOnly(FieldResolver):
    """Strategy 2: Fields that may change locally - write back to remote."""

    @property
    def strategy(self) -> ResolutionStrategy:
        return ResolutionStrategy.LOCAL_CHANGES_ONLY

    def resolve(
        self,
        transaction: SyncTransaction,
        field_name: str,
        local_value: Any,
        remote_value: Any,
        local_timestamp: Optional[Any] = None,
        remote_timestamp: Optional[Any] = None,
    ) -> Any:
        """
        Resolve by using local value and writing back to remote if different.

        This strategy assumes that local changes are intentional and should
        be propagated to the remote system.
        """
        if local_value != remote_value:
            logger.info(
                f"Local change detected in field '{field_name}' for transaction {transaction.id}: "
                f"'{remote_value}' -> '{local_value}'. Will write back to remote."
            )

        # Always use local value
        return local_value

    def should_write_back(
        self,
        transaction: SyncTransaction,
        field_name: str,
        resolved_value: Any,
        original_remote_value: Any,
    ) -> bool:
        """Write back if local value differs from remote."""
        return bool(resolved_value != original_remote_value)


class Strategy3RemoteChangesOnly(FieldResolver):
    """Strategy 3: Fields that may change remotely - overwrite local."""

    @property
    def strategy(self) -> ResolutionStrategy:
        return ResolutionStrategy.REMOTE_CHANGES_ONLY

    def resolve(
        self,
        transaction: SyncTransaction,
        field_name: str,
        local_value: Any,
        remote_value: Any,
        local_timestamp: Optional[Any] = None,
        remote_timestamp: Optional[Any] = None,
    ) -> Any:
        """
        Resolve by using remote value and overwriting local.

        This strategy assumes that remote changes are authoritative
        (e.g., timestamps updated by the server).
        """
        if local_value != remote_value:
            logger.info(
                f"Remote change detected in field '{field_name}' for transaction {transaction.id}: "
                f"'{local_value}' -> '{remote_value}'. Updating local value."
            )

        # Always use remote value
        return remote_value

    def should_write_back(
        self,
        transaction: SyncTransaction,
        field_name: str,
        resolved_value: Any,
        original_remote_value: Any,
    ) -> bool:
        """Never write back for remote-only fields."""
        return False


class Strategy4RemoteWins(FieldResolver):
    """Strategy 4: Fields where remote changes take precedence."""

    @property
    def strategy(self) -> ResolutionStrategy:
        return ResolutionStrategy.REMOTE_WINS

    def resolve(
        self,
        transaction: SyncTransaction,
        field_name: str,
        local_value: Any,
        remote_value: Any,
        local_timestamp: Optional[Any] = None,
        remote_timestamp: Optional[Any] = None,
    ) -> Any:
        """
        Resolve by preferring remote value over local changes.

        This strategy is used for fields where the remote system is
        considered the authoritative source (e.g., categories).
        """
        if local_value != remote_value:
            logger.info(
                f"Conflict in field '{field_name}' for transaction {transaction.id}: "
                f"local='{local_value}' vs remote='{remote_value}'. Using remote value."
            )

        # Always use remote value
        return remote_value

    def should_write_back(
        self,
        transaction: SyncTransaction,
        field_name: str,
        resolved_value: Any,
        original_remote_value: Any,
    ) -> bool:
        """Never write back since remote always wins."""
        return False


class Strategy5MergeLists(FieldResolver):
    """Strategy 5: Merge list fields and deduplicate."""

    @property
    def strategy(self) -> ResolutionStrategy:
        return ResolutionStrategy.MERGE_LISTS

    def resolve(
        self,
        transaction: SyncTransaction,
        field_name: str,
        local_value: Any,
        remote_value: Any,
        local_timestamp: Optional[Any] = None,
        remote_timestamp: Optional[Any] = None,
    ) -> List[Any]:
        """
        Resolve by merging lists and removing duplicates.

        This strategy combines local and remote list values,
        preserving unique items from both sources.
        """
        # Ensure we're working with lists
        local_list = self._ensure_list(local_value)
        remote_list = self._ensure_list(remote_value)

        # Merge and deduplicate while preserving order
        merged = []
        seen = set()

        # Add local items first
        for item in local_list:
            if item not in seen:
                merged.append(item)
                seen.add(item)

        # Add remote items that aren't already present
        for item in remote_list:
            if item not in seen:
                merged.append(item)
                seen.add(item)

        if merged != local_list or merged != remote_list:
            logger.info(
                f"Merged list field '{field_name}' for transaction {transaction.id}: "
                f"local={local_list}, remote={remote_list} -> merged={merged}"
            )

        return merged

    def should_write_back(
        self,
        transaction: SyncTransaction,
        field_name: str,
        resolved_value: Any,
        original_remote_value: Any,
    ) -> bool:
        """Write back if merged list differs from original remote list."""
        original_list = self._ensure_list(original_remote_value)
        resolved_list = self._ensure_list(resolved_value)
        return resolved_list != original_list

    def _ensure_list(self, value: Any) -> List[Any]:
        """Ensure value is a list."""
        if value is None:
            return []
        elif isinstance(value, list):
            return value
        elif isinstance(value, (tuple, set)):
            return list(value)
        else:
            return [value]


class FieldResolverFactory:
    """Factory for creating field resolver instances."""

    _resolvers = {
        ResolutionStrategy.NEVER_CHANGE: Strategy1NeverChange(),
        ResolutionStrategy.LOCAL_CHANGES_ONLY: Strategy2LocalChangesOnly(),
        ResolutionStrategy.REMOTE_CHANGES_ONLY: Strategy3RemoteChangesOnly(),
        ResolutionStrategy.REMOTE_WINS: Strategy4RemoteWins(),
        ResolutionStrategy.MERGE_LISTS: Strategy5MergeLists(),
    }

    @classmethod
    def get_resolver(cls, strategy: ResolutionStrategy) -> FieldResolver:
        """
        Get a resolver instance for the specified strategy.

        Args:
            strategy: The resolution strategy

        Returns:
            FieldResolver instance

        Raises:
            FieldResolutionError: If strategy is not supported
        """
        if strategy not in cls._resolvers:
            raise FieldResolutionError(
                f"Unsupported resolution strategy: {strategy}",
                field_name="unknown",
                strategy=str(strategy),
            )

        return cls._resolvers[strategy]

    @classmethod
    def get_all_strategies(cls) -> Set[ResolutionStrategy]:
        """Get all supported resolution strategies."""
        return set(cls._resolvers.keys())
