"""Tests for text-based beancount file updating with preservation."""

import tempfile
from pathlib import Path

from src.beancount.update import update_monthly_file_preserving_format


def test_update_preserves_comments_and_formatting():
    """Test that updating a transaction preserves all formatting."""
    original_content = """; Header comment
; Generated on some date

; First transaction - important note!
2025-01-15 * "Store A" "Groceries shopping"
    id: 1001
    Assets:Bank:Checking  -50.00 AUD
    Expenses:Groceries  50.00 AUD

; Second transaction
2025-01-16 ! "Store B" "More shopping"
    id: 1002
    ; Internal comment
    Assets:Bank:Checking  -30.00 AUD
    Expenses:Groceries  30.00 AUD

; Final transaction
2025-01-17 * "Store C" "Final shopping"
    id: 1003
    Assets:Bank:Checking  -20.00 AUD
    Expenses:Groceries  20.00 AUD
"""

    # Create temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".beancount", delete=False) as f:
        temp_path = Path(f.name)
        f.write(original_content)

    try:
        # Update transaction 1002 (middle one)
        updated_txn = {
            "id": 1002,
            "date": "2025-01-16",
            "payee": "Store B Updated",
            "note": "Updated shopping",
            "merchant": "Store B Updated",
            "amount": -35.00,  # Changed amount
            "currency_code": "AUD",
            "needs_review": False,  # Changed flag
            "transaction_account": {
                "name": "Checking",
                "currency_code": "AUD",
                "institution": {"title": "Bank"},
            },
            "category": {
                "title": "Groceries",
                "is_income": False,
                "is_transfer": False,
            },
        }

        update_monthly_file_preserving_format(temp_path, [updated_txn], 2025, 1)

        # Read result
        with open(temp_path, "r") as f:
            result = f.read()

        # Verify preservations
        assert "; Header comment" in result, "Header comment should be preserved"
        assert "; Generated on some date" in result, "Comment line preserved"
        assert "; First transaction - important note!" in result, (
            "Transaction comment preserved"
        )
        assert "; Second transaction" in result, "Second transaction comment preserved"
        assert "; Final transaction" in result, "Final transaction comment preserved"

        # Verify update happened
        assert "Store B Updated" in result, "Transaction should be updated"
        assert "35.0 AUD" in result or "35.00 AUD" in result, "Amount should be updated"
        assert '2025-01-16 * "Store B Updated"' in result, "Flag should be updated"

        # Verify order maintained
        lines = result.split("\n")
        store_a_line = next(
            i for i, line_text in enumerate(lines) if "Store A" in line_text
        )
        store_b_line = next(
            i for i, line_text in enumerate(lines) if "Store B Updated" in line_text
        )
        store_c_line = next(
            i for i, line_text in enumerate(lines) if "Store C" in line_text
        )
        assert store_a_line < store_b_line < store_c_line, "Order should be preserved"

    finally:
        temp_path.unlink()


