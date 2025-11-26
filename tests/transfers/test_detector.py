"""Tests for transfer detector with spatial hash indexing."""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from src.transfers.detector import TransferDetector, TransactionIndex
from src.transfers.models import DetectionCriteria
from src.compare.model import Transaction


def create_transaction(
    txn_id: str,
    amount: Decimal,
    txn_date: date,
    account_id: int,
    account_name: str = "Test Account",
    payee: str = "Test Payee",
) -> Transaction:
    """Helper to create a transaction for testing."""
    return Transaction(
        id=txn_id,
        amount=amount,
        date=txn_date,
        currency_code="USD",
        payee=payee,
        account={"id": account_id, "name": account_name},
    )


class TestTransactionIndex:
    """Test spatial hash indexing."""

    def test_amount_bucket_small_amounts(self):
        """Test bucketing for small amounts (<$1)."""
        index = TransactionIndex([])
        assert index._get_amount_bucket(Decimal("0.50")) == 0
        assert index._get_amount_bucket(Decimal("0.99")) == 0

    def test_amount_bucket_1_to_10(self):
        """Test bucketing for $1-$10."""
        index = TransactionIndex([])
        assert index._get_amount_bucket(Decimal("1.00")) == 1
        assert index._get_amount_bucket(Decimal("5.00")) == 5
        assert index._get_amount_bucket(Decimal("9.99")) == 9

    def test_amount_bucket_10_to_100(self):
        """Test bucketing for $10-$100."""
        index = TransactionIndex([])
        assert index._get_amount_bucket(Decimal("10.00")) == 11  # 10 + 10/10 = 11
        assert index._get_amount_bucket(Decimal("25.00")) == 12  # 10 + 25/10 = 12
        assert index._get_amount_bucket(Decimal("99.00")) == 19  # 10 + 99/10 = 19

    def test_amount_bucket_100_to_1000(self):
        """Test bucketing for $100-$1000."""
        index = TransactionIndex([])
        assert index._get_amount_bucket(Decimal("100.00")) == 22  # 20 + 100/50 = 22
        assert index._get_amount_bucket(Decimal("500.00")) == 30  # 20 + 500/50 = 30
        assert index._get_amount_bucket(Decimal("999.00")) == 39  # 20 + 999/50 = 39

    def test_find_candidates_exact_match(self):
        """Test finding candidates with exact amount match."""
        txn1 = create_transaction("1", Decimal("-100.00"), date(2025, 1, 1), 1, "Account A")
        txn2 = create_transaction("2", Decimal("100.00"), date(2025, 1, 2), 2, "Account B")
        txn3 = create_transaction("3", Decimal("-50.00"), date(2025, 1, 1), 1, "Account A")

        index = TransactionIndex([txn1, txn2, txn3])
        candidates = index.find_candidates(txn1, max_days=3)

        assert len(candidates) == 1
        assert candidates[0].id == "2"

    def test_find_candidates_with_tolerance(self):
        """Test finding candidates with amount tolerance."""
        txn1 = create_transaction("1", Decimal("-100.00"), date(2025, 1, 1), 1, "Account A")
        txn2 = create_transaction("2", Decimal("102.00"), date(2025, 1, 2), 2, "Account B")  # 2% diff

        index = TransactionIndex([txn1, txn2])

        # With 5% tolerance, should find
        candidates = index.find_candidates(txn1, max_days=3, amount_tolerance_percent=Decimal("5.0"))
        assert len(candidates) == 1

        # With 1% tolerance, should not find
        candidates = index.find_candidates(txn1, max_days=3, amount_tolerance_percent=Decimal("1.0"))
        assert len(candidates) == 0

    def test_find_candidates_date_filter(self):
        """Test date filtering."""
        txn1 = create_transaction("1", Decimal("-100.00"), date(2025, 1, 1), 1)
        txn2 = create_transaction("2", Decimal("100.00"), date(2025, 1, 2), 2)  # 1 day
        txn3 = create_transaction("3", Decimal("100.00"), date(2025, 1, 10), 3)  # 9 days

        index = TransactionIndex([txn1, txn2, txn3])

        candidates = index.find_candidates(txn1, max_days=2)
        assert len(candidates) == 1
        assert candidates[0].id == "2"


