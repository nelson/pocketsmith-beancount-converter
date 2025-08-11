"""Tests for rule data structures and models."""

import pytest

from src.pocketsmith_beancount.rule_models import (
    RuleApplicationStatus,
    RulePrecondition,
    RuleTransform,
    TransactionRule,
    RuleApplication,
    RuleApplicationBatch,
    RuleValidationError,
    RuleLoadResult,
)


class TestRulePrecondition:
    """Tests for RulePrecondition data model."""

    def test_rule_precondition_creation(self):
        """Test RulePrecondition creation with valid data."""
        precondition = RulePrecondition(
            account="checking", category="food", merchant="mcdonalds"
        )

        assert precondition.account == "checking"
        assert precondition.category == "food"
        assert precondition.merchant == "mcdonalds"
        assert precondition.has_condition()

    def test_rule_precondition_partial(self):
        """Test RulePrecondition with partial data."""
        precondition = RulePrecondition(merchant="walmart")

        assert precondition.account is None
        assert precondition.category is None
        assert precondition.merchant == "walmart"
        assert precondition.has_condition()

    def test_rule_precondition_empty_fails(self):
        """Test RulePrecondition fails with no conditions."""
        with pytest.raises(ValueError, match="At least one precondition"):
            RulePrecondition()

    def test_rule_precondition_all_none_fails(self):
        """Test RulePrecondition fails when all fields are None."""
        with pytest.raises(ValueError, match="At least one precondition"):
            RulePrecondition(account=None, category=None, merchant=None)


class TestRuleTransform:
    """Tests for RuleTransform data model."""

    def test_rule_transform_creation(self):
        """Test RuleTransform creation with valid data."""
        transform = RuleTransform(
            category="Dining",
            labels=["restaurants", "fast-food"],
            memo="Lunch at work",
            metadata={"business": True, "reimbursable": "yes"},
        )

        assert transform.category == "Dining"
        assert transform.labels == ["restaurants", "fast-food"]
        assert transform.memo == "Lunch at work"
        assert transform.metadata == {"business": True, "reimbursable": "yes"}
        assert transform.has_transform()

    def test_rule_transform_aliases(self):
        """Test RuleTransform handles field aliases correctly."""
        # Test tags alias for labels
        transform = RuleTransform(tags=["business", "travel"])
        assert transform.labels == ["business", "travel"]
        assert transform.tags is None

        # Test narration alias for memo
        transform = RuleTransform(narration="Business expense")
        assert transform.memo == "Business expense"
        assert transform.narration is None

    def test_rule_transform_alias_conflicts(self):
        """Test RuleTransform rejects conflicting aliases."""
        with pytest.raises(ValueError, match="Cannot specify both 'labels' and 'tags'"):
            RuleTransform(labels=["a"], tags=["b"])

        with pytest.raises(
            ValueError, match="Cannot specify both 'memo' and 'narration'"
        ):
            RuleTransform(memo="A", narration="B")

    def test_rule_transform_empty_fails(self):
        """Test RuleTransform fails with no transforms."""
        with pytest.raises(ValueError, match="At least one transform"):
            RuleTransform()

    def test_rule_transform_effective_methods(self):
        """Test effective getter methods."""
        transform = RuleTransform(tags=["work"], narration="Meeting")

        assert transform.get_effective_labels() == ["work"]
        assert transform.get_effective_memo() == "Meeting"


class TestTransactionRule:
    """Tests for complete TransactionRule."""

    def test_transaction_rule_creation(self):
        """Test TransactionRule creation with valid data."""
        precondition = RulePrecondition(merchant="starbucks")
        transform = RuleTransform(category="Dining", labels=["coffee"])

        rule = TransactionRule(id=1, precondition=precondition, transform=transform)

        assert rule.id == 1
        assert rule.precondition == precondition
        assert rule.transform == transform

    def test_transaction_rule_validation_invalid_id(self):
        """Test TransactionRule validation rejects invalid IDs."""
        precondition = RulePrecondition(merchant="test")
        transform = RuleTransform(category="Test")

        with pytest.raises(ValueError, match="Rule ID must be a positive integer"):
            TransactionRule(id=0, precondition=precondition, transform=transform)

        with pytest.raises(ValueError, match="Rule ID must be a positive integer"):
            TransactionRule(id=-1, precondition=precondition, transform=transform)

    def test_transaction_rule_validation_types(self):
        """Test TransactionRule validation of component types."""
        with pytest.raises(
            ValueError, match="Rule precondition must be a RulePrecondition"
        ):
            TransactionRule(
                id=1, precondition="invalid", transform=RuleTransform(category="Test")
            )

        with pytest.raises(ValueError, match="Rule transform must be a RuleTransform"):
            TransactionRule(
                id=1,
                precondition=RulePrecondition(merchant="test"),
                transform="invalid",
            )


