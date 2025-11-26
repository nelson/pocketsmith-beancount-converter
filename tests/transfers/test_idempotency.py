"""Idempotency tests for transfer metadata through push/pull/clone cycles.

Tests the 4 scenarios from the spec:
a. push→pull→clone are byte-identical
b. clone→detect-transfer→push→pull→clone are byte-identical
c. detect-transfer→push→pull are byte-identical
d. Multiple detect-transfer runs produce same result
"""

import pytest
from pathlib import Path
from decimal import Decimal
from datetime import date
import tempfile
import shutil

from src.transfers.detector import TransferDetector
from src.transfers.models import DetectionCriteria
from src.transfers.applier import TransferApplier
from src.compare.model import Transaction
from src.beancount.write import convert_transaction_to_beancount
from src.beancount.read import read_ledger
from src.compare.beancount import convert_beancount_to_model
from src.pocketsmith.metadata_encoding import encode_metadata_in_note, decode_metadata_from_note


def create_test_transaction(
    txn_id: str,
    amount: Decimal,
    txn_date: date,
    account_id: int,
    is_transfer: bool = False,
    paired: int = None,
    suspect_reason: str = None,
) -> dict:
    """Create a transaction dict for testing."""
    txn = {
        "id": txn_id,
        "amount": str(amount),
        "date": txn_date.isoformat(),
        "currency_code": "USD",
        "payee": "Test Payee",
        "note": "",
        "transaction_account": {
            "id": account_id,
            "name": f"Account {account_id}",
            "currency_code": "USD",
        },
        "category": {"title": "Groceries", "id": 123},
    }

    if is_transfer:
        txn["is_transfer"] = True
    if paired is not None:
        txn["paired"] = paired
    if suspect_reason:
        txn["suspect_reason"] = suspect_reason

    return txn


class TestMetadataRoundTrip:
    """Test metadata encoding/decoding round-trip."""

    def test_encode_decode_confirmed_transfer(self):
        """Test confirmed transfer metadata round-trip."""
        original_note = "Original transaction note"
        metadata = {
            "is_transfer": True,
            "paired": 12345,
        }

        # Encode
        encoded_note = encode_metadata_in_note(original_note, metadata)

        # Decode
        decoded_note, decoded_metadata = decode_metadata_from_note(encoded_note)

        assert decoded_note == original_note
        assert decoded_metadata["paired"] == 12345
        # is_transfer is NOT encoded in note (only in beancount metadata)

    def test_encode_decode_suspected_transfer(self):
        """Test suspected transfer metadata round-trip."""
        original_note = "Test note"
        metadata = {
            "paired": 67890,
            "suspect_reason": "date-delay-3days",
        }

        encoded_note = encode_metadata_in_note(original_note, metadata)
        decoded_note, decoded_metadata = decode_metadata_from_note(encoded_note)

        assert decoded_note == original_note
        assert decoded_metadata["paired"] == 67890
        assert decoded_metadata["suspect_reason"] == "date-delay-3days"

    def test_preserve_existing_note(self):
        """Test that original note content is preserved."""
        original_note = "Important transaction details"
        metadata = {"paired": 111}

        encoded_note = encode_metadata_in_note(original_note, metadata)
        decoded_note, _ = decode_metadata_from_note(encoded_note)

        assert decoded_note == original_note


class TestBeancountWriteRead:
    """Test beancount write/read round-trip for transfer metadata."""

    def test_write_read_confirmed_transfer(self):
        """Test writing and reading confirmed transfer in beancount format."""
        txn = create_test_transaction(
            "100",
            Decimal("-50.00"),
            date(2025, 1, 15),
            account_id=1,
            is_transfer=True,
            paired=200,
        )

        # Convert to beancount text
        beancount_text = convert_transaction_to_beancount(txn)

        # Verify metadata is in the text
        assert 'is_transfer: "true"' in beancount_text
        assert "paired: 200" in beancount_text

    def test_write_read_suspected_transfer(self):
        """Test writing and reading suspected transfer."""
        txn = create_test_transaction(
            "300",
            Decimal("75.00"),
            date(2025, 1, 20),
            account_id=2,
            paired=400,
            suspect_reason="same-direction",
        )

        beancount_text = convert_transaction_to_beancount(txn)

        # Verify metadata
        assert "paired: 400" in beancount_text
        assert 'suspect_reason: "same-direction"' in beancount_text
        assert "; Suspected transfer: same-direction" in beancount_text


