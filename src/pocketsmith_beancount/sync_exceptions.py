"""Exception classes for synchronization operations."""

from typing import Any, Optional


class SynchronizationError(Exception):
    """Base exception for synchronization operations."""

    def __init__(
        self,
        message: str,
        transaction_id: Optional[str] = None,
        field_name: Optional[str] = None,
    ):
        super().__init__(message)
        self.transaction_id = transaction_id
        self.field_name = field_name


class FieldResolutionError(SynchronizationError):
    """Exception raised when field resolution fails."""

    def __init__(
        self,
        message: str,
        field_name: str,
        strategy: Optional[str] = None,
        transaction_id: Optional[str] = None,
    ):
        super().__init__(message, transaction_id, field_name)
        self.strategy = strategy


class APIWriteBackError(SynchronizationError):
    """Exception raised when API write-back operations fail."""

    def __init__(
        self,
        message: str,
        transaction_id: Optional[str] = None,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        super().__init__(message, transaction_id)
        self.status_code = status_code
        self.response_body = response_body


class TransactionComparisonError(SynchronizationError):
    """Exception raised when transaction comparison fails."""

    def __init__(
        self,
        message: str,
        local_id: Optional[str] = None,
        remote_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.local_id = local_id
        self.remote_id = remote_id


class SyncConfigurationError(SynchronizationError):
    """Exception raised when synchronization configuration is invalid."""

    pass


class DataIntegrityError(SynchronizationError):
    """Exception raised when data integrity checks fail."""

    def __init__(
        self,
        message: str,
        transaction_id: Optional[str] = None,
        field_name: Optional[str] = None,
        expected_value: Any = None,
        actual_value: Any = None,
    ):
        super().__init__(message, transaction_id, field_name)
        self.expected_value = expected_value
        self.actual_value = actual_value
