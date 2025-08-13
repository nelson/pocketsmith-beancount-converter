"""Tests for compare.pocketsmith module functionality."""

from decimal import Decimal
from datetime import date, datetime
from hypothesis import given, strategies as st

from src.compare.pocketsmith import (
    convert_pocketsmith_to_model,
    convert_pocketsmith_list_to_model,
    _format_category,
    _format_account,
    _parse_date,
    _parse_timestamp,
)
from src.compare.model import Transaction


class TestConvertPocketsmithToModel:
    """Test converting PocketSmith data to Transaction model."""

    def test_convert_minimal_pocketsmith_transaction(self):
        """Test converting minimal PocketSmith transaction."""
        pocketsmith_data = {"id": 123, "amount": "100.50", "date": "2024-01-15"}

        transaction = convert_pocketsmith_to_model(pocketsmith_data)

        assert transaction.id == "123"
        assert transaction.amount == Decimal("100.50")
        assert transaction.date == date(2024, 1, 15)
        assert transaction.currency_code == "USD"  # Default

    def test_convert_full_pocketsmith_transaction(self):
        """Test converting full PocketSmith transaction."""
        pocketsmith_data = {
            "id": 123,
            "amount": "100.50",
            "date": "2024-01-15T10:30:00Z",
            "currency_code": "EUR",
            "merchant": "Test Merchant",
            "payee": "Test Payee",
            "note": "Test note",
            "memo": "Test memo",
            "labels": ["food", "dinner"],
            "needs_review": True,
            "closing_balance": "1000.00",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T11:30:00Z",
            "last_modified": "2024-01-15T11:30:00",
            "category": {
                "id": 1,
                "title": "Food",
                "is_income": False,
                "is_transfer": False,
                "is_bill": False,
                "colour": "#FF0000",
                "parent_id": None,
            },
            "transaction_account": {
                "id": 1,
                "name": "Checking Account",
                "type": "bank",
                "currency_code": "EUR",
                "institution": {"title": "Test Bank", "currency_code": "EUR"},
                "current_balance": "5000.00",
                "current_balance_date": "2024-01-15",
                "starting_balance": "4000.00",
                "starting_balance_date": "2024-01-01",
            },
        }

        transaction = convert_pocketsmith_to_model(pocketsmith_data)

        assert transaction.id == "123"
        assert transaction.amount == Decimal("100.50")
        assert transaction.date == date(2024, 1, 15)
        assert transaction.currency_code == "EUR"
        assert transaction.merchant == "Test Merchant"
        assert transaction.payee == "Test Payee"
        assert transaction.note == "Test note"
        assert transaction.memo == "Test memo"
        assert "dinner" in transaction.tags and "food" in transaction.tags
        assert transaction.needs_review is True
        assert transaction.closing_balance == Decimal("1000.00")
        # Timestamps include timezone info
        assert transaction.created_at.replace(tzinfo=None) == datetime(
            2024, 1, 15, 10, 30, 0
        )
        assert transaction.updated_at.replace(tzinfo=None) == datetime(
            2024, 1, 15, 11, 30, 0
        )
        assert transaction.last_modified == "2024-01-15T11:30:00"

        # Check category
        assert transaction.category is not None
        assert transaction.category["id"] == 1
        assert transaction.category["title"] == "Food"
        assert transaction.category["is_income"] is False
        assert transaction.category["colour"] == "#FF0000"

        # Check account
        assert transaction.account is not None
        assert transaction.account["id"] == 1
        assert transaction.account["name"] == "Checking Account"
        assert transaction.account["institution"]["title"] == "Test Bank"

    def test_convert_pocketsmith_with_empty_strings(self):
        """Test converting PocketSmith with empty string values."""
        pocketsmith_data = {
            "id": 123,
            "amount": "100.50",
            "date": "2024-01-15",
            "merchant": "  ",  # Whitespace only
            "payee": "",  # Empty string
            "note": "   ",
            "memo": "",
        }

        transaction = convert_pocketsmith_to_model(pocketsmith_data)

        # Empty/whitespace strings should become None
        assert transaction.merchant is None
        assert transaction.payee is None  # Falls back to merchant which is None
        assert transaction.note is None
        assert transaction.memo is None  # Falls back to note which is None

    def test_convert_pocketsmith_fallback_fields(self):
        """Test fallback behavior for related fields."""
        pocketsmith_data = {
            "id": 123,
            "amount": "100.50",
            "date": "2024-01-15",
            "merchant": "Test Merchant",
            "note": "Test note",
            # No payee or memo specified - should fallback
        }

        transaction = convert_pocketsmith_to_model(pocketsmith_data)

        assert transaction.payee == "Test Merchant"  # Falls back to merchant
        assert transaction.memo == "Test note"  # Falls back to note

    def test_convert_pocketsmith_currency_fallback(self):
        """Test currency code fallback from account."""
        pocketsmith_data = {
            "id": 123,
            "amount": "100.50",
            "date": "2024-01-15",
            # No currency_code at root level
            "transaction_account": {"currency_code": "GBP"},
        }

        transaction = convert_pocketsmith_to_model(pocketsmith_data)

        assert transaction.currency_code == "GBP"

    def test_convert_pocketsmith_labels_handling(self):
        """Test various labels input formats."""
        # Test with list
        pocketsmith_data1 = {
            "id": 123,
            "amount": "100.50",
            "date": "2024-01-15",
            "labels": ["tag1", "tag2"],
        }

        transaction1 = convert_pocketsmith_to_model(pocketsmith_data1)
        assert "tag1" in transaction1.tags and "tag2" in transaction1.tags

        # Test with single string
        pocketsmith_data2 = {
            "id": 123,
            "amount": "100.50",
            "date": "2024-01-15",
            "labels": "single_tag",
        }

        transaction2 = convert_pocketsmith_to_model(pocketsmith_data2)
        assert "single_tag" in transaction2.tags

        # Test with None/empty
        pocketsmith_data3 = {
            "id": 123,
            "amount": "100.50",
            "date": "2024-01-15",
            "labels": None,
        }

        transaction3 = convert_pocketsmith_to_model(pocketsmith_data3)
        assert transaction3.tags == []