class TestTransferDetector:
    """Test transfer detection logic."""

    def test_detect_confirmed_transfer_simple(self):
        """Test detecting a simple confirmed transfer."""
        txn1 = create_transaction("1", Decimal("-100.00"), date(2025, 1, 1), 1, "Checking")
        txn2 = create_transaction("2", Decimal("100.00"), date(2025, 1, 1), 2, "Savings")

        detector = TransferDetector()
        result = detector.detect_transfers([txn1, txn2])

        assert len(result.confirmed_pairs) == 1
        assert len(result.suspected_pairs) == 0
        assert len(result.unmatched_transactions) == 0

        pair = result.confirmed_pairs[0]
        assert pair.source_id == "1"
        assert pair.dest_id == "2"
        assert pair.confidence == "confirmed"

    def test_detect_confirmed_transfer_with_date_diff(self):
        """Test confirmed transfer with date difference within threshold."""
        txn1 = create_transaction("1", Decimal("-100.00"), date(2025, 1, 1), 1)
        txn2 = create_transaction("2", Decimal("100.00"), date(2025, 1, 3), 2)  # 2 days later

        criteria = DetectionCriteria(max_date_difference_days=2)
        detector = TransferDetector(criteria)
        result = detector.detect_transfers([txn1, txn2])

        assert len(result.confirmed_pairs) == 1

    def test_no_match_beyond_date_threshold(self):
        """Test that transfers beyond date threshold become suspected."""
        txn1 = create_transaction("1", Decimal("-100.00"), date(2025, 1, 1), 1)
        txn2 = create_transaction("2", Decimal("100.00"), date(2025, 1, 5), 2)  # 4 days later

        criteria = DetectionCriteria(max_date_difference_days=2, max_suspected_date_days=5)
        detector = TransferDetector(criteria)
        result = detector.detect_transfers([txn1, txn2])

        assert len(result.confirmed_pairs) == 0
        assert len(result.suspected_pairs) == 1
        assert "date-delay-4days" in result.suspected_pairs[0].reason

    def test_same_direction_suspected(self):
        """Test same direction transactions become suspected."""
        # Both negative (withdrawals from different accounts)
        txn1 = create_transaction("1", Decimal("-100.00"), date(2025, 1, 1), 1)
        txn2 = create_transaction("2", Decimal("-100.00"), date(2025, 1, 1), 2)

        detector = TransferDetector()
        result = detector.detect_transfers([txn1, txn2])

        assert len(result.confirmed_pairs) == 0
        assert len(result.suspected_pairs) == 1
        assert "same-direction" in result.suspected_pairs[0].reason

    def test_amount_mismatch_fx(self):
        """Test FX amount mismatch detection."""
        txn1 = create_transaction("1", Decimal("-100.00"), date(2025, 1, 1), 1, "Wise")
        txn2 = create_transaction("2", Decimal("102.00"), date(2025, 1, 1), 2, "Checking")  # 2% diff

        criteria = DetectionCriteria(
            fx_enabled_accounts=["Wise"],
            fx_amount_tolerance_percent=Decimal("5.0")
        )
        detector = TransferDetector(criteria)
        result = detector.detect_transfers([txn1, txn2])

        assert len(result.confirmed_pairs) == 0
        assert len(result.suspected_pairs) == 1
        assert "amount-mismatch-fx" in result.suspected_pairs[0].reason

    def test_description_based_detection(self):
        """Test description-based transfer detection."""
        txn1 = create_transaction(
            "1", Decimal("-100.00"), date(2025, 1, 1), 1,
            payee="Transfer to N Tam"
        )
        txn2 = create_transaction(
            "2", Decimal("100.00"), date(2025, 1, 5), 2,
            payee="Transfer from Sophia"
        )

        criteria = DetectionCriteria(max_suspected_date_days=5)
        detector = TransferDetector(criteria)
        result = detector.detect_transfers([txn1, txn2])

        # Should be suspected due to date delay + description match
        assert len(result.suspected_pairs) >= 1
        suspect_pair = next(
            (p for p in result.suspected_pairs if p.source_id == "1"),
            None
        )
        if suspect_pair:
            assert "description-based" in suspect_pair.reason

    def test_no_self_pairing(self):
        """Test that a transaction doesn't pair with itself."""
        txn1 = create_transaction("1", Decimal("-100.00"), date(2025, 1, 1), 1)

        detector = TransferDetector()
        result = detector.detect_transfers([txn1])

        assert len(result.confirmed_pairs) == 0
        assert len(result.suspected_pairs) == 0
        assert len(result.unmatched_transactions) == 1

    def test_no_same_account_pairing(self):
        """Test that transactions from same account don't pair."""
        txn1 = create_transaction("1", Decimal("-100.00"), date(2025, 1, 1), 1)
        txn2 = create_transaction("2", Decimal("100.00"), date(2025, 1, 1), 1)  # Same account

        detector = TransferDetector()
        result = detector.detect_transfers([txn1, txn2])

        assert len(result.confirmed_pairs) == 0
        assert len(result.unmatched_transactions) == 2

    def test_multiple_pairs(self):
        """Test detecting multiple transfer pairs."""
        txns = [
            create_transaction("1", Decimal("-100.00"), date(2025, 1, 1), 1),
            create_transaction("2", Decimal("100.00"), date(2025, 1, 1), 2),
            create_transaction("3", Decimal("-50.00"), date(2025, 1, 5), 1),
            create_transaction("4", Decimal("50.00"), date(2025, 1, 5), 2),
        ]

        detector = TransferDetector()
        result = detector.detect_transfers(txns)

        assert len(result.confirmed_pairs) == 2
        assert len(result.unmatched_transactions) == 0

    def test_one_to_one_pairing(self):
        """Test that each transaction pairs at most once."""
        # Two deposits matching one withdrawal
        txn1 = create_transaction("1", Decimal("-100.00"), date(2025, 1, 1), 1)
        txn2 = create_transaction("2", Decimal("100.00"), date(2025, 1, 1), 2)
        txn3 = create_transaction("3", Decimal("100.00"), date(2025, 1, 1), 3)

        detector = TransferDetector()
        result = detector.detect_transfers([txn1, txn2, txn3])

        # Should only create one pair (txn1 pairs with first match found)
        assert len(result.confirmed_pairs) == 1
        assert len(result.unmatched_transactions) == 1

    def test_month_boundary_transfer(self):
        """Test transfer across month boundary."""
        txn1 = create_transaction("1", Decimal("-100.00"), date(2025, 1, 31), 1)
        txn2 = create_transaction("2", Decimal("100.00"), date(2025, 2, 1), 2)

        detector = TransferDetector()
        result = detector.detect_transfers([txn1, txn2])

        assert len(result.confirmed_pairs) == 1

    def test_year_boundary_transfer(self):
        """Test transfer across year boundary."""
        txn1 = create_transaction("1", Decimal("-100.00"), date(2024, 12, 31), 1)
        txn2 = create_transaction("2", Decimal("100.00"), date(2025, 1, 1), 2)

        detector = TransferDetector()
        result = detector.detect_transfers([txn1, txn2])

        assert len(result.confirmed_pairs) == 1
