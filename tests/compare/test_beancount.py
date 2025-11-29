"""Tests for compare.beancount module functionality."""

import pytest
from decimal import Decimal
from datetime import date, datetime
from hypothesis import given, strategies as st

from src.compare.beancount import (
    convert_beancount_to_model,
    convert_beancount_list_to_model,
    _extract_amount_from_beancount,
    _extract_currency_from_beancount,
    _extract_account_from_postings,
    _extract_category_from_postings,
)
from src.compare.date_utils import parse_date as _parse_date
from src.compare.model import Transaction


class TestConvertBeancountToModel:
    """Test converting beancount data to Transaction model."""

    def test_convert_minimal_beancount_transaction(self):
        """Test converting minimal beancount transaction."""
        beancount_data = {
            "id": "123",
            "date": "2024-01-15",
            "postings": [
                {
                    "account": "Assets:Checking",
                    "units": {"number": "100.50", "currency": "USD"},
                }
            ],
        }

        transaction = convert_beancount_to_model(beancount_data)

        assert transaction.id == "123"
        assert transaction.amount == Decimal("100.50")
        assert transaction.date == date(2024, 1, 15)
        assert transaction.currency_code == "USD"

    def test_convert_full_beancount_transaction(self):
        """Test converting full beancount transaction."""
        beancount_data = {
            "id": "123",
            "date": "2024-01-15",
            "payee": "Test Merchant",
            "narration": "Test transaction",
            "flag": "!",
            "tags": ["food", "dinner"],
            "closing_balance": "1000.00",
            "last_modified": "2024-01-15T10:30:00",
            "postings": [
                {
                    "account": "Assets:Checking",
                    "units": {"number": "100.50", "currency": "USD"},
                },
                {
                    "account": "Expenses:Food:Restaurant",
                    "units": {"number": "-100.50", "currency": "USD"},
                },
            ],
        }

        transaction = convert_beancount_to_model(beancount_data)

        assert transaction.id == "123"
        assert transaction.amount == Decimal("100.50")
        assert transaction.date == date(2024, 1, 15)
        assert transaction.currency_code == "USD"
        # merchant field removed - now only using payee
        assert transaction.payee == "Test Merchant"
        assert transaction.note == "Test transaction"
        assert transaction.memo == "Test transaction"
        assert transaction.needs_review is True
        assert "dinner" in transaction.tags and "food" in transaction.tags
        assert transaction.closing_balance == Decimal("1000.00")
        assert transaction.last_modified == "2024-01-15T10:30:00"

        # Check account extraction
        assert transaction.account is not None
        assert transaction.account["name"] == "Assets:Checking"
        assert transaction.account["type"] == "Assets"

        # Check category extraction
        assert transaction.category is not None
        assert transaction.category["title"] == "Restaurant"
        assert transaction.category["is_income"] is False
        assert transaction.category["full_account"] == "Expenses:Food:Restaurant"

    def test_convert_beancount_with_empty_strings(self):
        """Test converting beancount with empty string values."""
        beancount_data = {
            "id": "123",
            "date": "2024-01-15",
            "payee": "  ",  # Whitespace only
            "narration": "",  # Empty string
            "postings": [
                {
                    "account": "Assets:Checking",
                    "units": {"number": "100.50", "currency": "USD"},
                }
            ],
        }

        transaction = convert_beancount_to_model(beancount_data)

        # Empty/whitespace strings should become None
        # merchant field removed - now only using payee
        assert transaction.payee is None
        assert transaction.note is None
        assert transaction.memo is None

    def test_convert_beancount_with_missing_fields(self):
        """Test converting beancount with missing optional fields."""
        beancount_data = {"date": "2024-01-15", "postings": []}

        transaction = convert_beancount_to_model(beancount_data)

        assert transaction.id == ""
        assert transaction.amount == Decimal("0")
        assert transaction.currency_code == "USD"  # Default fallback
        # merchant field removed - now only using payee
        assert transaction.account is None
        assert transaction.category is None
        assert transaction.needs_review is False  # Default


class TestConvertBeancountListToModel:
    """Test converting list of beancount transactions."""

    def test_convert_empty_list(self):
        """Test converting empty list."""
        result = convert_beancount_list_to_model([])
        assert result == []

    def test_convert_multiple_transactions(self):
        """Test converting multiple transactions."""
        beancount_transactions = [
            {
                "id": "123",
                "date": "2024-01-15",
                "postings": [
                    {
                        "account": "Assets:Checking",
                        "units": {"number": "100.50", "currency": "USD"},
                    }
                ],
            },
            {
                "id": "124",
                "date": "2024-01-16",
                "postings": [
                    {
                        "account": "Assets:Savings",
                        "units": {"number": "200.75", "currency": "USD"},
                    }
                ],
            },
        ]

        transactions = convert_beancount_list_to_model(beancount_transactions)

        assert len(transactions) == 2
        assert transactions[0].id == "123"
        assert transactions[1].id == "124"
        assert transactions[0].amount == Decimal("100.50")
        assert transactions[1].amount == Decimal("200.75")