class TestRuleApplication:
    """Tests for RuleApplication results."""

    def test_rule_application_success(self):
        """Test successful rule application."""
        app = RuleApplication(
            rule_id=1,
            transaction_id="123",
            field_name="CATEGORY",
            old_value="Unknown",
            new_value="Dining",
            status=RuleApplicationStatus.SUCCESS,
        )

        assert app.is_successful
        assert not app.has_error
        assert not app.has_warning

    def test_rule_application_error(self):
        """Test error rule application."""
        app = RuleApplication(
            rule_id=1,
            transaction_id="123",
            field_name="CATEGORY",
            old_value="Unknown",
            new_value="Invalid",
            status=RuleApplicationStatus.INVALID,
            error_message="Category not found",
        )

        assert not app.is_successful
        assert app.has_error
        assert not app.has_warning

    def test_rule_application_warning(self):
        """Test rule application with warning."""
        app = RuleApplication(
            rule_id=1,
            transaction_id="123",
            field_name="MEMO",
            old_value="Old memo",
            new_value="New memo",
            status=RuleApplicationStatus.SUCCESS,
            warning_message="Overwriting existing memo",
        )

        assert app.is_successful
        assert not app.has_error
        assert app.has_warning


class TestRuleApplicationBatch:
    """Tests for RuleApplicationBatch results."""

    def test_rule_application_batch_empty(self):
        """Test empty rule application batch."""
        batch = RuleApplicationBatch()

        assert batch.success_count == 0
        assert batch.error_count == 0
        assert batch.warning_count == 0
        assert len(batch.successful_applications) == 0
        assert len(batch.failed_applications) == 0
        assert len(batch.applications_with_warnings) == 0

    def test_rule_application_batch_mixed(self):
        """Test rule application batch with mixed results."""
        batch = RuleApplicationBatch()

        # Add successful application
        success_app = RuleApplication(
            rule_id=1,
            transaction_id="1",
            field_name="CATEGORY",
            old_value="A",
            new_value="B",
            status=RuleApplicationStatus.SUCCESS,
        )
        batch.add_application(success_app)

        # Add failed application
        error_app = RuleApplication(
            rule_id=2,
            transaction_id="2",
            field_name="CATEGORY",
            old_value="A",
            new_value="B",
            status=RuleApplicationStatus.ERROR,
        )
        batch.add_application(error_app)

        # Add warning application
        warning_app = RuleApplication(
            rule_id=3,
            transaction_id="3",
            field_name="MEMO",
            old_value="A",
            new_value="B",
            status=RuleApplicationStatus.SUCCESS,
            warning_message="Warning",
        )
        batch.add_application(warning_app)

        assert batch.success_count == 2
        assert batch.error_count == 1
        assert batch.warning_count == 1
        assert batch.transactions_matched == 2  # Only successful ones increment


class TestRuleValidationError:
    """Tests for RuleValidationError."""

    def test_rule_validation_error_string(self):
        """Test string representation of validation error."""
        error = RuleValidationError(
            rule_id=1,
            field_name="category",
            error_message="Invalid value",
            file_path="rules.yaml",
            line_number=10,
        )

        error_str = str(error)
        assert "Rule 1" in error_str
        assert "category" in error_str
        assert "Invalid value" in error_str
        assert "rules.yaml" in error_str
        assert "line 10" in error_str

    def test_rule_validation_error_minimal(self):
        """Test validation error with minimal information."""
        error = RuleValidationError(
            rule_id=None, field_name="syntax", error_message="Parse error"
        )

        error_str = str(error)
        assert "syntax: Parse error" == error_str


class TestRuleLoadResult:
    """Tests for RuleLoadResult."""

    def test_rule_load_result_success(self):
        """Test successful rule loading result."""
        result = RuleLoadResult()

        precondition = RulePrecondition(merchant="test")
        transform = RuleTransform(category="Test")
        rule = TransactionRule(id=1, precondition=precondition, transform=transform)

        result.add_rule(rule)
        result.files_processed = 1

        assert result.is_successful
        assert result.rule_count == 1
        assert len(result.errors) == 0

    def test_rule_load_result_with_errors(self):
        """Test rule loading result with errors."""
        result = RuleLoadResult()

        error = RuleValidationError(
            rule_id=1, field_name="test", error_message="Test error"
        )
        result.add_error(error)

        assert not result.is_successful
        assert result.rule_count == 0
        assert len(result.errors) == 1

    def test_rule_load_result_sort_by_priority(self):
        """Test rule sorting by priority (ID)."""
        result = RuleLoadResult()

        # Add rules in non-priority order
        for rule_id in [3, 1, 2]:
            precondition = RulePrecondition(merchant=f"test{rule_id}")
            transform = RuleTransform(category=f"Cat{rule_id}")
            rule = TransactionRule(
                id=rule_id, precondition=precondition, transform=transform
            )
            result.add_rule(rule)

        result.sort_rules_by_priority()

        assert [rule.id for rule in result.rules] == [1, 2, 3]
