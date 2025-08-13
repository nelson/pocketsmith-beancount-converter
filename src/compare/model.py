"""Standard transaction model for comparison operations."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from decimal import Decimal
from datetime import datetime, date
from enum import Enum


class ChangeType(Enum):
    """Types of changes detected in field comparison."""

    NO_CHANGE = "no_change"
    LOCAL_ONLY = "local_only"
    REMOTE_ONLY = "remote_only"
    BOTH_CHANGED = "both_changed"


@dataclass
class Transaction:
    """Standard transaction model for comparison operations."""

    # Core immutable fields
    id: str
    amount: Decimal
    date: Union[date, str]
    currency_code: str

    # Basic transaction info
    merchant: Optional[str] = None
    payee: Optional[str] = None
    note: Optional[str] = None
    memo: Optional[str] = None

    # Categorization
    category: Optional[Dict[str, Any]] = None
    account: Optional[Dict[str, Any]] = None

    # Labels and metadata
    labels: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Status fields
    needs_review: Optional[bool] = None

    # Balance information
    closing_balance: Optional[Decimal] = None

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_modified: Optional[str] = None

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Post-initialization processing."""
        # Ensure amount is Decimal
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))

        # Ensure closing_balance is Decimal if provided
        if self.closing_balance is not None and not isinstance(
            self.closing_balance, Decimal
        ):
            self.closing_balance = Decimal(str(self.closing_balance))

        # Ensure date is consistent format
        if isinstance(self.date, str):
            try:
                parsed_date = datetime.fromisoformat(self.date.replace("Z", "+00:00"))
                self.date = parsed_date.date()
            except ValueError:
                pass  # Keep original string if parsing fails

        # Merge tags and labels for consistency
        all_tags = set(self.tags + self.labels)
        self.tags = sorted(list(all_tags))

    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            "id": self.id,
            "amount": self.amount,
            "date": self.date.strftime("%Y-%m-%d")
            if isinstance(self.date, date)
            else self.date,
            "currency_code": self.currency_code,
            "merchant": self.merchant,
            "payee": self.payee,
            "note": self.note,
            "memo": self.memo,
            "category": self.category,
            "account": self.account,
            "labels": self.labels,
            "tags": self.tags,
            "needs_review": self.needs_review,
            "closing_balance": self.closing_balance,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_modified": self.last_modified,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        """Create transaction from dictionary."""
        # Handle timestamps
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(
                    data["created_at"].replace("Z", "+00:00")
                )
            except ValueError:
                pass

        updated_at = None
        if data.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(
                    data["updated_at"].replace("Z", "+00:00")
                )
            except ValueError:
                pass

        return cls(
            id=str(data["id"]),
            amount=Decimal(str(data["amount"])),
            date=data["date"],
            currency_code=data["currency_code"],
            merchant=data.get("merchant"),
            payee=data.get("payee"),
            note=data.get("note"),
            memo=data.get("memo"),
            category=data.get("category"),
            account=data.get("account"),
            labels=data.get("labels", []),
            tags=data.get("tags", []),
            needs_review=data.get("needs_review"),
            closing_balance=Decimal(str(data["closing_balance"]))
            if data.get("closing_balance") is not None
            else None,
            created_at=created_at,
            updated_at=updated_at,
            last_modified=data.get("last_modified"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class FieldChange:
    """Represents a change detected in a transaction field."""

    field_name: str
    old_value: Any
    new_value: Any
    change_type: ChangeType

    def is_significant(self) -> bool:
        """Determine if this change is significant."""
        # No change is never significant
        if self.change_type == ChangeType.NO_CHANGE:
            return False

        # Handle string comparisons - ignore whitespace-only changes
        if isinstance(self.old_value, str) and isinstance(self.new_value, str):
            return self.old_value.strip() != self.new_value.strip()

        # Handle numeric comparisons - ignore very small differences
        if isinstance(self.old_value, (int, float, Decimal)) and isinstance(
            self.new_value, (int, float, Decimal)
        ):
            try:
                old_decimal = Decimal(str(self.old_value))
                new_decimal = Decimal(str(self.new_value))
                diff = abs(old_decimal - new_decimal)
                # Consider differences smaller than 0.01 as insignificant
                return diff >= Decimal("0.01")
            except (ValueError, TypeError):
                pass

        # For other types, any difference is significant
        return bool(self.old_value != self.new_value)

    def __str__(self) -> str:
        return f"{self.field_name}: {self.old_value} -> {self.new_value} ({self.change_type.value})"


@dataclass
class TransactionComparison:
    """Result of comparing two transactions."""

    transaction_id: str
    local_transaction: Optional[Transaction]
    remote_transaction: Optional[Transaction]
    changes: List[FieldChange] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Check if any changes were detected."""
        return len(self.changes) > 0

    @property
    def significant_changes(self) -> List[FieldChange]:
        """Get only significant changes."""
        return [change for change in self.changes if change.is_significant()]

    @property
    def has_significant_changes(self) -> bool:
        """Check if any significant changes were detected."""
        return len(self.significant_changes) > 0

    def get_changes_by_type(self, change_type: ChangeType) -> List[FieldChange]:
        """Get changes of a specific type."""
        return [change for change in self.changes if change.change_type == change_type]

    def get_fields_changed(self) -> List[str]:
        """Get list of field names that changed."""
        return [change.field_name for change in self.changes]

    def __str__(self) -> str:
        status = "with changes" if self.has_changes else "no changes"
        return f"TransactionComparison({self.transaction_id}) - {status}"
