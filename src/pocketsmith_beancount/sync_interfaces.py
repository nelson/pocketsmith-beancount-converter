"""Interfaces and abstract base classes for synchronization components."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from .sync_models import FieldChange, SyncConflict, SyncResult, SyncTransaction
from .sync_enums import ResolutionStrategy, ChangeType


class FieldResolver(ABC):
    """Abstract base class for field resolution strategies."""

    @property
    @abstractmethod
    def strategy(self) -> ResolutionStrategy:
        """Return the resolution strategy this resolver implements."""
        pass

    @abstractmethod
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
        Resolve a conflict between local and remote values.

        Args:
            transaction: The transaction being synchronized
            field_name: Name of the field being resolved
            local_value: Value from local beancount data
            remote_value: Value from remote PocketSmith data
            local_timestamp: Timestamp of local modification
            remote_timestamp: Timestamp of remote modification

        Returns:
            The resolved value to use

        Raises:
            FieldResolutionError: If resolution fails
        """
        pass

    @abstractmethod
    def should_write_back(
        self,
        transaction: SyncTransaction,
        field_name: str,
        resolved_value: Any,
        original_remote_value: Any,
    ) -> bool:
        """
        Determine if the resolved value should be written back to remote.

        Args:
            transaction: The transaction being synchronized
            field_name: Name of the field
            resolved_value: The resolved value
            original_remote_value: Original remote value

        Returns:
            True if write-back is needed
        """
        pass


class TransactionComparator(ABC):
    """Interface for transaction comparison logic."""

    @abstractmethod
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
        pass

    @abstractmethod
    def detect_change_type(
        self,
        field_name: str,
        local_value: Any,
        remote_value: Any,
        local_timestamp: Optional[Any] = None,
        remote_timestamp: Optional[Any] = None,
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
        pass


class SyncLogger(ABC):
    """Interface for sync operation logging."""

    @abstractmethod
    def log_sync_start(self, transaction_count: int, dry_run: bool = False) -> None:
        """Log the start of synchronization."""
        pass

    @abstractmethod
    def log_sync_complete(self, summary: Dict[str, Any]) -> None:
        """Log the completion of synchronization."""
        pass

    @abstractmethod
    def log_transaction_sync(self, result: SyncResult) -> None:
        """Log the result of syncing a single transaction."""
        pass

    @abstractmethod
    def log_conflict(self, conflict: SyncConflict) -> None:
        """Log a synchronization conflict."""
        pass

    @abstractmethod
    def log_error(self, error: str, transaction_id: Optional[str] = None) -> None:
        """Log an error during synchronization."""
        pass

    @abstractmethod
    def log_warning(self, warning: str, transaction_id: Optional[str] = None) -> None:
        """Log a warning during synchronization."""
        pass


class APIWriter(ABC):
    """Interface for API write-back operations."""

    @abstractmethod
    def update_transaction(
        self, transaction_id: str, updates: Dict[str, Any], dry_run: bool = False
    ) -> bool:
        """
        Update a transaction via API.

        Args:
            transaction_id: ID of transaction to update
            updates: Dictionary of field updates
            dry_run: If True, don't actually make the API call

        Returns:
            True if update was successful
        """
        pass

    @abstractmethod
    def batch_update_transactions(
        self, updates: List[Dict[str, Any]], dry_run: bool = False
    ) -> List[bool]:
        """
        Update multiple transactions in batch.

        Args:
            updates: List of update dictionaries with transaction_id and fields
            dry_run: If True, don't actually make API calls

        Returns:
            List of success/failure results
        """
        pass

    @abstractmethod
    def validate_update_data(
        self, transaction_id: str, updates: Dict[str, Any]
    ) -> bool:
        """
        Validate update data before sending to API.

        Args:
            transaction_id: ID of transaction to update
            updates: Dictionary of field updates

        Returns:
            True if data is valid
        """
        pass


class SyncOrchestrator(ABC):
    """Interface for synchronization orchestration."""

    @abstractmethod
    def synchronize(
        self,
        local_transactions: List[Dict[str, Any]],
        remote_transactions: List[Dict[str, Any]],
        dry_run: bool = False,
    ) -> List[SyncResult]:
        """
        Synchronize local and remote transactions.

        Args:
            local_transactions: List of local transaction data
            remote_transactions: List of remote transaction data
            dry_run: If True, don't make actual changes

        Returns:
            List of synchronization results
        """
        pass

    @abstractmethod
    def prepare_sync(
        self,
        local_transactions: List[Dict[str, Any]],
        remote_transactions: List[Dict[str, Any]],
    ) -> bool:
        """
        Prepare for synchronization (validation, setup, etc.).

        Args:
            local_transactions: List of local transaction data
            remote_transactions: List of remote transaction data

        Returns:
            True if preparation was successful
        """
        pass
