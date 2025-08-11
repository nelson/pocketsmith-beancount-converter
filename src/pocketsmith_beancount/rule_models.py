"""Data structures for transaction processing rules."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class RuleApplicationStatus(Enum):
    """Status of a rule application to a transaction."""

    SUCCESS = "SUCCESS"
    INVALID = "INVALID"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


@dataclass
class RulePrecondition:
    """Preconditions for matching a transaction against a rule.

    All specified conditions must match for the rule to apply.
    Matching is case-insensitive and supports regex patterns.
    """

    account: Optional[str] = None  # Match against Assets/Liabilities accounts
    category: Optional[str] = None  # Match against Income/Expenses categories
    merchant: Optional[str] = None  # Match against payee/merchant field

    def __post_init__(self) -> None:
        """Validate preconditions after initialization."""
        if not any([self.account, self.category, self.merchant]):
            raise ValueError(
                "At least one precondition (account, category, merchant) must be specified"
            )

    def has_condition(self) -> bool:
        """Check if any conditions are specified."""
        return any([self.account, self.category, self.merchant])


@dataclass
class RuleTransform:
    """Transformations to apply to a transaction when a rule matches.

    Supports category changes, label/tag management, memo updates,
    and metadata additions.
    """

    category: Optional[str] = None  # Change expense/income category
    labels: Optional[List[str]] = None  # Add/remove labels/tags
    tags: Optional[List[str]] = None  # Alias for labels
    memo: Optional[str] = None  # Update transaction memo/narration
    narration: Optional[str] = None  # Alias for memo
    metadata: Optional[Dict[str, Union[str, Decimal, bool, int]]] = None  # Add metadata

    def __post_init__(self) -> None:
        """Validate and normalize transforms after initialization."""
        if not any(
            [
                self.category,
                self.labels,
                self.tags,
                self.memo,
                self.narration,
                self.metadata,
            ]
        ):
            raise ValueError(
                "At least one transform (category, labels, memo, metadata) must be specified"
            )

        # Handle aliases - tags is alias for labels
        if self.tags is not None and self.labels is not None:
            raise ValueError("Cannot specify both 'labels' and 'tags' - use either one")
        if self.tags is not None and self.labels is None:
            self.labels = self.tags
            self.tags = None

        # Handle aliases - narration is alias for memo
        if self.narration is not None and self.memo is not None:
            raise ValueError(
                "Cannot specify both 'memo' and 'narration' - use either one"
            )
        if self.narration is not None and self.memo is None:
            self.memo = self.narration
            self.narration = None

    def has_transform(self) -> bool:
        """Check if any transforms are specified."""
        return any([self.category, self.labels, self.memo, self.metadata])

    def get_effective_labels(self) -> Optional[List[str]]:
        """Get the effective labels list (handling tags alias)."""
        return self.labels

    def get_effective_memo(self) -> Optional[str]:
        """Get the effective memo string (handling narration alias)."""
        return self.memo


@dataclass
class TransactionRule:
    """A complete transaction processing rule with ID, preconditions, and transforms."""

    id: int
    precondition: RulePrecondition
    transform: RuleTransform

    def __post_init__(self) -> None:
        """Validate rule after initialization."""
        if self.id <= 0:
            raise ValueError("Rule ID must be a positive integer")

        if not isinstance(self.precondition, RulePrecondition):
            raise ValueError("Rule precondition must be a RulePrecondition instance")

        if not isinstance(self.transform, RuleTransform):
            raise ValueError("Rule transform must be a RuleTransform instance")

        if not self.precondition.has_condition():
            raise ValueError("Rule must have at least one precondition")

        if not self.transform.has_transform():
            raise ValueError("Rule must have at least one transform")


@dataclass
class RuleApplication:
    """Result of applying a rule to a transaction."""

    rule_id: int
    transaction_id: str
    field_name: str
    old_value: Any
    new_value: Any
    status: RuleApplicationStatus
    error_message: Optional[str] = None
    warning_message: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        """Check if the rule application was successful."""
        return self.status == RuleApplicationStatus.SUCCESS

    @property
    def has_error(self) -> bool:
        """Check if the rule application had an error."""
        return self.status in [
            RuleApplicationStatus.ERROR,
            RuleApplicationStatus.INVALID,
        ]

    @property
    def has_warning(self) -> bool:
        """Check if the rule application has a warning."""
        return self.warning_message is not None


@dataclass
class RuleApplicationBatch:
    """Results from applying rules to multiple transactions."""

    applications: List[RuleApplication] = field(default_factory=list)
    rules_loaded: int = 0
    transactions_processed: int = 0
    transactions_matched: int = 0

    def add_application(self, application: RuleApplication) -> None:
        """Add a rule application result."""
        self.applications.append(application)
        if application.is_successful:
            self.transactions_matched += 1

    @property
    def successful_applications(self) -> List[RuleApplication]:
        """Get all successful rule applications."""
        return [app for app in self.applications if app.is_successful]

    @property
    def failed_applications(self) -> List[RuleApplication]:
        """Get all failed rule applications."""
        return [app for app in self.applications if app.has_error]

    @property
    def applications_with_warnings(self) -> List[RuleApplication]:
        """Get all rule applications with warnings."""
        return [app for app in self.applications if app.has_warning]

    @property
    def success_count(self) -> int:
        """Count of successful applications."""
        return len(self.successful_applications)

    @property
    def error_count(self) -> int:
        """Count of failed applications."""
        return len(self.failed_applications)

    @property
    def warning_count(self) -> int:
        """Count of applications with warnings."""
        return len(self.applications_with_warnings)


@dataclass
class RuleValidationError:
    """Error found during rule validation."""

    rule_id: Optional[int]
    field_name: str
    error_message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None

    def __str__(self) -> str:
        """String representation of the validation error."""
        location = ""
        if self.file_path:
            location += f" in {self.file_path}"
        if self.line_number:
            location += f" at line {self.line_number}"

        rule_info = ""
        if self.rule_id is not None:
            rule_info = f"Rule {self.rule_id} "

        return f"{rule_info}{self.field_name}: {self.error_message}{location}"


@dataclass
class RuleLoadResult:
    """Result of loading rules from files."""

    rules: List[TransactionRule] = field(default_factory=list)
    errors: List[RuleValidationError] = field(default_factory=list)
    files_processed: int = 0

    @property
    def is_successful(self) -> bool:
        """Check if rule loading was successful (no errors)."""
        return len(self.errors) == 0

    @property
    def rule_count(self) -> int:
        """Count of successfully loaded rules."""
        return len(self.rules)

    def add_rule(self, rule: TransactionRule) -> None:
        """Add a successfully loaded rule."""
        self.rules.append(rule)

    def add_error(self, error: RuleValidationError) -> None:
        """Add a validation error."""
        self.errors.append(error)

    def sort_rules_by_priority(self) -> None:
        """Sort rules by ID (priority order)."""
        self.rules.sort(key=lambda r: r.id)