class TestConvertPocketsmithListToModel:
    """Test converting list of PocketSmith transactions."""

    def test_convert_empty_list(self):
        """Test converting empty list."""
        result = convert_pocketsmith_list_to_model([])
        assert result == []

    def test_convert_multiple_transactions(self):
        """Test converting multiple transactions."""
        pocketsmith_transactions = [
            {"id": 123, "amount": "100.50", "date": "2024-01-15"},
            {"id": 124, "amount": "200.75", "date": "2024-01-16"},
        ]

        transactions = convert_pocketsmith_list_to_model(pocketsmith_transactions)

        assert len(transactions) == 2
        assert transactions[0].id == "123"
        assert transactions[1].id == "124"
        assert transactions[0].amount == Decimal("100.50")
        assert transactions[1].amount == Decimal("200.75")


class TestFormatCategory:
    """Test PocketSmith category formatting."""

    def test_format_full_category(self):
        """Test formatting complete category data."""
        category_data = {
            "id": 1,
            "title": "Food & Dining",
            "is_income": False,
            "is_transfer": False,
            "is_bill": True,
            "colour": "#FF0000",
            "parent_id": 10,
        }

        result = _format_category(category_data)

        assert result is not None
        assert result["id"] == 1
        assert result["title"] == "Food & Dining"
        assert result["is_income"] is False
        assert result["is_transfer"] is False
        assert result["is_bill"] is True
        assert result["colour"] == "#FF0000"
        assert result["parent_id"] == 10

    def test_format_minimal_category(self):
        """Test formatting minimal category data."""
        category_data = {"id": 1}

        result = _format_category(category_data)

        assert result is not None
        assert result["id"] == 1
        assert result["title"] == "Uncategorized"  # Default
        assert result["is_income"] is False  # Default
        assert result["is_transfer"] is False  # Default
        assert result["is_bill"] is False  # Default
        assert result["colour"] is None
        assert result["parent_id"] is None

    def test_format_none_category(self):
        """Test formatting None category."""
        result = _format_category(None)
        assert result is None

    def test_format_empty_category(self):
        """Test formatting empty category."""
        result = _format_category({})

        # Empty dict should return None
        assert result is None