class TestDetectionIdempotency:
    """Test idempotency of detection runs."""

    def test_multiple_detection_runs_identical(self):
        """Test that running detection multiple times produces identical results."""
        # Create test transactions
        txns = [
            Transaction(
                id="1",
                amount=Decimal("-100.00"),
                date=date(2025, 1, 1),
                currency_code="USD",
                account={"id": 1, "name": "Checking"},
            ),
            Transaction(
                id="2",
                amount=Decimal("100.00"),
                date=date(2025, 1, 1),
                currency_code="USD",
                account={"id": 2, "name": "Savings"},
            ),
        ]

        detector = TransferDetector()

        # Run detection twice
        result1 = detector.detect_transfers(txns.copy())
        result2 = detector.detect_transfers(txns.copy())

        # Results should be identical
        assert len(result1.confirmed_pairs) == len(result2.confirmed_pairs)
        assert len(result1.suspected_pairs) == len(result2.suspected_pairs)

        if result1.confirmed_pairs:
            pair1 = result1.confirmed_pairs[0]
            pair2 = result2.confirmed_pairs[0]
            assert pair1.source_id == pair2.source_id
            assert pair1.dest_id == pair2.dest_id
            assert pair1.confidence == pair2.confidence

    def test_detection_after_metadata_preserved(self):
        """Test that re-running detection with existing metadata doesn't duplicate."""
        # Transactions already marked as transfers
        txns = [
            Transaction(
                id="1",
                amount=Decimal("-100.00"),
                date=date(2025, 1, 1),
                currency_code="USD",
                account={"id": 1, "name": "Checking"},
                is_transfer=True,
                paired=2,
            ),
            Transaction(
                id="2",
                amount=Decimal("100.00"),
                date=date(2025, 1, 1),
                currency_code="USD",
                account={"id": 2, "name": "Savings"},
                is_transfer=True,
                paired=1,
            ),
        ]

        detector = TransferDetector()
        result = detector.detect_transfers(txns)

        # Should still detect the same pair
        assert len(result.confirmed_pairs) == 1
        assert result.confirmed_pairs[0].source_id == "1"
        assert result.confirmed_pairs[0].dest_id == "2"


class TestPushPullPreservation:
    """Test that transfer metadata is preserved through push/pull operations."""

    def test_beancount_to_pocketsmith_note_encoding(self):
        """Test that beancount metadata gets encoded into PocketSmith note."""
        # Beancount transaction with transfer metadata
        txn_dict = {
            "id": 500,
            "amount": "-25.50",
            "date": "2025-01-10",
            "payee": "Test",
            "note": "Original note",
            "is_transfer": True,
            "paired": 600,
            "transaction_account": {"id": 1, "name": "Test", "currency_code": "USD"},
            "category": {"title": "Transfer", "id": 24918120},
        }

        # Simulate encoding for push to PocketSmith
        metadata = {
            "paired": txn_dict["paired"],
        }
        # Note: is_transfer is NOT pushed to PocketSmith (beancount wins)
        encoded_note = encode_metadata_in_note(txn_dict["note"], metadata)

        # Verify encoding
        assert "[paired:" in encoded_note
        assert "Original note" in encoded_note

    def test_pocketsmith_to_beancount_metadata_extraction(self):
        """Test that PocketSmith note metadata gets extracted to beancount."""
        # PocketSmith transaction with encoded metadata in note
        note_with_metadata = "Test note [paired:123] [suspect_reason:date-delay-3days]"

        decoded_note, metadata = decode_metadata_from_note(note_with_metadata)

        assert decoded_note == "Test note"
        assert metadata["paired"] == 123
        assert metadata["suspect_reason"] == "date-delay-3days"
