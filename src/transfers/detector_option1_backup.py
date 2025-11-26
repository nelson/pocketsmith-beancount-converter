"""
BACKUP: Option 1 (Dual Index with Binary Search)

This is a fallback implementation using sorted lists and binary search.
Performance: O(n log n) build + O(n log n) queries

Use this if Option 3 (Spatial Hash) shows performance degradation due to:
- Extreme clustering in few buckets (>1000 items per bucket)
- Need for exact range queries
- Very sparse amount distribution

To use: Replace TransactionIndex in detector.py with this implementation.
"""

from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..compare.model import Transaction


class TransactionIndexOption1:
    """Efficient index using binary search on sorted amounts."""

    def __init__(self, transactions: List["Transaction"]):
        self.transactions = transactions
        self.date_index: Dict[date, List["Transaction"]] = defaultdict(list)
        self.amount_index: List[Tuple[Decimal, "Transaction"]] = []

        self._build_indices()

    def _build_indices(self):
        """Build both indices. O(n log n)"""
        # Build date index: O(n)
        for txn in self.transactions:
            txn_date = self._parse_date(txn.date)
            self.date_index[txn_date].append(txn)

        # Build amount index: O(n log n)
        self.amount_index = [
            (abs(txn.amount), txn)
            for txn in self.transactions
        ]
        self.amount_index.sort(key=lambda x: x[0])

    def find_candidates(
        self,
        txn: "Transaction",
        max_days: int,
        amount_tolerance_percent: Decimal = Decimal("0")
    ) -> List["Transaction"]:
        """Find candidate matches for a transaction.

        Returns transactions that:
        - Are within max_days
        - Have matching amount (within tolerance)
        - Are from different account
        """
        candidates = []

        # 1. Find amount range
        amount = abs(txn.amount)
        tolerance = amount * (amount_tolerance_percent / 100)
        min_amount = amount - tolerance
        max_amount = amount + tolerance

        # 2. Binary search for amount range in sorted list
        # Custom comparison for bisect with tuple keys
        left_idx = bisect_left(self.amount_index, (min_amount, ))
        right_idx = bisect_right(self.amount_index, (max_amount, ))

        amount_matches = [
            t for _, t in self.amount_index[left_idx:right_idx]
        ]

        # 3. Filter by date window
        txn_date = self._parse_date(txn.date)
        date_range = set(
            txn_date + timedelta(days=d)
            for d in range(-max_days, max_days + 1)
        )

        # 4. Combine: candidates must be in both amount AND date matches
        for candidate in amount_matches:
            candidate_date = self._parse_date(candidate.date)

            # Check date proximity
            if candidate_date not in date_range:
                continue

            # Check different account
            if not self._different_accounts(txn, candidate):
                continue

            # Check not same transaction
            if txn.id == candidate.id:
                continue

            candidates.append(candidate)

        return candidates

    def _parse_date(self, date_value) -> date:
        """Parse date from various formats."""
        if isinstance(date_value, date):
            return date_value
        if isinstance(date_value, str):
            from datetime import datetime
            return datetime.fromisoformat(date_value.replace("Z", "+00:00")).date()
        raise ValueError(f"Cannot parse date: {date_value}")

    def _different_accounts(self, txn1: "Transaction", txn2: "Transaction") -> bool:
        """Check if from different accounts."""
        account1 = txn1.account.get("id") if txn1.account else None
        account2 = txn2.account.get("id") if txn2.account else None
        return account1 != account2 and account1 is not None and account2 is not None
