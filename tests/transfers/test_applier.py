"""Tests for transfer applier to ensure all transaction details are preserved."""

import pytest
from decimal import Decimal
from datetime import date
from pathlib import Path
import tempfile
import textwrap

from beancount.core import data as bc_data
from beancount.core.amount import Amount

from src.transfers.applier import TransferApplier
from src.transfers.models import DetectionResult, TransferPair


class TestTransferApplierPreservation:
    """Test that transfer applier preserves all transaction details."""

    def test_format_entry_preserves_all_metadata(self):
        """Test that _format_entry_as_text preserves all metadata fields."""
        applier = TransferApplier(transfer_category_id=24918120)

        # Create a transaction with comprehensive metadata
        entry = bc_data.Transaction(
            meta={
                "id": Decimal("123456789"),
                "last_modified": "Nov 27 12:34:56.000",
                "closing_balance": Decimal("1234.56"),
                "is_transfer": "true",
                "paired": Decimal("987654321"),
                "custom_field": "custom_value",
                "filename": "/path/to/file.beancount",  # Should be skipped
                "lineno": 42,  # Should be skipped
            },
            date=date(2025, 11, 27),
            flag="*",
            payee="Test Payee",
            narration="Test Narration",
            tags=frozenset(["loans", "test"]),
            links=frozenset(["link1", "link2"]),
            postings=[
                bc_data.Posting(
                    account="Expenses:Transfer",
                    units=Amount(Decimal("100.50"), "AUD"),
                    cost=None,
                    price=None,
                    flag=None,
                    meta={},
                ),
                bc_data.Posting(
                    account="Assets:Bank:Account",
                    units=Amount(Decimal("-100.50"), "AUD"),
                    cost=None,
                    price=None,
                    flag=None,
                    meta={},
                ),
            ],
        )

        result = applier._format_entry_as_text(entry)

        # Check header with payee, narration, tags, and links
        assert '2025-11-27 * "Test Payee" "Test Narration"' in result
        assert "#loans" in result
        assert "#test" in result
        assert "^link1" in result
        assert "^link2" in result

        # Check all metadata is preserved
        assert "id: 123456789" in result
        assert 'last_modified: "Nov 27 12:34:56.000"' in result
        assert "closing_balance: 1234.56" in result
        assert 'is_transfer: "true"' in result
        assert "paired: 987654321" in result
        assert 'custom_field: "custom_value"' in result

        # Check internal fields are skipped
        assert "filename:" not in result
        assert "lineno:" not in result

        # Check postings
        assert "Expenses:Transfer" in result
        assert "Assets:Bank:Account" in result
        assert "100.50 AUD" in result
        assert "-100.50 AUD" in result

    def test_format_entry_aligns_decimal_points(self):
        """Test that amounts are aligned by decimal point."""
        applier = TransferApplier(transfer_category_id=24918120)

        entry = bc_data.Transaction(
            meta={"id": Decimal("123")},
            date=date(2025, 11, 27),
            flag="*",
            payee="Test",
            narration="",
            tags=frozenset(),
            links=frozenset(),
            postings=[
                bc_data.Posting(
                    account="Expenses:Transfer",
                    units=Amount(Decimal("844.0"), "AUD"),
                    cost=None,
                    price=None,
                    flag=None,
                    meta={},
                ),
                bc_data.Posting(
                    account="Assets:Commonwealth-Bank-Cba:Offset",
                    units=Amount(Decimal("-844.0"), "AUD"),
                    cost=None,
                    price=None,
                    flag=None,
                    meta={},
                ),
            ],
        )

        result = applier._format_entry_as_text(entry)
        lines = result.split("\n")

        # Find the posting lines
        posting_lines = [line for line in lines if line.startswith("  ")]

        # Extract the amount parts (should be aligned)
        amounts = []
        for line in posting_lines:
            # Find where the amount starts (look for digits after spaces)
            parts = line.split()
            if len(parts) >= 3:  # account, amount, currency
                # Get the position of the decimal point or last digit before currency
                amount_str = parts[-2]  # Second to last is the amount
                amounts.append(amount_str)

        # Both amounts should have the decimal in the same position when rendered
        assert "844.0" in amounts[0]
        assert "-844.0" in amounts[1]

        # Check that the decimal points align by finding their positions in the lines
        decimal_positions = []
        for line in posting_lines:
            if "." in line:
                # Find position of decimal point
                decimal_positions.append(line.index("."))

        # All decimal points should be at the same position
        assert len(set(decimal_positions)) == 1, "Decimal points should align"

    def test_format_entry_with_different_length_amounts(self):
        """Test decimal alignment with amounts of different lengths."""
        applier = TransferApplier(transfer_category_id=24918120)

        entry = bc_data.Transaction(
            meta={"id": Decimal("123")},
            date=date(2025, 11, 27),
            flag="*",
            payee="Test",
            narration="",
            tags=frozenset(),
            links=frozenset(),
            postings=[
                bc_data.Posting(
                    account="Expenses:Transfer",
                    units=Amount(Decimal("5.50"), "AUD"),
                    cost=None,
                    price=None,
                    flag=None,
                    meta={},
                ),
                bc_data.Posting(
                    account="Assets:Bank:Account",
                    units=Amount(Decimal("-12345.67"), "AUD"),
                    cost=None,
                    price=None,
                    flag=None,
                    meta={},
                ),
            ],
        )

        result = applier._format_entry_as_text(entry)
        lines = result.split("\n")

        posting_lines = [line for line in lines if line.startswith("  ")]

        # Check that decimal points align
        decimal_positions = []
        for line in posting_lines:
            if "." in line:
                decimal_positions.append(line.index("."))

        assert len(set(decimal_positions)) == 1, "Decimal points should align"

        # The shorter amount should be right-padded to align
        # "    5.50 AUD" should have leading spaces before the 5
        assert "5.50 AUD" in result
        assert "-12345.67 AUD" in result

    def test_format_entry_preserves_empty_narration(self):
        """Test that empty narration is preserved as empty string."""
        applier = TransferApplier(transfer_category_id=24918120)

        entry = bc_data.Transaction(
            meta={"id": Decimal("123")},
            date=date(2025, 11, 27),
            flag="*",
            payee="Test Payee",
            narration="",  # Empty narration
            tags=frozenset(),
            links=frozenset(),
            postings=[],
        )

        result = applier._format_entry_as_text(entry)
        assert '2025-11-27 * "Test Payee" ""' in result

    def test_format_entry_preserves_tags_order(self):
        """Test that tags are sorted for consistency."""
        applier = TransferApplier(transfer_category_id=24918120)

        entry = bc_data.Transaction(
            meta={"id": Decimal("123")},
            date=date(2025, 11, 27),
            flag="*",
            payee="Test",
            narration="",
            tags=frozenset(["zzz", "aaa", "mmm"]),  # Unsorted
            links=frozenset(),
            postings=[],
        )

        result = applier._format_entry_as_text(entry)

        # Tags should appear in sorted order
        tag_line = [line for line in result.split("\n") if "#" in line][0]
        assert tag_line.index("#aaa") < tag_line.index("#mmm")
        assert tag_line.index("#mmm") < tag_line.index("#zzz")

    def test_format_entry_preserves_all_real_world_details(self):
        """Test formatting with a real-world beancount transaction entry."""
        applier = TransferApplier(transfer_category_id=24918120)

        # Create a realistic transaction from finance-vault
        entry = bc_data.Transaction(
            meta={
                "id": Decimal("302704761"),
                "last_modified": "Aug 03 23:56:32.000",
                "closing_balance": Decimal("1050.09"),
                "is_transfer": "true",
                "paired": Decimal("302705431"),
                "filename": "/path/file.beancount",  # Should be skipped
                "lineno": 100,  # Should be skipped
            },
            date=date(2020, 11, 3),
            flag="*",
            payee="Loan Repayment LN REPAY 559037066",
            narration="",
            tags=frozenset(["loans"]),
            links=frozenset(),
            postings=[
                bc_data.Posting(
                    account="Expenses:Transfer",
                    units=Amount(Decimal("844.0"), "AUD"),
                    cost=None,
                    price=None,
                    flag=None,
                    meta={},
                ),
                bc_data.Posting(
                    account="Assets:Commonwealth-Bank-Cba:Offset",
                    units=Amount(Decimal("-844.0"), "AUD"),
                    cost=None,
                    price=None,
                    flag=None,
                    meta={},
                ),
            ],
        )

        result = applier._format_entry_as_text(entry)

        # Verify exact format matches expected output
        expected_lines = [
            '2020-11-03 * "Loan Repayment LN REPAY 559037066" "" #loans',
            "    id: 302704761",
            '    last_modified: "Aug 03 23:56:32.000"',
            "    closing_balance: 1050.09",
            '    is_transfer: "true"',
            "    paired: 302705431",
            "  Expenses:Transfer                     844.0 AUD",
            "  Assets:Commonwealth-Bank-Cba:Offset  -844.0 AUD",
        ]

        result_lines = result.split("\n")

        # Check each expected line is present
        for expected in expected_lines:
            assert expected in result_lines, f"Expected line not found: {expected}"

        # Verify decimal alignment - both decimals should be at same position
        posting_lines = [line for line in result_lines if line.startswith("  ") and "AUD" in line]
        assert len(posting_lines) == 2, "Should have 2 posting lines"

        decimal_positions = [line.index(".") for line in posting_lines]
        assert len(set(decimal_positions)) == 1, f"Decimal points must align, got positions: {decimal_positions}"

    def test_metadata_ordering(self):
        """Test that metadata fields appear in the correct order."""
        applier = TransferApplier(transfer_category_id=24918120)

        entry = bc_data.Transaction(
            meta={
                "paired": Decimal("987"),  # Should come after standard fields
                "last_modified": "Nov 27 12:34:56.000",
                "id": Decimal("123"),
                "closing_balance": Decimal("100.0"),
                "is_transfer": "true",
                "custom_field": "value",  # Should come at the end
            },
            date=date(2025, 11, 27),
            flag="*",
            payee="Test",
            narration="",
            tags=frozenset(),
            links=frozenset(),
            postings=[],
        )

        result = applier._format_entry_as_text(entry)
        lines = result.split("\n")

        # Find metadata lines (those starting with 4 spaces)
        meta_lines = [line.strip() for line in lines if line.startswith("    ")]

        # Check ordering
        expected_order = [
            "id:",
            "last_modified:",
            "closing_balance:",
            "is_transfer:",
            "paired:",
            "custom_field:",
        ]

        for i, expected_field in enumerate(expected_order):
            # Find the line with this field
            matching_lines = [line for line in meta_lines if line.startswith(expected_field)]
            if matching_lines:
                actual_index = meta_lines.index(matching_lines[0])
                # Check that it appears in order (allowing for missing fields)
                assert (
                    actual_index >= i
                ), f"{expected_field} appears out of order"