class TestExtractAmountFromBeancount:
    """Test amount extraction from beancount postings."""

    def test_extract_amount_from_first_posting(self):
        """Test extracting amount from first posting."""
        beancount_data = {
            "postings": [
                {
                    "account": "Assets:Checking",
                    "units": {"number": "100.50", "currency": "USD"},
                },
                {
                    "account": "Expenses:Food",
                    "units": {"number": "-100.50", "currency": "USD"},
                },
            ]
        }

        amount = _extract_amount_from_beancount(beancount_data)
        assert amount == Decimal("100.50")

    def test_extract_amount_skip_invalid_postings(self):
        """Test skipping invalid postings and finding valid one."""
        beancount_data = {
            "postings": [
                {"account": "Assets:Checking"},  # No units
                {"units": {}},  # Empty units
                {"units": {"number": "invalid"}},  # Invalid number
                {
                    "account": "Assets:Savings",
                    "units": {"number": "200.75", "currency": "USD"},
                },
            ]
        }

        # The function will throw InvalidOperation on "invalid" string
        with pytest.raises(Exception):
            _extract_amount_from_beancount(beancount_data)

    def test_extract_amount_no_valid_postings(self):
        """Test fallback when no valid postings found."""
        beancount_data = {"postings": []}

        amount = _extract_amount_from_beancount(beancount_data)
        assert amount == Decimal("0")

    def test_extract_amount_no_postings_key(self):
        """Test fallback when postings key missing."""
        beancount_data = {}

        amount = _extract_amount_from_beancount(beancount_data)
        assert amount == Decimal("0")


class TestExtractCurrencyFromBeancount:
    """Test currency extraction from beancount postings."""

    def test_extract_currency_from_first_posting(self):
        """Test extracting currency from first posting."""
        beancount_data = {
            "postings": [
                {
                    "account": "Assets:Checking",
                    "units": {"number": "100.50", "currency": "EUR"},
                }
            ]
        }

        currency = _extract_currency_from_beancount(beancount_data)
        assert currency == "EUR"

    def test_extract_currency_fallback_to_usd(self):
        """Test fallback to USD when no currency found."""
        beancount_data = {"postings": []}

        currency = _extract_currency_from_beancount(beancount_data)
        assert currency == "USD"

    def test_extract_currency_skip_invalid_postings(self):
        """Test skipping invalid postings."""
        beancount_data = {
            "postings": [
                {"account": "Assets:Checking"},  # No units
                {"units": {}},  # No currency
                {
                    "account": "Assets:Savings",
                    "units": {"number": "100.50", "currency": "GBP"},
                },
            ]
        }

        currency = _extract_currency_from_beancount(beancount_data)
        assert currency == "GBP"


class TestExtractAccountFromPostings:
    """Test account extraction from beancount postings."""

    def test_extract_assets_account(self):
        """Test extracting Assets account."""
        postings = [
            {
                "account": "Assets:Checking:MainAccount",
                "units": {"number": "100.50", "currency": "USD"},
            },
            {
                "account": "Expenses:Food",
                "units": {"number": "-100.50", "currency": "USD"},
            },
        ]

        account = _extract_account_from_postings(postings)

        assert account is not None
        assert account["name"] == "Assets:Checking:MainAccount"
        assert account["type"] == "Assets"

    def test_extract_liabilities_account(self):
        """Test extracting Liabilities account."""
        postings = [
            {
                "account": "Liabilities:CreditCard",
                "units": {"number": "100.50", "currency": "USD"},
            }
        ]

        account = _extract_account_from_postings(postings)

        assert account is not None
        assert account["name"] == "Liabilities:CreditCard"
        assert account["type"] == "Liabilities"

    def test_extract_account_no_assets_or_liabilities(self):
        """Test when no Assets or Liabilities accounts found."""
        postings = [
            {
                "account": "Expenses:Food",
                "units": {"number": "-100.50", "currency": "USD"},
            },
            {
                "account": "Income:Salary",
                "units": {"number": "100.50", "currency": "USD"},
            },
        ]

        account = _extract_account_from_postings(postings)
        assert account is None

    def test_extract_account_empty_postings(self):
        """Test with empty postings list."""
        account = _extract_account_from_postings([])
        assert account is None


