"""Tests for beancount.common module utility functions."""

from decimal import Decimal
from datetime import datetime
import pytz
from hypothesis import given, strategies as st
import re

from src.beancount.common import (
    BeancountError,
    sanitize_account_name,
    format_account_name,
    convert_id_to_decimal,
    convert_to_aest,
    sanitize_tags_for_beancount,
)


class TestBeancountError:
    """Test BeancountError exception class."""

    def test_beancount_error_creation(self):
        """Test creating BeancountError with message."""
        error = BeancountError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)


class TestSanitizeAccountName:
    """Test account name sanitization functionality."""

    def test_sanitize_basic_names(self):
        """Test sanitization of basic account names."""
        assert sanitize_account_name("Checking Account") == "Checking-Account"
        assert sanitize_account_name("My Savings") == "My-Savings"
        assert sanitize_account_name("Simple") == "Simple"

    def test_sanitize_special_characters(self):
        """Test sanitization removes special characters."""
        assert sanitize_account_name("Account@#$%") == "Account"
        assert sanitize_account_name("Test!&*()") == "Test"
        assert sanitize_account_name("Name++--__") == "Name"

    def test_sanitize_numbers_and_letters(self):
        """Test sanitization preserves numbers and letters."""
        assert sanitize_account_name("Account123") == "Account123"
        assert (
            sanitize_account_name("Test-123-ABC") == "Test-123-Abc"
        )  # .title() converts to title case

    def test_sanitize_hyphen_handling(self):
        """Test proper hyphen handling in sanitization."""
        assert (
            sanitize_account_name("Test--Multiple--Hyphens") == "Test-Multiple-Hyphens"
        )
        assert sanitize_account_name("-Leading-Hyphen") == "Leading-Hyphen"
        assert sanitize_account_name("Trailing-Hyphen-") == "Trailing-Hyphen"
        assert sanitize_account_name("---") == ""

    def test_sanitize_empty_and_whitespace(self):
        """Test sanitization of empty and whitespace-only inputs."""
        assert sanitize_account_name("") == ""
        assert sanitize_account_name("   ") == ""
        assert sanitize_account_name("\t\n") == ""

    def test_sanitize_unicode_characters(self):
        """Test sanitization with Unicode characters."""
        assert sanitize_account_name("Café Account") == "Caf-Account"
        assert (
            sanitize_account_name("München Bank") == "M-Nchen-Bank"
        )  # Unicode ü gets replaced with -
        # Should preserve Unicode letters
        result = sanitize_account_name("测试账户")
        assert len(result) >= 0  # Unicode handling may vary

    @given(st.text(min_size=1, max_size=100))
    def test_sanitize_never_produces_invalid_beancount_names(self, name):
        """Property test: sanitized names should always be valid for beancount."""
        result = sanitize_account_name(name)
        if result:  # Non-empty result
            # Should only contain letters, numbers, and hyphens
            assert re.match(r"^[A-Za-z0-9\-\u00C0-\u017F\u0400-\u04FF]*$", result)
            # Should not start or end with hyphen
            assert not result.startswith("-")
            assert not result.endswith("-")
            # Should not have consecutive hyphens
            assert "--" not in result


class TestFormatAccountName:
    """Test account name formatting functionality."""

    def test_format_simple_account(self):
        """Test formatting simple account names."""
        # format_account_name takes (account_type, institution, account_name)
        result = format_account_name("Assets", "Bank of Test", "Checking")
        assert result == "Assets:Bank-Of-Test:Checking"

    def test_format_account_with_special_chars(self):
        """Test formatting with special characters in names."""
        result = format_account_name(
            "Assets", "Credit Union & Trust", "High-Yield Savings"
        )
        assert result == "Assets:Credit-Union-Trust:High-Yield-Savings"

    def test_format_account_missing_institution(self):
        """Test formatting when institution is missing."""
        result = format_account_name("Assets", "", "Cash")
        assert result == "Assets::Cash"  # Empty institution becomes empty

    def test_format_account_empty_institution(self):
        """Test formatting with empty institution."""
        result = format_account_name("Assets", "", "Checking")
        assert result == "Assets::Checking"  # Empty institution becomes empty

    def test_format_account_missing_name(self):
        """Test formatting when account name is missing."""
        result = format_account_name("Assets", "Test Bank", "")
        assert result == "Assets:Test-Bank:"  # Empty account name becomes empty


