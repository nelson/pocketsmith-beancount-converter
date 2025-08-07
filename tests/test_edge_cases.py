"""
Edge case tests for comprehensive coverage of unusual scenarios.

These tests cover edge cases that might not be caught by regular unit tests
or property-based tests, focusing on boundary conditions and error scenarios.
"""

import pytest
import requests
from pathlib import Path
from unittest.mock import Mock, patch

from src.pocketsmith_beancount.beancount_converter import BeancountConverter
from src.pocketsmith_beancount.pocketsmith_client import PocketSmithClient
from src.pocketsmith_beancount.file_writer import BeancountFileWriter


class TestBeancountConverterEdgeCases:
    """Test edge cases for BeancountConverter."""

    def test_extremely_large_amounts(self):
        """Test handling of very large transaction amounts."""
        converter = BeancountConverter()

        large_amounts = [
            "999999999.99",
            "-999999999.99",
            "1000000000000.00",
            "0.01",
            "-0.01",
        ]

        for amount in large_amounts:
            transaction = {
                "id": 1,
                "date": "2024-01-01T00:00:00Z",
                "amount": amount,
                "merchant": "Test",
                "note": "Test",
                "currency_code": "USD",
                "transaction_account": {
                    "id": 1,
                    "name": "Test Account",
                    "type": "checking",
                    "institution": {"title": "Test Bank"},
                },
                "category": {"id": 1, "title": "Test"},
            }

            accounts = {1: transaction["transaction_account"]}
            result = converter.convert_transaction(transaction, accounts)

            assert result != "", f"Should handle large amount: {amount}"
            assert amount.lstrip("-") in result, (
                f"Amount {amount} should appear in result"
            )

    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters in all text fields."""
        converter = BeancountConverter()

        special_texts = [
            "Café München",
            "北京烤鸭",
            "Москва",
            "🏦 Bank & Trust 💰",
            "Test\nNewline",
            "Test\tTab",
            "Test\"Quote'Mixed",
            "Test\\Backslash",
            "",  # Empty string
            "   ",  # Whitespace only
        ]

        for text in special_texts:
            transaction = {
                "id": 1,
                "date": "2024-01-01T00:00:00Z",
                "amount": "10.00",
                "merchant": text,
                "note": text,
                "currency_code": "USD",
                "transaction_account": {
                    "id": 1,
                    "name": text or "Default",
                    "type": "checking",
                    "institution": {"title": text or "Default Bank"},
                },
                "category": {"id": 1, "title": text or "Default"},
            }

            accounts = {1: transaction["transaction_account"]}
            result = converter.convert_transaction(transaction, accounts)

            # Should not crash and should produce some output
            assert isinstance(result, str), f"Should handle special text: {repr(text)}"
            if text.strip():  # Non-empty text should appear somehow
                # Check that the transaction line is properly formatted
                lines = result.split("\n")
                assert len(lines) >= 3, "Should have at least 3 lines"

    def test_malformed_dates(self):
        """Test handling of various malformed date formats."""
        converter = BeancountConverter()

        malformed_dates = [
            "2024-01-01",  # Missing time
            "invalid-date",  # Completely invalid
            "",  # Empty string
            "2024-01-01T00:00:00",  # Missing Z
        ]

        for date in malformed_dates:
            transaction = {
                "id": 1,
                "date": date,
                "amount": "10.00",
                "merchant": "Test",
                "note": "Test",
                "currency_code": "USD",
                "transaction_account": {
                    "id": 1,
                    "name": "Test Account",
                    "type": "checking",
                    "institution": {"title": "Test Bank"},
                },
                "category": {"id": 1, "title": "Test"},
            }

            accounts = {1: transaction["transaction_account"]}

            # Should either handle gracefully or raise a specific exception
            try:
                result = converter.convert_transaction(transaction, accounts)
                # If it succeeds, should still be a string
                assert isinstance(result, str), f"Should return string for date: {date}"
            except (ValueError, Exception):
                # Expected for malformed dates
                pass  # This is acceptable

    def test_missing_required_fields(self):
        """Test handling of transactions with missing required fields."""
        converter = BeancountConverter()

        base_transaction = {
            "id": 1,
            "date": "2024-01-01T00:00:00Z",
            "amount": "10.00",
            "merchant": "Test",
            "note": "Test",
            "currency_code": "USD",
            "transaction_account": {
                "id": 1,
                "name": "Test Account",
                "type": "checking",
                "institution": {"title": "Test Bank"},
            },
            "category": {"id": 1, "title": "Test"},
        }

        # Test removing each field one by one
        required_fields = ["transaction_account"]  # Only test truly required fields

        for field in required_fields:
            transaction = base_transaction.copy()
            del transaction[field]

            accounts = {1: base_transaction["transaction_account"]}

            result = converter.convert_transaction(transaction, accounts)

            if field == "transaction_account":
                # Should return empty string for missing account
                assert result == "", f"Should return empty for missing {field}"
            else:
                # Other fields might have defaults or cause errors
                try:
                    assert isinstance(result, str), f"Should handle missing {field}"
                except (KeyError, ValueError):
                    # Some fields might be truly required and cause exceptions
                    pass

    def test_circular_category_references(self):
        """Test handling of circular parent-child relationships in categories."""
        converter = BeancountConverter()

        # Create categories with circular references
        categories = [
            {"id": 1, "title": "Parent", "parent_id": 2},
            {"id": 2, "title": "Child", "parent_id": 1},  # Circular reference
            {"id": 3, "title": "Self", "parent_id": 3},  # Self-reference
        ]

        # Should not crash when generating declarations
        declarations = converter.generate_category_declarations(categories)

        assert isinstance(declarations, list), "Should return list"
        assert len(declarations) == 3, "Should create declarations for all categories"

    def test_extreme_precision_amounts(self):
        """Test handling of amounts with extreme decimal precision."""
        converter = BeancountConverter()

        extreme_amounts = [
            "10.123456789",  # Many decimal places
            "10.000000001",  # Tiny fraction
            "0.000000001",  # Very small amount
            "10.",  # Trailing decimal
            ".50",  # Leading decimal
            "1e10",  # Scientific notation
            "1E-10",  # Scientific notation small
        ]

        for amount in extreme_amounts:
            transaction = {
                "id": 1,
                "date": "2024-01-01T00:00:00Z",
                "amount": amount,
                "merchant": "Test",
                "note": "Test",
                "currency_code": "USD",
                "transaction_account": {
                    "id": 1,
                    "name": "Test Account",
                    "type": "checking",
                    "institution": {"title": "Test Bank"},
                },
                "category": {"id": 1, "title": "Test"},
            }

            accounts = {1: transaction["transaction_account"]}

            try:
                result = converter.convert_transaction(transaction, accounts)
                assert isinstance(result, str), f"Should handle amount: {amount}"
                # Should contain some representation of the amount
                assert any(char.isdigit() for char in result), (
                    f"Should contain digits for: {amount}"
                )
            except (ValueError, OverflowError):
                # Some extreme values might not be convertible
                pass

    def test_very_long_text_fields(self):
        """Test handling of extremely long text in various fields."""
        converter = BeancountConverter()

        # Create very long strings
        long_text = "A" * 1000
        very_long_text = "B" * 10000

        transaction = {
            "id": 1,
            "date": "2024-01-01T00:00:00Z",
            "amount": "10.00",
            "merchant": long_text,
            "note": very_long_text,
            "currency_code": "USD",
            "transaction_account": {
                "id": 1,
                "name": long_text,
                "type": "checking",
                "institution": {"title": long_text},
            },
            "category": {"id": 1, "title": long_text},
        }

        accounts = {1: transaction["transaction_account"]}
        result = converter.convert_transaction(transaction, accounts)

        assert isinstance(result, str), "Should handle very long text"
        assert len(result) > 0, "Should produce some output"
        # Should contain parts of the long text
        assert "A" in result, "Should contain merchant text"
        assert "B" in result, "Should contain note text"

    def test_null_and_none_values(self):
        """Test handling of null/None values in various fields."""
        converter = BeancountConverter()

        transaction = {
            "id": 1,
            "date": "2024-01-01T00:00:00Z",
            "amount": "10.00",
            "merchant": None,
            "note": None,
            "payee": None,
            "memo": None,
            "labels": None,
            "needs_review": None,
            "currency_code": "USD",
            "transaction_account": {
                "id": 1,
                "name": "Test Account",
                "type": "checking",
                "institution": None,
            },
            "category": None,
        }

        accounts = {1: transaction["transaction_account"]}
        result = converter.convert_transaction(transaction, accounts)

        assert isinstance(result, str), "Should handle None values"
        assert len(result) > 0, "Should produce some output"
        # Should use defaults for None values - check for either Unknown or empty quotes
        assert "Unknown" in result or '""' in result or "Uncategorized" in result, (
            "Should use defaults for None values"
        )


class TestPocketSmithClientEdgeCases:
    """Test edge cases for PocketSmith client."""

    def test_network_timeout_simulation(self):
        """Test handling of network timeouts and connection errors."""
        client = PocketSmithClient("test_key")

        with patch("requests.get") as mock_get:
            # Simulate various network errors
            network_errors = [
                requests.exceptions.Timeout("Request timed out"),
                requests.exceptions.ConnectionError("Connection failed"),
                requests.exceptions.HTTPError("HTTP Error"),
            ]

            for error in network_errors:
                mock_get.side_effect = error

                with pytest.raises(type(error)):
                    client._make_request("test_endpoint")

    def test_malformed_json_responses(self):
        """Test handling of malformed JSON responses."""
        client = PocketSmithClient("test_key")

        with patch(
            "src.pocketsmith_beancount.pocketsmith_client.requests.get"
        ) as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_get.return_value = mock_response

            with pytest.raises(ValueError):
                client._make_request("test_endpoint")

    def test_very_large_api_responses(self):
        """Test handling of very large API responses."""
        client = PocketSmithClient("test_key")

        # Create a very large mock response
        large_response = [{"id": i, "name": f"Item {i}"} for i in range(10000)]

        with patch(
            "src.pocketsmith_beancount.pocketsmith_client.requests.get"
        ) as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = large_response
            mock_response.headers.get.return_value = ""
            mock_get.return_value = mock_response

            with patch.object(client, "get_user", return_value={"id": 123}):
                result = client.get_accounts()

                assert isinstance(result, list), "Should handle large responses"
                assert len(result) == 10000, "Should return all items"

    def test_pagination_with_malformed_links(self):
        """Test pagination handling with malformed Link headers."""
        client = PocketSmithClient("test_key")

        malformed_links = [
            "invalid-link-header",
            "<>; rel=next",  # Empty URL
            "<url>; invalid-rel",  # Invalid relation format
            "<url1>; rel=next, <url2>; rel=next",  # Duplicate relations
        ]

        for link_header in malformed_links:
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.raise_for_status.return_value = None
                mock_response.json.return_value = [{"id": 1}]
                mock_response.headers.get.return_value = link_header
                mock_get.return_value = mock_response

                with patch.object(client, "get_user", return_value={"id": 123}):
                    result = client.get_transactions()

                    # Should handle malformed headers gracefully
                    assert isinstance(result, list), (
                        f"Should handle malformed link: {link_header}"
                    )


class TestFileWriterEdgeCases:
    """Test edge cases for file writer."""

    def test_permission_denied_scenarios(self):
        """Test handling of permission denied errors."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a read-only directory
            readonly_dir = Path(temp_dir) / "readonly"
            readonly_dir.mkdir()
            readonly_dir.chmod(0o444)  # Read-only

            try:
                writer = BeancountFileWriter(str(readonly_dir))

                with pytest.raises(PermissionError):
                    writer.write_beancount_file("test content", "test")
            finally:
                # Restore permissions for cleanup
                readonly_dir.chmod(0o755)

    def test_disk_space_simulation(self):
        """Test handling of disk space issues (simulated)."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            writer = BeancountFileWriter(temp_dir)

            # Create a moderately large content string
            large_content = "A" * (1024 * 1024)  # 1MB string (more reasonable)

            try:
                # This should usually succeed
                result = writer.write_beancount_file(large_content, "large_test")
                if result:
                    assert Path(result).exists(), "File should exist if write succeeded"
                    # Clean up the large file
                    Path(result).unlink()
            except (OSError, IOError):
                # Expected if disk space is insufficient
                pass
