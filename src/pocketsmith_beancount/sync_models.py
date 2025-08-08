"""Data models for synchronization operations."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from .sync_enums import ChangeType, ResolutionStrategy, SyncStatus, SyncDirection


@dataclass
class FieldChange:
    """Represents a change in a specific field."""

    field_name: str
    old_value: Any
    new_value: Any
    change_type: ChangeType
    strategy: ResolutionStrategy
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Validate field change data."""
        if self.field_name is None or self.field_name == "":
            raise ValueError("Field name cannot be empty")


@dataclass
class SyncTransaction:
    """Unified transaction representation for synchronization."""

    id: str
    local_data: Optional[Dict[str, Any]] = None
    remote_data: Optional[Dict[str, Any]] = None
    local_last_modified: Optional[datetime] = None
    remote_last_modified: Optional[datetime] = None

    # Core transaction fields
    amount: Optional[Decimal] = None
    date: Optional[str] = None
    merchant: Optional[str] = None
    payee: Optional[str] = None
    note: Optional[str] = None
    memo: Optional[str] = None
    category: Optional[Dict[str, Any]] = None
    labels: Optional[List[str]] = None
    needs_review: Optional[bool] = None
    closing_balance: Optional[Decimal] = None
    currency_code: Optional[str] = None
    transaction_account: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate transaction data."""
        if not self.id:
            raise ValueError("Transaction ID cannot be empty")

        # Ensure labels is a list
        if self.labels is None:
            self.labels = []
        elif not isinstance(self.labels, list):
            self.labels = list(self.labels) if self.labels else []


@dataclass
class SyncConflict:
    """Represents a conflict between local and remote data."""

    transaction_id: str
    field_name: str
    local_value: Any
    remote_value: Any
    local_timestamp: Optional[datetime]
    remote_timestamp: Optional[datetime]
    strategy: ResolutionStrategy
    resolution: Optional[Any] = None
    status: SyncStatus = SyncStatus.CONFLICT
    message: Optional[str] = None

    def __post_init__(self) -> None:
        """Generate default conflict message if not provided."""
        if self.message is None:
            self.message = f"Conflict in field '{self.field_name}' for transaction {self.transaction_id}"


@dataclass
class SyncResult:
    """Results of synchronization operation."""

    transaction_id: str
    status: SyncStatus
    changes: List[FieldChange] = field(default_factory=list)
    conflicts: List[SyncConflict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sync_direction: SyncDirection = SyncDirection.NO_SYNC
    timestamp: datetime = field(default_factory=datetime.now)
    resolved_data: Dict[str, Any] = field(default_factory=dict)
    write_back_needed: Dict[str, bool] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        """Check if any changes were made."""
        return len(self.changes) > 0

    @property
    def has_conflicts(self) -> bool:
        """Check if any conflicts were detected."""
        return len(self.conflicts) > 0

    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if any warnings were generated."""
        return len(self.warnings) > 0

    def add_change(
        self,
        field_name: str,
        old_value: Any,
        new_value: Any,
        change_type: ChangeType,
        strategy: ResolutionStrategy,
    ) -> None:
        """Add a field change to the result."""
        change = FieldChange(
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            change_type=change_type,
            strategy=strategy,
        )
        self.changes.append(change)

    def add_conflict(
        self,
        field_name: str,
        local_value: Any,
        remote_value: Any,
        strategy: ResolutionStrategy,
        local_timestamp: Optional[datetime] = None,
        remote_timestamp: Optional[datetime] = None,
        message: Optional[str] = None,
    ) -> None:
        """Add a conflict to the result."""
        conflict = SyncConflict(
            transaction_id=self.transaction_id,
            field_name=field_name,
            local_value=local_value,
            remote_value=remote_value,
            local_timestamp=local_timestamp,
            remote_timestamp=remote_timestamp,
            strategy=strategy,
            message=message,
        )
        self.conflicts.append(conflict)

    def add_error(self, error_message: str) -> None:
        """Add an error message to the result."""
        self.errors.append(error_message)

    def add_warning(self, warning_message: str) -> None:
        """Add a warning message to the result."""
        self.warnings.append(warning_message)


@dataclass
class SyncSummary:
    """Summary of synchronization operation across all transactions."""

    total_transactions: int = 0
    successful_syncs: int = 0
    conflicts_detected: int = 0
    errors_encountered: int = 0
    warnings_generated: int = 0
    changes_made: int = 0
    local_to_remote_updates: int = 0
    remote_to_local_updates: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    dry_run: bool = False

    @property
    def duration(self) -> Optional[float]:
        """Calculate sync duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_transactions == 0:
            return 0.0
        return (self.successful_syncs / self.total_transactions) * 100.0

    def add_result(self, result: SyncResult) -> None:
        """Add a sync result to the summary."""
        self.total_transactions += 1

        if result.status == SyncStatus.SUCCESS:
            self.successful_syncs += 1

        if result.has_conflicts:
            self.conflicts_detected += len(result.conflicts)

        if result.has_errors:
            self.errors_encountered += len(result.errors)

        if result.has_warnings:
            self.warnings_generated += len(result.warnings)

        if result.has_changes:
            self.changes_made += len(result.changes)

        if result.sync_direction == SyncDirection.LOCAL_TO_REMOTE:
            self.local_to_remote_updates += 1
        elif result.sync_direction == SyncDirection.REMOTE_TO_LOCAL:
            self.remote_to_local_updates += 1