class TestFormatAccount:
    """Test PocketSmith account formatting."""

    def test_format_full_account(self):
        """Test formatting complete account data."""
        account_data = {
            "id": 1,
            "name": "Primary Checking",
            "type": "bank",
            "currency_code": "USD",
            "institution": {"title": "Test Bank", "currency_code": "USD"},
            "current_balance": "5000.00",
            "current_balance_date": "2024-01-15",
            "starting_balance": "4000.00",
            "starting_balance_date": "2024-01-01",
        }

        result = _format_account(account_data)

        assert result is not None
        assert result["id"] == 1
        assert result["name"] == "Primary Checking"
        assert result["type"] == "bank"
        assert result["currency_code"] == "USD"
        assert result["institution"]["title"] == "Test Bank"
        assert result["institution"]["currency_code"] == "USD"
        assert result["current_balance"] == "5000.00"
        assert result["starting_balance"] == "4000.00"

    def test_format_minimal_account(self):
        """Test formatting minimal account data."""
        account_data = {"id": 1}

        result = _format_account(account_data)

        assert result is not None
        assert result["id"] == 1
        assert result["name"] == "Unknown"  # Default
        assert result["type"] == "bank"  # Default
        assert result["currency_code"] == "USD"  # Default
        assert result["institution"]["title"] == "Unknown"
        assert result["institution"]["currency_code"] is None

    def test_format_account_with_none_institution(self):
        """Test formatting account with None institution."""
        account_data = {"id": 1, "name": "Test Account", "institution": None}

        result = _format_account(account_data)

        assert result is not None
        assert result["institution"]["title"] == "Unknown"

    def test_format_none_account(self):
        """Test formatting None account."""
        result = _format_account(None)
        assert result is None


