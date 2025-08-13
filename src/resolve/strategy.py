"""Resolution strategies for handling field conflicts."""

import logging
from abc import ABC, abstractmethod
from typing import Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ResolutionStrategyType(Enum):
    """Types of resolution strategies."""

    NEVER_CHANGE = "never_change"
    LOCAL_CHANGES_ONLY = "local_changes_only"
    REMOTE_CHANGES_ONLY = "remote_changes_only"
    REMOTE_WINS = "remote_wins"
    MERGE_LISTS = "merge_lists"


class ResolutionStrategy(ABC):
    """Base class for field resolution strategies."""

    @property
    @abstractmethod
    def strategy_type(self) -> ResolutionStrategyType:
        """Return the strategy type."""
        pass

    @abstractmethod
    def resolve(
        self,
        field_name: str,
        local_value: Any,
        remote_value: Any,
        local_timestamp: Optional[Any] = None,
        remote_timestamp: Optional[Any] = None,
    ) -> Any:
        """Resolve conflict between local and remote values."""
        pass

    @abstractmethod
    def should_write_back(
        self,
        field_name: str,
        resolved_value: Any,
        original_remote_value: Any,
    ) -> bool:
        """Determine if the resolved value should be written back to remote."""
        pass


class NeverChangeStrategy(ResolutionStrategy):
    """Strategy 1: Fields that should never change - warn on conflicts."""

    @property
    def strategy_type(self) -> ResolutionStrategyType:
        return ResolutionStrategyType.NEVER_CHANGE

    def resolve(
        self,
        field_name: str,
        local_value: Any,
        remote_value: Any,
        local_timestamp: Optional[Any] = None,
        remote_timestamp: Optional[Any] = None,
    ) -> Any:
        """Resolve by keeping the remote value and warning on conflicts."""
        if local_value != remote_value:
            logger.warning(
                f"Unexpected change detected in immutable field '{field_name}': "
                f"local='{local_value}' vs remote='{remote_value}'. "
                f"Using remote value as authoritative."
            )

        # Always use remote value as authoritative for immutable fields
        return remote_value

    def should_write_back(
        self,
        field_name: str,
        resolved_value: Any,
        original_remote_value: Any,
    ) -> bool:
        """Never write back for immutable fields."""
        return False


class LocalChangesOnlyStrategy(ResolutionStrategy):
    """Strategy 2: Fields that may change locally - write back to remote."""

    @property
    def strategy_type(self) -> ResolutionStrategyType:
        return ResolutionStrategyType.LOCAL_CHANGES_ONLY

    def resolve(
        self,
        field_name: str,
        local_value: Any,
        remote_value: Any,
        local_timestamp: Optional[Any] = None,
        remote_timestamp: Optional[Any] = None,
    ) -> Any:
        """Resolve by using local value and writing back to remote if different."""
        if local_value != remote_value:
            logger.info(
                f"Local change detected in field '{field_name}': "
                f"'{remote_value}' -> '{local_value}'. Will write back to remote."
            )

        # Always use local value
        return local_value

    def should_write_back(
        self,
        field_name: str,
        resolved_value: Any,
        original_remote_value: Any,
    ) -> bool:
        """Write back if local value differs from remote."""
        return bool(resolved_value != original_remote_value)


class RemoteChangesOnlyStrategy(ResolutionStrategy):
    """Strategy 3: Fields that may change remotely - overwrite local."""

    @property
    def strategy_type(self) -> ResolutionStrategyType:
        return ResolutionStrategyType.REMOTE_CHANGES_ONLY

    def resolve(
        self,
        field_name: str,
        local_value: Any,
        remote_value: Any,
        local_timestamp: Optional[Any] = None,
        remote_timestamp: Optional[Any] = None,
    ) -> Any:
        """Resolve by using remote value and overwriting local."""
        if local_value != remote_value:
            logger.info(
                f"Remote change detected in field '{field_name}': "
                f"'{local_value}' -> '{remote_value}'. Updating local value."
            )

        # Always use remote value
        return remote_value

    def should_write_back(
        self,
        field_name: str,
        resolved_value: Any,
        original_remote_value: Any,
    ) -> bool:
        """Never write back for remote-only fields."""
        return False


class RemoteWinsStrategy(ResolutionStrategy):
    """Strategy 4: Fields where remote changes take precedence."""

    @property
    def strategy_type(self) -> ResolutionStrategyType:
        return ResolutionStrategyType.REMOTE_WINS

    def resolve(
        self,
        field_name: str,
        local_value: Any,
        remote_value: Any,
        local_timestamp: Optional[Any] = None,
        remote_timestamp: Optional[Any] = None,
    ) -> Any:
        """Resolve by preferring remote value over local changes."""
        if local_value != remote_value:
            logger.info(
                f"Conflict in field '{field_name}': "
                f"local='{local_value}' vs remote='{remote_value}'. Using remote value."
            )

        # Always use remote value
        return remote_value

    def should_write_back(
        self,
        field_name: str,
        resolved_value: Any,
        original_remote_value: Any,
    ) -> bool:
        """Never write back since remote always wins."""
        return False


class MergeListsStrategy(ResolutionStrategy):
    """Strategy 5: Merge list fields and deduplicate."""

    @property
    def strategy_type(self) -> ResolutionStrategyType:
        return ResolutionStrategyType.MERGE_LISTS

    def resolve(
        self,
        field_name: str,
        local_value: Any,
        remote_value: Any,
        local_timestamp: Optional[Any] = None,
        remote_timestamp: Optional[Any] = None,
    ) -> List[Any]:
        """Resolve by merging lists and removing duplicates."""
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
                f"Merged list field '{field_name}': "
                f"local={local_list}, remote={remote_list} -> merged={merged}"
            )

        return merged

    def should_write_back(
        self,
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


# Strategy factory
_STRATEGY_INSTANCES = {
    ResolutionStrategyType.NEVER_CHANGE: NeverChangeStrategy(),
    ResolutionStrategyType.LOCAL_CHANGES_ONLY: LocalChangesOnlyStrategy(),
    ResolutionStrategyType.REMOTE_CHANGES_ONLY: RemoteChangesOnlyStrategy(),
    ResolutionStrategyType.REMOTE_WINS: RemoteWinsStrategy(),
    ResolutionStrategyType.MERGE_LISTS: MergeListsStrategy(),
}


def get_strategy(strategy_type: ResolutionStrategyType) -> ResolutionStrategy:
    """Get a strategy instance by type."""
    if strategy_type not in _STRATEGY_INSTANCES:
        raise ValueError(f"Unsupported resolution strategy: {strategy_type}")

    return _STRATEGY_INSTANCES[strategy_type]


def get_all_strategies() -> List[ResolutionStrategyType]:
    """Get all available strategy types."""
    return list(_STRATEGY_INSTANCES.keys())
