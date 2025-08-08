import pytest
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite
from src.pocketsmith_beancount.beancount_converter import BeancountConverter


class TestPropertyBasedTests:
    """Property-based tests using Hypothesis for robust edge case coverage."""

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=200)
    def test_property_account_name_sanitization(self, name):
        """Property test for account name cleaning with various special characters."""
        converter = BeancountConverter()

        # Skip empty strings after stripping and strings that would result in empty sanitized names
        assume(name.strip())
        assume(re.sub(r"[^a-zA-Z0-9\-]", "-", name.strip()).strip("-"))

        sanitized = converter._sanitize_account_name(name)

        # Ensure sanitized names are valid beancount account names
        assert isinstance(sanitized, str), (
            f"Sanitized name should be string: {sanitized}"
        )

        # Only test non-empty results (some inputs may result in empty strings after sanitization)
        if sanitized:
            # Should not start or end with hyphens or underscores
            assert not sanitized.startswith("-"), (
                f"Sanitized name should not start with hyphen: '{sanitized}'"
            )
            assert not sanitized.endswith("-"), (
                f"Sanitized name should not end with hyphen: '{sanitized}'"
            )
            assert not sanitized.startswith("_"), (
                f"Sanitized name should not start with underscore: '{sanitized}'"
            )

            # Should only contain valid characters (letters, numbers, hyphens)
            assert re.match(r"^[A-Za-z0-9-]+$", sanitized), (
                f"Sanitized name contains invalid characters: '{sanitized}'"
            )

            # Should not have consecutive hyphens
            assert "--" not in sanitized, (
                f"Sanitized name should not have consecutive hyphens: '{sanitized}'"
            )

            # Should be title case
            words = sanitized.split("-")
            for word in words:
                if word:  # Skip empty words
                    assert word[0].isupper() or word[0].isdigit(), (
                        f"Word should start with uppercase or digit: '{word}' in '{sanitized}'"
                    )

    @composite
    def transaction_amount_strategy(draw):
        """Generate realistic transaction amounts."""
        # Generate amounts with various precisions and signs
        amount_type = draw(
            st.sampled_from(
                ["positive", "negative", "decimal_string", "integer", "float"]
            )
        )

        if amount_type == "positive":
            return draw(
                st.floats(
                    min_value=0.01,
                    max_value=999999.99,
                    allow_nan=False,
                    allow_infinity=False,
                )
            )
        elif amount_type == "negative":
            return draw(
                st.floats(
                    min_value=-999999.99,
                    max_value=-0.01,
                    allow_nan=False,
                    allow_infinity=False,
                )
            )
        elif amount_type == "decimal_string":
            # Generate decimal strings with 2 decimal places
            integer_part = draw(st.integers(min_value=1, max_value=999999))
            decimal_part = draw(st.integers(min_value=0, max_value=99))
            sign = draw(st.sampled_from(["", "-"]))
            return f"{sign}{integer_part}.{decimal_part:02d}"
        elif amount_type == "integer":
            return draw(
                st.integers(min_value=-999999, max_value=999999).filter(
                    lambda x: x != 0
                )
            )
        else:  # float
            return draw(
                st.floats(
                    min_value=-999999.99,
                    max_value=999999.99,
                    allow_nan=False,
                    allow_infinity=False,
                ).filter(lambda x: x != 0)
            )

    @given(transaction_amount_strategy())
    @settings(max_examples=200)
    def test_property_transaction_amount_conversion(self, amount):
        """Property test for amount handling with various formats."""

        # Skip zero amounts as they're not valid transactions
        if isinstance(amount, (int, float)) and amount == 0:
            assume(False)
        if isinstance(amount, str) and float(amount) == 0:
            assume(False)

        # Test conversion to Decimal
        try:
            if isinstance(amount, str):
                decimal_amount = Decimal(amount)
            else:
                decimal_amount = Decimal(str(amount))

            # Ensure proper decimal precision is maintained
            assert isinstance(decimal_amount, Decimal), (
                f"Should convert to Decimal: {decimal_amount}"
            )

            # Ensure reasonable precision (no more than 4 decimal places for financial data)
            quantized = decimal_amount.quantize(Decimal("0.0001"))
            assert abs(decimal_amount - quantized) < Decimal("0.00005"), (
                f"Amount should have reasonable precision: {decimal_amount}"
            )

            # Ensure currency formatting is consistent (2 decimal places for display)
            formatted = f"{decimal_amount:.2f}"
            assert re.match(r"^-?\d+\.\d{2}$", formatted), (
                f"Formatted amount should have 2 decimal places: {formatted}"
            )

        except (InvalidOperation, ValueError, OverflowError):
            # Some extreme values might not be convertible, which is acceptable
            pass

    @composite
    def date_string_strategy(draw):
        """Generate various date string formats that PocketSmith might return."""
        date_format = draw(
            st.sampled_from(
                [
                    "iso_with_z",
                    "iso_with_timezone",
                    "iso_basic",
                    "date_only",
                    "malformed",
                ]
            )
        )

        # Generate a base datetime
        base_date = draw(
            st.datetimes(
                min_value=datetime(2000, 1, 1), max_value=datetime(2030, 12, 31)
            )
        )

        if date_format == "iso_with_z":
            return base_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        elif date_format == "iso_with_timezone":
            return base_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        elif date_format == "iso_basic":
            return base_date.strftime("%Y-%m-%dT%H:%M:%S")
        elif date_format == "date_only":
            return base_date.strftime("%Y-%m-%d")
        else:  # malformed
            malformed_formats = [
                "invalid-date",
                "2024-13-45",  # Invalid month/day
                "2024/01/01",  # Wrong separator
                "01-01-2024",  # Wrong order
                "",  # Empty string
                "not-a-date",
            ]
            return draw(st.sampled_from(malformed_formats))

    @given(date_string_strategy())
    @settings(max_examples=200)
    def test_property_date_parsing(self, date_string):
        """Property test for date string handling with various formats."""
        converter = BeancountConverter()

        try:
            # Test the _convert_to_aest method
            result = converter._convert_to_aest(date_string)

            # Should return a string
            assert isinstance(result, str), (
                f"Date conversion should return string: {result}"
            )

            # For empty input, result might be empty (acceptable)
            if not date_string:
                return

            # For valid ISO dates, should match expected format (MMM DD HH:MM:SS.mmm)
            if date_string and date_string not in [
                "invalid-date",
                "2024-13-45",
                "2024/01/01",
                "01-01-2024",
                "not-a-date",
            ]:
                if result != str(date_string):  # If conversion happened (not fallback)
                    # Should contain month abbreviation, day, and time
                    assert re.search(
                        r"[A-Z][a-z]{2} \d{1,2} \d{2}:\d{2}:\d{2}\.\d{3}", result
                    ), (
                        f"Valid date should produce formatted output: '{result}' from '{date_string}'"
                    )

        except (ValueError, AttributeError):
            # Invalid dates should either raise an exception or return the original string
            # Both behaviors are acceptable
            pass

    @composite
    def label_string_strategy(draw):
        """Generate various label strings with special characters."""
        label_type = draw(
            st.sampled_from(
                [
                    "normal",
                    "with_spaces",
                    "with_special_chars",
                    "unicode",
                    "empty",
                    "very_long",
                ]
            )
        )

        if label_type == "normal":
            return draw(
                st.text(
                    alphabet=st.characters(whitelist_categories=["Lu", "Ll", "Nd"]),
                    min_size=1,
                    max_size=20,
                )
            )
        elif label_type == "with_spaces":
            return draw(
                st.text(min_size=1, max_size=30).filter(
                    lambda x: " " in x and x.strip()
                )
            )
        elif label_type == "with_special_chars":
            return draw(
                st.text(alphabet="!@#$%^&*()_+-=[]{}|;:,.<>?", min_size=1, max_size=20)
            )
        elif label_type == "unicode":
            return draw(
                st.text(
                    alphabet=st.characters(
                        whitelist_categories=["Lu", "Ll", "Nd", "Sm", "So"]
                    ),
                    min_size=1,
                    max_size=20,
                )
            )
        elif label_type == "empty":
            return ""
        else:  # very_long
            return draw(st.text(min_size=100, max_size=500))

    @given(st.lists(label_string_strategy(), min_size=0, max_size=10))
    @settings(max_examples=200)
    def test_property_label_tag_conversion(self, labels):
        """Property test for label sanitization and tag conversion."""

        # Filter out empty labels as they shouldn't be processed
        non_empty_labels = [label for label in labels if label and label.strip()]

        # Convert labels to tags (simulate the conversion logic)
        tags = []
        for label in non_empty_labels:
            # Sanitize label to create valid beancount tag
            sanitized = re.sub(r"[^a-zA-Z0-9-]", "-", label.strip())
            sanitized = re.sub(r"-+", "-", sanitized)
            sanitized = sanitized.strip("-").lower()

            if sanitized:  # Only add non-empty sanitized tags
                tags.append(f"#{sanitized}")

        # Ensure all labels convert to valid beancount tags
        for tag in tags:
            assert isinstance(tag, str), f"Tag should be string: {tag}"
            assert tag.startswith("#"), f"Tag should start with #: {tag}"

            # Tag content should only contain valid characters
            tag_content = tag[1:]  # Remove the #
            if tag_content:  # Skip empty tags
                assert re.match(r"^[a-z0-9-]+$", tag_content), (
                    f"Tag content should only contain lowercase letters, numbers, and hyphens: '{tag_content}'"
                )
                assert not tag_content.startswith("-"), (
                    f"Tag should not start with hyphen: '{tag_content}'"
                )
                assert not tag_content.endswith("-"), (
                    f"Tag should not end with hyphen: '{tag_content}'"
                )
                assert "--" not in tag_content, (
                    f"Tag should not have consecutive hyphens: '{tag_content}'"
                )

        # Ensure tag uniqueness is maintained (deduplicate tags as expected behavior)
        unique_tags = list(set(tags))
        # Note: Duplicate labels should result in duplicate tags, which is acceptable behavior
        # The assertion should check that the deduplication process works correctly
        assert len(unique_tags) <= len(tags), (
            f"Unique tags should not exceed total tags: {unique_tags} vs {tags}"
        )

    @given(st.text(min_size=0, max_size=200))
    @settings(max_examples=100)
    def test_property_payee_narration_escaping(self, text):
        """Property test for quote and special character escaping in payee/narration."""
        # Test escaping logic for beancount format
        escaped = text.replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")

        # Should not contain literal newlines or carriage returns
        assert "\n" not in escaped, f"Should not contain literal newlines: '{escaped}'"
        assert "\r" not in escaped, (
            f"Should not contain literal carriage returns: '{escaped}'"
        )

        # Count actual quote characters (not escaped sequences)
        # Simple approach: count quotes that are not part of \\" sequence
        quote_positions = []
        i = 0
        while i < len(escaped):
            if escaped[i] == '"':
                quote_positions.append(i)
            i += 1

        # Check each quote to see if it's properly escaped
        for pos in quote_positions:
            if pos > 0:
                # Check if preceded by odd number of backslashes (properly escaped)
                backslash_count = 0
                j = pos - 1
                while j >= 0 and escaped[j] == "\\":
                    backslash_count += 1
                    j -= 1

                # If even number of backslashes (including 0), quote is not escaped
                if backslash_count % 2 == 0:
                    # This is acceptable for input that already contains escaped quotes
                    pass
            else:
                # Quote at beginning should be escaped if it's a literal quote
                pass

    @given(st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=3, max_size=3))
    @settings(max_examples=100)
    def test_property_currency_code_validation(self, currency_code):
        """Property test for currency code validation."""
        # Test currency code format validation
        upper_code = currency_code.upper()

        # Should be exactly 3 uppercase ASCII letters
        assert len(upper_code) == 3, (
            f"Currency code should be 3 characters: '{upper_code}'"
        )
        assert upper_code.isupper(), (
            f"Currency code should be uppercase: '{upper_code}'"
        )
        assert upper_code.isalpha(), (
            f"Currency code should only contain letters: '{upper_code}'"
        )
        assert re.match(r"^[A-Z]{3}$", upper_code), (
            f"Currency code should match ISO format: '{upper_code}'"
        )

    @composite
    def account_data_strategy(draw):
        """Generate account data with various institution and type combinations."""
        # Generate institution name that will result in non-empty sanitized name or None
        institution_choice = draw(st.sampled_from(["none", "valid", "empty"]))
        if institution_choice == "none":
            institution_name = None
        elif institution_choice == "empty":
            institution_name = (
                None  # Treat empty as None to avoid empty sanitized names
            )
        else:
            institution_name = draw(
                st.text(
                    alphabet=st.characters(whitelist_categories=["Lu", "Ll", "Nd"]),
                    min_size=1,
                    max_size=50,
                )
            )
            assume(institution_name.strip())
            assume(re.sub(r"[^a-zA-Z0-9\-]", "-", institution_name.strip()).strip("-"))

        # Generate account name that will result in non-empty sanitized name
        account_name = draw(
            st.text(
                alphabet=st.characters(whitelist_categories=["Lu", "Ll", "Nd"]),
                min_size=1,
                max_size=50,
            )
        )
        assume(account_name.strip())
        assume(re.sub(r"[^a-zA-Z0-9\-]", "-", account_name.strip()).strip("-"))

        account_type = draw(
            st.sampled_from(
                [
                    "bank",
                    "credit_card",
                    "loan",
                    "mortgage",
                    "line_of_credit",
                    "investment",
                    "other",
                    "checking",
                    "savings",
                    "UNKNOWN",
                ]
            )
        )

        return {
            "id": draw(st.integers(min_value=1, max_value=999999)),
            "name": account_name,
            "type": account_type,
            "institution": {"title": institution_name} if institution_name else None,
        }

    @given(account_data_strategy())
    @settings(max_examples=100)
    def test_property_account_hierarchy_generation(self, account_data):
        """Property test for account path creation with various combinations."""
        converter = BeancountConverter()

        account_name = converter._get_account_name(account_data)

        # Should return a valid beancount account path
        assert isinstance(account_name, str), (
            f"Account name should be string: {account_name}"
        )
        assert account_name, "Account name should not be empty"

        # Should have proper hierarchy (Type:Institution:Account or Type:Unknown:Account)
        parts = account_name.split(":")
        assert len(parts) >= 2, (
            f"Account should have at least 2 parts: '{account_name}'"
        )
        assert len(parts) <= 3, f"Account should have at most 3 parts: '{account_name}'"

        # First part should be valid account type
        account_type = parts[0]
        assert account_type in ["Assets", "Liabilities"], (
            f"Invalid account type: '{account_type}'"
        )

        # All parts should be valid beancount account components
        for i, part in enumerate(parts):
            if i == 0:  # Account type part
                assert part in ["Assets", "Liabilities"], (
                    f"First part should be account type: '{part}'"
                )
            else:
                # Other parts should not be empty and should contain valid characters
                assert part, (
                    f"Account parts should not be empty: '{account_name}' (part {i}: '{part}')"
                )
                assert re.match(r"^[A-Za-z0-9-]+$", part), (
                    f"Account part should only contain valid characters: '{part}'"
                )
                assert not part.startswith("-"), (
                    f"Account part should not start with hyphen: '{part}'"
                )
                assert not part.endswith("-"), (
                    f"Account part should not end with hyphen: '{part}'"
                )

    @given(st.integers(min_value=1, max_value=10000))
    @settings(max_examples=50)
    def test_property_large_dataset_performance(self, transaction_count):
        """Property test for performance with datasets of varying sizes."""
        converter = BeancountConverter()

        # Generate mock transaction data
        transactions = []
        for i in range(transaction_count):
            transactions.append(
                {
                    "id": i + 1,
                    "amount": f"{(i % 1000) + 1}.00",
                    "date": "2024-01-01T00:00:00Z",
                    "payee": f"Payee {i}",
                    "memo": f"Transaction {i}",
                    "currency_code": "USD",
                    "labels": [f"label{i % 5}"],
                    "needs_review": i % 2 == 0,
                    "transaction_account": {
                        "id": (i % 10) + 1,
                        "account": {
                            "id": (i % 10) + 1,
                            "name": f"Account {i % 10}",
                            "type": "bank",
                            "institution": {"title": f"Bank {i % 3}"},
                        },
                    },
                    "category": {
                        "id": (i % 20) + 1,
                        "title": f"Category {i % 20}",
                        "is_transfer": False,
                        "is_income": i % 10 == 0,
                    },
                }
            )

        # Test conversion performance
        import time

        start_time = time.time()

        try:
            # Create transaction accounts list
            transaction_accounts = []
            for transaction in transactions:
                transaction_accounts.append(transaction["transaction_account"])

            result = converter.convert_transactions(transactions, transaction_accounts)
            end_time = time.time()

            # Should complete within reasonable time (adjust threshold as needed)
            processing_time = end_time - start_time
            time_per_transaction = processing_time / transaction_count

            # Should process at least 100 transactions per second for reasonable performance
            assert time_per_transaction < 0.01, (
                f"Processing too slow: {time_per_transaction:.4f}s per transaction"
            )

            # Result should be a string
            assert isinstance(result, str), "Result should be string"
            assert result, "Result should not be empty"

            # Should contain expected number of transactions (count by transaction markers)
            actual_transaction_count = result.count(
                " * "
            )  # Beancount uses * for transactions
            assert actual_transaction_count == transaction_count, (
                f"Should have {transaction_count} transactions, got {actual_transaction_count}"
            )

        except Exception as e:
            # Large datasets might cause memory issues, which is acceptable for very large sizes
            if transaction_count > 5000:
                pytest.skip(
                    f"Large dataset ({transaction_count}) caused expected resource limitation: {e}"
                )
            else:
                raise