class TestParseDate:
    """Test PocketSmith date parsing."""

    def test_parse_date_object(self):
        """Test parsing date object."""
        test_date = date(2024, 1, 15)
        result = _parse_date(test_date)
        assert result == test_date

    def test_parse_datetime_object(self):
        """Test parsing datetime object."""
        test_datetime = datetime(2024, 1, 15, 10, 30, 0)
        result = _parse_date(test_datetime)
        # The model doesn't auto-convert datetime to date, returns as-is
        assert result == test_datetime

    def test_parse_iso_string_with_z(self):
        """Test parsing ISO string with Z suffix."""
        result = _parse_date("2024-01-15T10:30:00Z")
        assert result == date(2024, 1, 15)

    def test_parse_iso_string_without_timezone(self):
        """Test parsing ISO string without timezone."""
        result = _parse_date("2024-01-15T10:30:00")
        assert result == date(2024, 1, 15)

    def test_parse_date_only_string(self):
        """Test parsing date-only string."""
        result = _parse_date("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_parse_partial_date_string(self):
        """Test parsing string with extra characters."""
        result = _parse_date("2024-01-15T10:30:00.123Z")
        assert result == date(2024, 1, 15)

    def test_parse_none_value(self):
        """Test parsing None value falls back to today."""
        result = _parse_date(None)
        assert result == date.today()

    def test_parse_invalid_string(self):
        """Test parsing invalid string falls back to today."""
        result = _parse_date("invalid-date")
        assert result == date.today()


class TestParseTimestamp:
    """Test PocketSmith timestamp parsing."""

    def test_parse_datetime_object(self):
        """Test parsing datetime object."""
        test_datetime = datetime(2024, 1, 15, 10, 30, 0)
        result = _parse_timestamp(test_datetime)
        assert result == test_datetime

    def test_parse_iso_string_with_z(self):
        """Test parsing ISO string with Z suffix."""
        result = _parse_timestamp("2024-01-15T10:30:00Z")
        # Result includes timezone info
        assert result.replace(tzinfo=None) == datetime(2024, 1, 15, 10, 30, 0)

    def test_parse_iso_string_without_timezone(self):
        """Test parsing ISO string without timezone."""
        result = _parse_timestamp("2024-01-15T10:30:00")
        assert result == datetime(2024, 1, 15, 10, 30, 0)

    def test_parse_space_separated_format(self):
        """Test parsing space-separated datetime format."""
        result = _parse_timestamp("2024-01-15 10:30:00")
        assert result == datetime(2024, 1, 15, 10, 30, 0)

    def test_parse_none_value(self):
        """Test parsing None value."""
        result = _parse_timestamp(None)
        assert result is None

    def test_parse_invalid_string(self):
        """Test parsing invalid string."""
        result = _parse_timestamp("invalid-timestamp")
        assert result is None


class TestPropertyBasedTests:
    """Property-based tests for PocketSmith conversion."""

    @given(st.integers(min_value=1, max_value=999999))
    def test_pocketsmith_id_conversion_properties(self, transaction_id):
        """Property test: transaction ID should be preserved as string."""
        pocketsmith_data = {
            "id": transaction_id,
            "amount": "100.00",
            "date": "2024-01-15",
        }

        transaction = convert_pocketsmith_to_model(pocketsmith_data)
        assert transaction.id == str(transaction_id)

    @given(
        st.decimals(
            allow_nan=False, allow_infinity=False, min_value=-1000000, max_value=1000000
        )
    )
    def test_pocketsmith_amount_conversion_properties(self, amount):
        """Property test: amounts should be preserved as Decimals."""
        pocketsmith_data = {"id": 123, "amount": str(amount), "date": "2024-01-15"}

        transaction = convert_pocketsmith_to_model(pocketsmith_data)
        assert isinstance(transaction.amount, Decimal)
        assert transaction.amount == amount

    @given(st.dates(min_value=date(1900, 1, 1), max_value=date(2100, 12, 31)))
    def test_pocketsmith_date_conversion_properties(self, test_date):
        """Property test: dates should be preserved."""
        pocketsmith_data = {
            "id": 123,
            "amount": "100.00",
            "date": test_date.isoformat(),
        }

        transaction = convert_pocketsmith_to_model(pocketsmith_data)
        assert transaction.date == test_date

    @given(st.text(min_size=0, max_size=100))
    def test_pocketsmith_text_field_properties(self, text_value):
        """Property test: text fields should handle various inputs."""
        pocketsmith_data = {
            "id": 123,
            "amount": "100.00",
            "date": "2024-01-15",
            "merchant": text_value,
            "note": text_value,
        }

        transaction = convert_pocketsmith_to_model(pocketsmith_data)

        # Should handle empty/whitespace text appropriately
        if text_value.strip():
            assert transaction.merchant == text_value.strip()  # Model strips whitespace
            assert transaction.note == text_value.strip()
        else:
            assert transaction.merchant is None
            assert transaction.note is None

    @given(
        st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.integers(min_value=1, max_value=999999),
                    "amount": st.just("100.00"),
                    "date": st.just("2024-01-15"),
                }
            ),
            min_size=0,
            max_size=10,
        )
    )
    def test_pocketsmith_list_conversion_properties(self, pocketsmith_list):
        """Property test: list conversion should preserve length and order."""
        transactions = convert_pocketsmith_list_to_model(pocketsmith_list)

        assert len(transactions) == len(pocketsmith_list)

        for i, (original, converted) in enumerate(zip(pocketsmith_list, transactions)):
            assert converted.id == str(original["id"])
            assert isinstance(converted, Transaction)