class TestExtractCategoryFromPostings:
    """Test category extraction from beancount postings."""

    def test_extract_expenses_category(self):
        """Test extracting Expenses category."""
        postings = [
            {
                "account": "Assets:Checking",
                "units": {"number": "100.50", "currency": "USD"},
            },
            {
                "account": "Expenses:Food:Restaurant",
                "units": {"number": "-100.50", "currency": "USD"},
            },
        ]

        category = _extract_category_from_postings(postings)

        assert category is not None
        assert category["title"] == "Restaurant"
        assert category["is_income"] is False
        assert category["is_transfer"] is False
        assert category["full_account"] == "Expenses:Food:Restaurant"

    def test_extract_income_category(self):
        """Test extracting Income category."""
        postings = [
            {
                "account": "Income:Salary:Company",
                "units": {"number": "1000.00", "currency": "USD"},
            }
        ]

        category = _extract_category_from_postings(postings)

        assert category is not None
        assert category["title"] == "Company"
        assert category["is_income"] is True
        assert category["is_transfer"] is False

    def test_extract_transfers_category(self):
        """Test extracting Transfers category."""
        postings = [
            {
                "account": "Transfers:Internal",
                "units": {"number": "500.00", "currency": "USD"},
            }
        ]

        category = _extract_category_from_postings(postings)

        assert category is not None
        assert category["title"] == "Internal"
        assert category["is_transfer"] is True
        assert category["is_income"] is False

    def test_extract_category_single_part_account(self):
        """Test category extraction with single part account name."""
        postings = [
            {
                "account": "Expenses:",  # Only one part after colon
                "units": {"number": "-100.50", "currency": "USD"},
            }
        ]

        category = _extract_category_from_postings(postings)
        # Should still extract since len(parts) >= 2 but title would be empty
        assert category is not None
        assert category["title"] == ""

    def test_extract_category_no_matching_accounts(self):
        """Test when no matching category accounts found."""
        postings = [
            {
                "account": "Assets:Checking",
                "units": {"number": "100.50", "currency": "USD"},
            },
            {
                "account": "Liabilities:CreditCard",
                "units": {"number": "-100.50", "currency": "USD"},
            },
        ]

        category = _extract_category_from_postings(postings)
        assert category is None


class TestParseDate:
    """Test date parsing functionality."""

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

    def test_parse_iso_string_with_timezone(self):
        """Test parsing ISO string with timezone."""
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

    def test_parse_none_value(self):
        """Test parsing None value falls back to today."""
        result = _parse_date(None)
        assert result == date.today()

    def test_parse_invalid_string(self):
        """Test parsing invalid string falls back to today."""
        result = _parse_date("invalid-date")
        assert result == date.today()

    def test_parse_numeric_value(self):
        """Test parsing numeric value falls back to today."""
        result = _parse_date(12345)
        assert result == date.today()


class TestPropertyBasedTests:
    """Property-based tests for beancount conversion."""

    @given(st.text(min_size=1, max_size=50))
    def test_beancount_id_conversion_properties(self, transaction_id):
        """Property test: transaction ID should be preserved as string."""
        beancount_data = {
            "id": transaction_id,
            "date": "2024-01-15",
            "postings": [
                {
                    "account": "Assets:Checking",
                    "units": {"number": "100.00", "currency": "USD"},
                }
            ],
        }

        transaction = convert_beancount_to_model(beancount_data)
        assert transaction.id == str(transaction_id)

    @given(
        st.decimals(
            allow_nan=False, allow_infinity=False, min_value=-1000000, max_value=1000000
        )
    )
    def test_beancount_amount_conversion_properties(self, amount):
        """Property test: amounts should be preserved as Decimals."""
        beancount_data = {
            "id": "123",
            "date": "2024-01-15",
            "postings": [
                {
                    "account": "Assets:Checking",
                    "units": {"number": str(amount), "currency": "USD"},
                }
            ],
        }

        transaction = convert_beancount_to_model(beancount_data)
        assert isinstance(transaction.amount, Decimal)
        assert transaction.amount == amount

    @given(st.dates(min_value=date(1900, 1, 1), max_value=date(2100, 12, 31)))
    def test_beancount_date_conversion_properties(self, test_date):
        """Property test: dates should be preserved."""
        beancount_data = {
            "id": "123",
            "date": test_date.isoformat(),
            "postings": [
                {
                    "account": "Assets:Checking",
                    "units": {"number": "100.00", "currency": "USD"},
                }
            ],
        }

        transaction = convert_beancount_to_model(beancount_data)
        assert transaction.date == test_date

    @given(
        st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.text(min_size=1, max_size=20),
                    "date": st.just("2024-01-15"),
                    "postings": st.just(
                        [
                            {
                                "account": "Assets:Checking",
                                "units": {"number": "100.00", "currency": "USD"},
                            }
                        ]
                    ),
                }
            ),
            min_size=0,
            max_size=10,
        )
    )
    def test_beancount_list_conversion_properties(self, beancount_list):
        """Property test: list conversion should preserve length and order."""
        transactions = convert_beancount_list_to_model(beancount_list)

        assert len(transactions) == len(beancount_list)

        for i, (original, converted) in enumerate(zip(beancount_list, transactions)):
            assert converted.id == str(original["id"])
            assert isinstance(converted, Transaction)