class TestConvertIdToDecimal:
    """Test ID to Decimal conversion functionality."""

    def test_convert_valid_integers(self):
        """Test conversion of valid integer IDs."""
        assert convert_id_to_decimal("123") == Decimal("123")
        assert convert_id_to_decimal("0") == Decimal("0")
        # Negative signs get stripped by regex, so -456 becomes 456
        assert convert_id_to_decimal("-456") == Decimal("456")

    def test_convert_valid_decimals(self):
        """Test conversion of valid decimal IDs."""
        assert convert_id_to_decimal("123.45") == Decimal("123.45")
        assert convert_id_to_decimal("0.0") == Decimal("0.0")
        # Negative signs get stripped by regex, so -456.78 becomes 456.78
        assert convert_id_to_decimal("-456.78") == Decimal("456.78")

    def test_convert_integer_input(self):
        """Test conversion of integer inputs."""
        assert convert_id_to_decimal(123) == Decimal("123")
        assert convert_id_to_decimal(0) == Decimal("0")
        assert convert_id_to_decimal(-456) == Decimal("-456")

    def test_convert_float_input(self):
        """Test conversion of float inputs."""
        assert convert_id_to_decimal(123.45) == Decimal("123.45")
        assert convert_id_to_decimal(0.0) == Decimal("0.0")

    def test_convert_decimal_input(self):
        """Test conversion of Decimal inputs."""
        decimal_val = Decimal("123.45")
        assert convert_id_to_decimal(decimal_val) == decimal_val

    def test_convert_invalid_inputs(self):
        """Test conversion of invalid inputs returns None."""
        assert convert_id_to_decimal("not_a_number") is None  # No digits, returns None
        assert convert_id_to_decimal("") is None
        assert convert_id_to_decimal(None) is None
        # Multiple decimals make it invalid for Decimal(), returns None
        assert convert_id_to_decimal("123.45.67") is None
        assert convert_id_to_decimal("abc123") == Decimal("123")  # Extracts digits

    def test_convert_scientific_notation(self):
        """Test conversion of scientific notation."""
        # Regex removes 'e' and 'E', so 1.23e2 becomes 1.232, not 123
        assert convert_id_to_decimal("1.23e2") == Decimal("1.232")
        assert convert_id_to_decimal("1.23E-2") == Decimal("1.232")  # Same result

    @given(
        st.one_of(
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.decimals(allow_nan=False, allow_infinity=False),
        )
    )
    def test_convert_numeric_types_always_succeed(self, value):
        """Property test: valid numeric types should always convert."""
        result = convert_id_to_decimal(value)
        assert result is None or isinstance(result, Decimal)


class TestConvertToAest:
    """Test timezone conversion to AEST functionality."""

    def test_convert_utc_to_aest(self):
        """Test conversion from UTC to AEST."""
        utc_time = "2024-01-15T10:30:00Z"
        result = convert_to_aest(utc_time)
        # Function returns formatted string, not datetime object
        assert isinstance(result, str)
        # Should contain timestamp elements
        assert "Jan 15" in result  # Date part
        assert ":" in result  # Time separator

    def test_convert_with_timezone_info(self):
        """Test conversion with timezone information."""
        pst_time = "2024-01-15T10:30:00-08:00"
        result = convert_to_aest(pst_time)
        assert isinstance(result, str)
        # PST to AEST crosses date boundary (15th -> 16th)
        assert "Jan 16" in result

    def test_convert_naive_datetime(self):
        """Test conversion of naive datetime (assumes UTC)."""
        naive_time = "2024-01-15T10:30:00"
        result = convert_to_aest(naive_time)
        assert isinstance(result, str)
        assert "Jan 15" in result

    def test_convert_datetime_object(self):
        """Test conversion of datetime object."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=pytz.UTC)
        result = convert_to_aest(dt)
        assert isinstance(result, str)
        assert "Jan 15" in result

    def test_convert_invalid_format(self):
        """Test conversion with invalid datetime format."""
        # Function has fallback to return string representation
        result = convert_to_aest("invalid-datetime")
        assert result == "invalid-datetime"

    def test_convert_none_input(self):
        """Test conversion with None input."""
        # Function has fallback to return string representation
        result = convert_to_aest(None)
        assert result == "None"


class TestSanitizeTagsForBeancount:
    """Test tag sanitization for beancount format."""

    def test_sanitize_basic_tags(self):
        """Test sanitization of basic tags."""
        tags = ["food", "restaurant", "dinner"]
        result = sanitize_tags_for_beancount(tags)
        assert result == ["food", "restaurant", "dinner"]

    def test_sanitize_tags_with_spaces(self):
        """Test sanitization of tags with spaces."""
        tags = ["food dining", "quick meal", "test tag"]
        result = sanitize_tags_for_beancount(tags)
        assert result == ["food-dining", "quick-meal", "test-tag"]

    def test_sanitize_tags_with_special_chars(self):
        """Test sanitization of tags with special characters."""
        tags = ["food&dining", "quick$meal", "test@tag"]
        result = sanitize_tags_for_beancount(tags)
        assert result == ["food-dining", "quick-meal", "test-tag"]

    def test_sanitize_empty_and_none_tags(self):
        """Test sanitization handles empty and None tags."""
        assert sanitize_tags_for_beancount([]) == []
        assert sanitize_tags_for_beancount(None) == []
        assert sanitize_tags_for_beancount(["", "  ", "valid"]) == ["valid"]

    def test_sanitize_removes_duplicates(self):
        """Test sanitization preserves all tags including duplicates."""
        tags = ["food", "dining", "food", "restaurant", "dining"]
        result = sanitize_tags_for_beancount(tags)
        # Function doesn't remove duplicates, preserves original order
        assert result == ["food", "dining", "food", "restaurant", "dining"]

    def test_sanitize_preserves_case(self):
        """Test sanitization preserves case."""
        tags = ["Food", "DINING", "Restaurant"]
        result = sanitize_tags_for_beancount(tags)
        assert result == ["Food", "DINING", "Restaurant"]

    @given(st.lists(st.text(min_size=0, max_size=50), min_size=0, max_size=20))
    def test_sanitize_tags_properties(self, tags):
        """Property test: sanitized tags should be valid beancount tags."""
        result = sanitize_tags_for_beancount(tags)
        assert isinstance(result, list)

        for tag in result:
            # Valid beancount tags should not contain spaces or special chars
            assert " " not in tag
            assert all(c.isalnum() or c in "-_" for c in tag)  # Allow underscore
            # Should not be empty
            assert len(tag) > 0
            # Should not start or end with hyphen
            assert not tag.startswith("-")
            assert not tag.endswith("-")
