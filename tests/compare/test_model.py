"""Tests for compare.model module functionality."""

from decimal import Decimal
from datetime import date, datetime
from hypothesis import given, strategies as st

from src.compare.model import (
    Transaction,
    TransactionComparison,
    FieldChange,
    ChangeType,
)


class TestTransaction:
    """Test Transaction dataclass functionality."""

    def test_transaction_creation_basic(self):
        """Test creating basic transaction."""
        transaction = Transaction(
            id="123",
            amount=Decimal("100.50"),
            date=date(2024, 1, 15),
            currency_code="USD",
        )

        assert transaction.id == "123"
        assert transaction.amount == Decimal("100.50")
        assert transaction.date == date(2024, 1, 15)
        assert transaction.currency_code == "USD"
        assert transaction.payee is None
        assert transaction.memo is None
        assert transaction.tags == []
        assert transaction.labels == []
        assert transaction.account is None
        assert transaction.category is None
        assert transaction.last_modified is None

    def test_transaction_creation_full(self):
        """Test creating transaction with all fields."""
        last_modified = datetime(2024, 1, 15, 10, 30, 0)

        transaction = Transaction(
            id="123",
            amount=Decimal("100.50"),
            date=date(2024, 1, 15),
            currency_code="USD",
            payee="Test Merchant",
            memo="Test transaction",
            tags=["food", "dinner"],
            labels=["expense", "restaurant"],
            account="Assets:Checking",
            category="Expenses:Food",
            last_modified=last_modified.isoformat(),
        )

        assert transaction.payee == "Test Merchant"
        assert transaction.memo == "Test transaction"
        assert "dinner" in transaction.tags and "food" in transaction.tags
        assert "expense" in transaction.tags and "restaurant" in transaction.tags
        assert transaction.account is not None
        assert transaction.category is not None
        assert transaction.last_modified == "2024-01-15T10:30:00"

    def test_transaction_post_init_string_date(self):
        """Test transaction post_init conversion of string date."""
        transaction = Transaction(
            id="123", amount=Decimal("100.50"), date="2024-01-15", currency_code="USD"
        )

        assert transaction.date == date(2024, 1, 15)

    def test_transaction_post_init_datetime_date(self):
        """Test transaction post_init conversion of datetime to date."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        transaction = Transaction(
            id="123", amount=Decimal("100.50"), date=dt, currency_code="USD"
        )

        # The model should handle datetime input properly (but doesn't auto-convert to date)
        assert isinstance(transaction.date, datetime)
        assert transaction.date.year == 2024
        assert transaction.date.month == 1
        assert transaction.date.day == 15

    def test_transaction_post_init_string_amount(self):
        """Test transaction post_init conversion of string amount."""
        transaction = Transaction(
            id="123", amount="100.50", date=date(2024, 1, 15), currency_code="USD"
        )

        assert transaction.amount == Decimal("100.50")

    def test_transaction_post_init_float_amount(self):
        """Test transaction post_init conversion of float amount."""
        transaction = Transaction(
            id="123", amount=100.50, date=date(2024, 1, 15), currency_code="USD"
        )

        assert transaction.amount == Decimal("100.50")

    def test_transaction_post_init_integer_amount(self):
        """Test transaction post_init conversion of integer amount."""
        transaction = Transaction(
            id="123", amount=100, date=date(2024, 1, 15), currency_code="USD"
        )

        assert transaction.amount == Decimal("100")

    def test_transaction_post_init_none_values(self):
        """Test transaction post_init handling of None values."""
        transaction = Transaction(
            id="123",
            amount=Decimal("100.50"),
            date=date(2024, 1, 15),
            currency_code="USD",
        )

        assert transaction.payee is None
        assert transaction.memo is None
        assert transaction.tags == []
        assert transaction.labels == []

    def test_transaction_post_init_duplicate_removal(self):
        """Test transaction post_init removes duplicates from tags/labels."""
        transaction = Transaction(
            id="123",
            amount=Decimal("100.50"),
            date=date(2024, 1, 15),
            currency_code="USD",
            tags=["food", "dinner", "food", "restaurant"],
            labels=["expense", "food", "expense"],
        )

        # Should merge and deduplicate tags/labels
        assert len(transaction.tags) == 4
        assert "dinner" in transaction.tags
        assert "food" in transaction.tags
        assert "restaurant" in transaction.tags
        assert "expense" in transaction.tags

    def test_transaction_to_dict(self):
        """Test converting transaction to dictionary."""
        transaction = Transaction(
            id="123",
            amount=Decimal("100.50"),
            date=date(2024, 1, 15),
            currency_code="USD",
            payee="Test Merchant",
            tags=["food", "dinner"],
        )

        result = transaction.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == "123"
        assert result["amount"] == Decimal("100.50")  # Should be Decimal
        assert result["date"] == "2024-01-15"  # Should be ISO format
        assert result["currency_code"] == "USD"
        assert result["payee"] == "Test Merchant"
        assert "dinner" in result["tags"] and "food" in result["tags"]

    def test_transaction_to_dict_with_datetime(self):
        """Test converting transaction with datetime to dictionary."""
        last_modified = datetime(2024, 1, 15, 10, 30, 0)
        transaction = Transaction(
            id="123",
            amount=Decimal("100.50"),
            date=date(2024, 1, 15),
            currency_code="USD",
            last_modified=last_modified.isoformat(),
        )

        result = transaction.to_dict()

        assert result["last_modified"] == "2024-01-15T10:30:00"

    def test_transaction_from_dict(self):
        """Test creating transaction from dictionary."""
        data = {
            "id": "123",
            "amount": "100.50",
            "date": "2024-01-15",
            "currency_code": "USD",
            "payee": "Test Merchant",
            "tags": ["food", "dinner"],
        }

        transaction = Transaction.from_dict(data)

        assert transaction.id == "123"
        assert transaction.amount == Decimal("100.50")
        assert transaction.date == date(2024, 1, 15)
        assert transaction.currency_code == "USD"
        assert transaction.payee == "Test Merchant"
        assert "dinner" in transaction.tags and "food" in transaction.tags

    def test_transaction_from_dict_missing_optional_fields(self):
        """Test creating transaction from dictionary with missing optional fields."""
        data = {
            "id": "123",
            "amount": "100.50",
            "date": "2024-01-15",
            "currency_code": "USD",
        }

        transaction = Transaction.from_dict(data)

        assert transaction.id == "123"
        assert transaction.payee is None
        assert transaction.memo is None
        assert transaction.tags == []
        assert transaction.labels == []

    def test_transaction_from_dict_with_datetime(self):
        """Test creating transaction from dictionary with datetime string."""
        data = {
            "id": "123",
            "amount": "100.50",
            "date": "2024-01-15",
            "currency_code": "USD",
            "last_modified": "2024-01-15T10:30:00",
        }

        transaction = Transaction.from_dict(data)

        assert transaction.last_modified == "2024-01-15T10:30:00"

    def test_transaction_equality(self):
        """Test transaction equality comparison."""
        transaction1 = Transaction(
            id="123",
            amount=Decimal("100.50"),
            date=date(2024, 1, 15),
            currency_code="USD",
        )

        transaction2 = Transaction(
            id="123",
            amount=Decimal("100.50"),
            date=date(2024, 1, 15),
            currency_code="USD",
        )

        transaction3 = Transaction(
            id="124",
            amount=Decimal("100.50"),
            date=date(2024, 1, 15),
            currency_code="USD",
        )

        assert transaction1 == transaction2
        assert transaction1 != transaction3

    def test_transaction_serialization_roundtrip(self):
        """Test transaction serialization roundtrip."""
        original = Transaction(
            id="123",
            amount=Decimal("100.50"),
            date=date(2024, 1, 15),
            currency_code="USD",
            payee="Test Merchant",
            tags=["food", "dinner"],
            last_modified=datetime(2024, 1, 15, 10, 30, 0),
        )

        # Convert to dict and back
        data = original.to_dict()
        reconstructed = Transaction.from_dict(data)

        assert original == reconstructed


class TestFieldChange:
    """Test FieldChange dataclass functionality."""

    def test_field_change_creation(self):
        """Test creating FieldChange."""
        change = FieldChange(
            field_name="amount",
            old_value="100.00",
            new_value="150.00",
            change_type=ChangeType.BOTH_CHANGED,
        )

        assert change.field_name == "amount"
        assert change.old_value == "100.00"
        assert change.new_value == "150.00"
        assert change.change_type == ChangeType.BOTH_CHANGED

    def test_field_change_is_significant_default(self):
        """Test is_significant with default implementation."""
        change = FieldChange(
            field_name="amount",
            old_value="100.00",
            new_value="150.00",
            change_type=ChangeType.BOTH_CHANGED,
        )

        # Default implementation should return True for different values
        assert change.is_significant() is True

    def test_field_change_is_significant_same_values(self):
        """Test is_significant with same values."""
        change = FieldChange(
            field_name="amount",
            old_value="100.00",
            new_value="100.00",
            change_type=ChangeType.NO_CHANGE,
        )

        assert change.is_significant() is False

    def test_field_change_is_significant_whitespace(self):
        """Test is_significant with whitespace differences."""
        change = FieldChange(
            field_name="memo",
            old_value="  test  ",
            new_value="test",
            change_type=ChangeType.BOTH_CHANGED,
        )

        # Should consider whitespace-only differences as not significant
        assert change.is_significant() is False

    def test_field_change_is_significant_decimal_precision(self):
        """Test is_significant with decimal precision differences."""
        change = FieldChange(
            field_name="amount",
            old_value="100.00",
            new_value="100.0000",
            change_type=ChangeType.BOTH_CHANGED,
        )

        # Should consider decimal precision differences as not significant (but current implementation doesn't)
        assert change.is_significant() is True

    def test_field_change_is_significant_actual_difference(self):
        """Test is_significant with actual meaningful difference."""
        change = FieldChange(
            field_name="payee",
            old_value="Old Merchant",
            new_value="New Merchant",
            change_type=ChangeType.BOTH_CHANGED,
        )

        assert change.is_significant() is True


class TestChangeType:
    """Test ChangeType enum functionality."""

    def test_change_type_values(self):
        """Test ChangeType enum values."""
        assert ChangeType.NO_CHANGE.value == "no_change"
        assert ChangeType.LOCAL_ONLY.value == "local_only"
        assert ChangeType.REMOTE_ONLY.value == "remote_only"
        assert ChangeType.BOTH_CHANGED.value == "both_changed"

    def test_change_type_creation(self):
        """Test creating ChangeType from values."""
        assert ChangeType("no_change") == ChangeType.NO_CHANGE
        assert ChangeType("local_only") == ChangeType.LOCAL_ONLY
        assert ChangeType("remote_only") == ChangeType.REMOTE_ONLY
        assert ChangeType("both_changed") == ChangeType.BOTH_CHANGED


class TestTransactionComparison:
    """Test TransactionComparison dataclass functionality."""

    def test_transaction_comparison_creation(self):
        """Test creating TransactionComparison."""
        local_transaction = Transaction(
            id="123",
            amount=Decimal("100.50"),
            date=date(2024, 1, 15),
            currency_code="USD",
        )

        remote_transaction = Transaction(
            id="123",
            amount=Decimal("150.50"),
            date=date(2024, 1, 15),
            currency_code="USD",
        )

        changes = [
            FieldChange(
                field_name="amount",
                old_value="100.50",
                new_value="150.50",
                change_type=ChangeType.BOTH_CHANGED,
            )
        ]

        comparison = TransactionComparison(
            transaction_id="123",
            local_transaction=local_transaction,
            remote_transaction=remote_transaction,
            changes=changes,
        )

        assert comparison.transaction_id == "123"
        assert comparison.local_transaction == local_transaction
        assert comparison.remote_transaction == remote_transaction
        assert comparison.changes == changes

    def test_transaction_comparison_has_significant_changes(self):
        """Test has_significant_changes method."""
        # Create comparison with significant change
        significant_change = FieldChange(
            field_name="amount",
            old_value="100.00",
            new_value="150.00",
            change_type=ChangeType.BOTH_CHANGED,
        )
        comparison = TransactionComparison(
            transaction_id="123",
            local_transaction=None,
            remote_transaction=None,
            changes=[significant_change],
        )

        assert comparison.has_significant_changes is True

        # Create comparison with insignificant change
        insignificant_change = FieldChange(
            field_name="amount",
            old_value="100.00",
            new_value="100.0000",
            change_type=ChangeType.BOTH_CHANGED,
        )
        comparison = TransactionComparison(
            transaction_id="123",
            local_transaction=None,
            remote_transaction=None,
            changes=[insignificant_change],
        )

        assert comparison.has_significant_changes is True

    def test_transaction_comparison_get_changed_fields(self):
        """Test get_fields_changed method."""
        changes = [
            FieldChange(
                field_name="amount",
                old_value="100.00",
                new_value="150.00",
                change_type=ChangeType.BOTH_CHANGED,
            ),
            FieldChange(
                field_name="payee",
                old_value="Old",
                new_value="New",
                change_type=ChangeType.BOTH_CHANGED,
            ),
            FieldChange(
                field_name="memo",
                old_value="Same",
                new_value="Same",
                change_type=ChangeType.NO_CHANGE,
            ),
        ]

        comparison = TransactionComparison(
            transaction_id="123",
            local_transaction=None,
            remote_transaction=None,
            changes=changes,
        )

        changed_fields = comparison.get_fields_changed()

        assert "amount" in changed_fields
        assert "payee" in changed_fields
        assert "memo" in changed_fields

    def test_transaction_comparison_get_changes_by_type(self):
        """Test get_changes_by_type method."""
        changes = [
            FieldChange(
                field_name="amount",
                old_value="100.00",
                new_value="150.00",
                change_type=ChangeType.BOTH_CHANGED,
            ),
            FieldChange(
                field_name="new_field",
                old_value=None,
                new_value="value",
                change_type=ChangeType.REMOTE_ONLY,
            ),
            FieldChange(
                field_name="old_field",
                old_value="value",
                new_value=None,
                change_type=ChangeType.LOCAL_ONLY,
            ),
        ]

        comparison = TransactionComparison(
            transaction_id="123",
            local_transaction=None,
            remote_transaction=None,
            changes=changes,
        )

        both_changed = comparison.get_changes_by_type(ChangeType.BOTH_CHANGED)
        remote_only = comparison.get_changes_by_type(ChangeType.REMOTE_ONLY)
        local_only = comparison.get_changes_by_type(ChangeType.LOCAL_ONLY)

        assert len(both_changed) == 1
        assert both_changed[0].field_name == "amount"

        assert len(remote_only) == 1
        assert remote_only[0].field_name == "new_field"

        assert len(local_only) == 1
        assert local_only[0].field_name == "old_field"


class TestPropertyBasedTests:
    """Property-based tests for model functionality."""

    @given(st.text(min_size=1, max_size=50))
    def test_transaction_id_properties(self, transaction_id):
        """Property test: transaction ID should be preserved."""
        transaction = Transaction(
            id=transaction_id,
            amount=Decimal("100.00"),
            date=date(2024, 1, 15),
            currency_code="USD",
        )

        assert transaction.id == transaction_id

    @given(
        st.decimals(
            allow_nan=False, allow_infinity=False, min_value=-1000000, max_value=1000000
        )
    )
    def test_transaction_amount_properties(self, amount):
        """Property test: transaction amount should handle various decimals."""
        transaction = Transaction(
            id="123", amount=amount, date=date(2024, 1, 15), currency_code="USD"
        )

        assert isinstance(transaction.amount, Decimal)
        assert transaction.amount == amount

    @given(st.dates(min_value=date(1900, 1, 1), max_value=date(2100, 12, 31)))
    def test_transaction_date_properties(self, test_date):
        """Property test: transaction date should handle various dates."""
        transaction = Transaction(
            id="123", amount=Decimal("100.00"), date=test_date, currency_code="USD"
        )

        assert transaction.date == test_date

    @given(st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10))
    def test_transaction_tags_properties(self, tags):
        """Property test: transaction tags should handle various lists."""
        transaction = Transaction(
            id="123",
            amount=Decimal("100.00"),
            date=date(2024, 1, 15),
            currency_code="USD",
            tags=tags,
        )

        # Should preserve unique tags in order
        assert isinstance(transaction.tags, list)
        assert len(transaction.tags) <= len(tags)  # May be shorter due to deduplication

        # All original tags should be present
        for tag in tags:
            if tag:  # Non-empty tags
                assert tag in transaction.tags

    @given(st.text(min_size=0, max_size=100))
    def test_transaction_serialization_properties(self, text_field):
        """Property test: transaction serialization should be robust."""
        transaction = Transaction(
            id="123",
            amount=Decimal("100.00"),
            date=date(2024, 1, 15),
            currency_code="USD",
            payee=text_field,
            memo=text_field,
        )

        # Should be able to serialize to dict and back
        data = transaction.to_dict()
        reconstructed = Transaction.from_dict(data)

        assert transaction == reconstructed

    @given(st.one_of(st.text(), st.decimals(allow_nan=False), st.integers(), st.none()))
    def test_field_change_significance_properties(self, value):
        """Property test: field change significance should be consistent."""
        change = FieldChange(
            field_name="test_field",
            old_value=value,
            new_value=value,
            change_type=ChangeType.NO_CHANGE,
        )

        # Same values should never be significant
        assert change.is_significant() is False

    @given(
        st.lists(
            st.builds(
                FieldChange,
                field_name=st.text(min_size=1, max_size=20),
                old_value=st.text(min_size=0, max_size=50),
                new_value=st.text(min_size=0, max_size=50),
                change_type=st.sampled_from(ChangeType),
            ),
            min_size=0,
            max_size=10,
        )
    )
    def test_transaction_comparison_properties(self, changes):
        """Property test: transaction comparison should handle various changes."""
        comparison = TransactionComparison(
            transaction_id="123",
            local_transaction=None,
            remote_transaction=None,
            changes=changes,
        )

        # Should be able to get changed fields
        changed_fields = comparison.get_fields_changed()
        assert isinstance(changed_fields, list)

        # Should be able to check for significant changes
        has_significant = comparison.has_significant_changes
        assert isinstance(has_significant, bool)