def test_insert_new_transaction_in_chronological_order():
    """Test that new transactions are inserted in correct chronological position."""
    original_content = """; Monthly transactions

2025-01-10 * "Early" "Early transaction"
    id: 1001
    Assets:Bank:Checking  -10.00 AUD
    Expenses:Groceries  10.00 AUD

2025-01-20 * "Late" "Late transaction"
    id: 1003
    Assets:Bank:Checking  -30.00 AUD
    Expenses:Groceries  30.00 AUD
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".beancount", delete=False) as f:
        temp_path = Path(f.name)
        f.write(original_content)

    try:
        # Insert transaction dated 2025-01-15 (should go between the two)
        new_txn = {
            "id": 1002,
            "date": "2025-01-15T10:00:00Z",
            "payee": "Middle",
            "note": "Middle transaction",
            "merchant": "Middle",
            "amount": -20.00,
            "currency_code": "AUD",
            "transaction_account": {
                "name": "Checking",
                "currency_code": "AUD",
                "institution": {"title": "Bank"},
            },
            "category": {
                "title": "Groceries",
                "is_income": False,
                "is_transfer": False,
            },
        }

        update_monthly_file_preserving_format(temp_path, [new_txn], 2025, 1)

        with open(temp_path, "r") as f:
            result = f.read()

        # Verify insertion
        assert "Middle transaction" in result, "New transaction should be inserted"

        # Verify chronological order
        lines = result.split("\n")
        early_line = next(
            i for i, line_text in enumerate(lines) if "Early" in line_text
        )
        middle_line = next(
            i for i, line_text in enumerate(lines) if "Middle" in line_text
        )
        late_line = next(i for i, line_text in enumerate(lines) if "Late" in line_text)
        assert early_line < middle_line < late_line, "Should be in chronological order"

        # Verify original comments preserved
        assert "; Monthly transactions" in result

    finally:
        temp_path.unlink()


def test_append_recent_transaction_at_end():
    """Test that recent transactions are appended at the end."""
    original_content = """2025-01-10 * "First" "First transaction"
    id: 1001
    Assets:Bank:Checking  -10.00 AUD
    Expenses:Groceries  10.00 AUD
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".beancount", delete=False) as f:
        temp_path = Path(f.name)
        f.write(original_content)

    try:
        # Add later transaction
        new_txn = {
            "id": 1002,
            "date": "2025-01-25T10:00:00Z",
            "payee": "Recent",
            "note": "Recent transaction",
            "merchant": "Recent",
            "amount": -20.00,
            "currency_code": "AUD",
            "transaction_account": {
                "name": "Checking",
                "currency_code": "AUD",
                "institution": {"title": "Bank"},
            },
            "category": {
                "title": "Groceries",
                "is_income": False,
                "is_transfer": False,
            },
        }

        update_monthly_file_preserving_format(temp_path, [new_txn], 2025, 1)

        with open(temp_path, "r") as f:
            result = f.read()

        # Verify appended
        assert "Recent transaction" in result

        # Verify order
        lines = result.split("\n")
        first_line = next(
            i for i, line_text in enumerate(lines) if "First" in line_text
        )
        recent_line = next(
            i for i, line_text in enumerate(lines) if "Recent" in line_text
        )
        assert first_line < recent_line, "Recent should be after first"

    finally:
        temp_path.unlink()


def test_mixed_update_and_insert():
    """Test updating existing and inserting new transactions together."""
    original_content = """2025-01-10 * "First" "First transaction"
    id: 1001
    Assets:Bank:Checking  -10.00 AUD
    Expenses:Groceries  10.00 AUD

2025-01-20 * "Second" "Second transaction"
    id: 1002
    Assets:Bank:Checking  -20.00 AUD
    Expenses:Groceries  20.00 AUD
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".beancount", delete=False) as f:
        temp_path = Path(f.name)
        f.write(original_content)

    try:
        # Update 1001 and insert new 1003
        updated_txn = {
            "id": 1001,
            "date": "2025-01-10",
            "payee": "First Updated",
            "note": "Updated first",
            "merchant": "First Updated",
            "amount": -15.00,
            "currency_code": "AUD",
            "transaction_account": {
                "name": "Checking",
                "currency_code": "AUD",
                "institution": {"title": "Bank"},
            },
            "category": {
                "title": "Groceries",
                "is_income": False,
                "is_transfer": False,
            },
        }

        new_txn = {
            "id": 1003,
            "date": "2025-01-15T10:00:00Z",
            "payee": "New Middle",
            "note": "New middle transaction",
            "merchant": "New Middle",
            "amount": -25.00,
            "currency_code": "AUD",
            "transaction_account": {
                "name": "Checking",
                "currency_code": "AUD",
                "institution": {"title": "Bank"},
            },
            "category": {
                "title": "Groceries",
                "is_income": False,
                "is_transfer": False,
            },
        }

        update_monthly_file_preserving_format(
            temp_path, [updated_txn, new_txn], 2025, 1
        )

        with open(temp_path, "r") as f:
            result = f.read()

        # Verify both operations
        assert "First Updated" in result, "Transaction should be updated"
        assert "15.0 AUD" in result or "15.00 AUD" in result, "Amount should be updated"
        assert "New middle transaction" in result, "New transaction should be inserted"

        # Verify order
        lines = result.split("\n")
        first_line = next(
            i for i, line_text in enumerate(lines) if "First Updated" in line_text
        )
        new_line = next(
            i for i, line_text in enumerate(lines) if "New Middle" in line_text
        )
        second_line = next(
            i for i, line_text in enumerate(lines) if "Second" in line_text
        )
        assert first_line < new_line < second_line, (
            "Should maintain chronological order"
        )

    finally:
        temp_path.unlink()
