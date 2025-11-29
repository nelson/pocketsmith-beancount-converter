"""Transfer detection logic with spatial hash indexing."""

import re
import math
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Set, Any
from collections import defaultdict

from .models import TransferPair, DetectionCriteria, DetectionResult
from ..compare.model import Transaction


class TransactionIndex:
    """Spatial hash index for efficient transfer pair finding.

    Uses hybrid logarithmic bucketing for amounts and date-based hash map.
    Optimized for typical transaction distributions (90% under $1000).
    """

    def __init__(self, transactions: List[Transaction]):
        self.transactions = transactions
        self.date_index: Dict[date, List[Transaction]] = defaultdict(list)
        self.amount_index: Dict[int, List[Transaction]] = defaultdict(list)

        self._build_indices()

    def _build_indices(self) -> None:
        """Build both indices. O(n)"""
        for txn in self.transactions:
            # Build date index
            txn_date = self._parse_date(txn.date)
            self.date_index[txn_date].append(txn)

            # Build amount index with hybrid bucketing
            bucket = self._get_amount_bucket(abs(txn.amount))
            self.amount_index[bucket].append(txn)

    def _get_amount_bucket(self, amount: Decimal) -> int:
        """Get bucket ID for amount using hybrid logarithmic strategy.

        Optimized for transaction distributions:
        - 16% under $10 → fine buckets
        - 54% $10-$100 → medium buckets
        - 21% $100-$1000 → coarse buckets
        - 9% over $1000 → logarithmic buckets
        """
        abs_amt = float(amount)

        if abs_amt < 1:
            return 0  # All small amounts
        elif abs_amt < 10:
            return int(abs_amt)  # $1, $2, ... $9
        elif abs_amt < 100:
            return 10 + int(abs_amt / 10)  # $0-10, $10-20, ... $90-100
        elif abs_amt < 1000:
            return 20 + int(abs_amt / 50)  # $0-50, $50-100, ... $950-1000
        elif abs_amt < 10000:
            return 40 + int(abs_amt / 500)  # $0-500, $500-1000, ...
        else:
            # Logarithmic for large amounts
            magnitude = int(math.floor(math.log10(abs_amt)))
            return 60 + magnitude

    def find_candidates(
        self,
        txn: Transaction,
        max_days: int,
        amount_tolerance_percent: Decimal = Decimal("0"),
    ) -> List[Transaction]:
        """Find candidate matches for a transaction.

        Returns transactions that:
        - Are within max_days
        - Have matching amount (within tolerance)
        - Are from different account
        """
        candidates: List[Transaction] = []

        # 1. Find amount bucket range
        amount = abs(txn.amount)
        tolerance = amount * (amount_tolerance_percent / 100)

        # Get buckets to check (center bucket + neighbors for tolerance)
        center_bucket = self._get_amount_bucket(amount)
        buckets_to_check = {center_bucket}

        # Add neighbor buckets if tolerance requires it
        if tolerance > 0:
            min_amount = amount - tolerance
            max_amount = amount + tolerance
            min_bucket = self._get_amount_bucket(min_amount)
            max_bucket = self._get_amount_bucket(max_amount)

            for bucket in range(min_bucket, max_bucket + 1):
                buckets_to_check.add(bucket)

        # 2. Get all transactions in these buckets
        amount_matches = []
        for bucket in buckets_to_check:
            amount_matches.extend(self.amount_index.get(bucket, []))

        # 3. Filter by exact amount range
        min_amount = amount - tolerance
        max_amount = amount + tolerance
        amount_matches = [
            t for t in amount_matches if min_amount <= abs(t.amount) <= max_amount
        ]

        # 4. Filter by date window
        txn_date = self._parse_date(txn.date)
        date_range: Set[date] = set(
            txn_date + timedelta(days=d) for d in range(-max_days, max_days + 1)
        )

        # 5. Combine: candidates must match amount AND date AND different account
        for candidate in amount_matches:
            candidate_date = self._parse_date(candidate.date)

            if candidate_date not in date_range:
                continue

            if not self._different_accounts(txn, candidate):
                continue

            if txn.id == candidate.id:
                continue

            candidates.append(candidate)

        return candidates

    def _parse_date(self, date_value: Any) -> date:
        """Parse date from various formats."""
        if isinstance(date_value, date):
            return date_value
        if isinstance(date_value, str):
            from datetime import datetime

            return datetime.fromisoformat(date_value.replace("Z", "+00:00")).date()
        raise ValueError(f"Cannot parse date: {date_value}")

    def _different_accounts(self, txn1: Transaction, txn2: Transaction) -> bool:
        """Check if from different accounts."""
        # Try ID first (PocketSmith), fall back to name (Beancount)
        account1 = (
            (txn1.account.get("id") or txn1.account.get("name"))
            if txn1.account
            else None
        )
        account2 = (
            (txn2.account.get("id") or txn2.account.get("name"))
            if txn2.account
            else None
        )
        return account1 != account2 and account1 is not None and account2 is not None


class TransferDetector:
    """Detects transfer transaction pairs efficiently."""

    def __init__(self, criteria: Optional[DetectionCriteria] = None):
        self.criteria = criteria or DetectionCriteria()

    def detect_transfers(self, transactions: List[Transaction]) -> DetectionResult:
        """Detect all transfer pairs. O(n) average case."""

        # Build indices
        index = TransactionIndex(transactions)

        paired_ids: Set[str] = set()
        confirmed = []
        suspected = []

        # Find confirmed pairs
        for txn in transactions:
            if txn.id in paired_ids:
                continue

            # Get candidates with exact amount match
            candidates = index.find_candidates(
                txn,
                max_days=self.criteria.max_date_difference_days,
                amount_tolerance_percent=Decimal("0"),
            )

            # Check each candidate
            for candidate in candidates:
                if candidate.id in paired_ids:
                    continue

                if self._is_confirmed_match(txn, candidate):
                    pair = self._create_pair(txn, candidate, "confirmed")
                    confirmed.append(pair)
                    paired_ids.add(txn.id)
                    paired_ids.add(candidate.id)
                    break

        # Find suspected pairs
        for txn in transactions:
            if txn.id in paired_ids:
                continue

            # Get candidates with FX tolerance
            candidates = index.find_candidates(
                txn,
                max_days=self.criteria.max_suspected_date_days,
                amount_tolerance_percent=self.criteria.fx_amount_tolerance_percent,
            )

            for candidate in candidates:
                if candidate.id in paired_ids:
                    continue

                reasons = self._check_suspected_match(txn, candidate)
                if reasons:
                    pair = self._create_pair(
                        txn, candidate, "suspected", ", ".join(reasons)
                    )
                    suspected.append(pair)
                    paired_ids.add(txn.id)
                    paired_ids.add(candidate.id)
                    break

        # Unmatched
        unmatched = [t for t in transactions if t.id not in paired_ids]

        # Detect patterns and notify
        self._notify_patterns(confirmed, suspected)

        return DetectionResult(
            confirmed_pairs=confirmed,
            suspected_pairs=suspected,
            unmatched_transactions=unmatched,
        )

    def _is_confirmed_match(self, txn1: Transaction, txn2: Transaction) -> bool:
        """Check if confirmed transfer (all criteria met)."""
        return self._opposite_directions(txn1, txn2)

    def _check_suspected_match(self, txn1: Transaction, txn2: Transaction) -> List[str]:
        """Return list of ALL reasons why this might be a transfer."""
        reasons = []

        # Scenario 1: Same direction
        if not self._opposite_directions(txn1, txn2):
            reasons.append("same-direction")

        # Scenario 2: Amount mismatch (within FX tolerance)
        if self._has_amount_mismatch(txn1, txn2):
            reasons.append("amount-mismatch-fx")

        # Scenario 3: Date delay beyond confirmed window
        days_diff = self._date_difference_days(txn1, txn2)
        if days_diff > self.criteria.max_date_difference_days:
            reasons.append(f"date-delay-{days_diff}days")

        # Scenario 4: Description suggests transfer
        if self._description_suggests_transfer(
            txn1
        ) or self._description_suggests_transfer(txn2):
            reasons.append("description-based")

        return reasons

    def _opposite_directions(self, txn1: Transaction, txn2: Transaction) -> bool:
        """Check if amounts have opposite signs."""
        return (txn1.amount > 0 and txn2.amount < 0) or (
            txn1.amount < 0 and txn2.amount > 0
        )

    def _has_amount_mismatch(self, txn1: Transaction, txn2: Transaction) -> bool:
        """Check if amount mismatch is within FX tolerance."""
        if not self._has_fx_account(txn1, txn2):
            return False

        amount1 = abs(txn1.amount)
        amount2 = abs(txn2.amount)

        diff = abs(amount1 - amount2)
        if diff == 0:
            return False  # Exact match, not a mismatch

        avg = (amount1 + amount2) / 2
        if avg == 0:
            return False

        percent_diff = (diff / avg) * 100
        return percent_diff <= self.criteria.fx_amount_tolerance_percent

    def _has_fx_account(self, txn1: Transaction, txn2: Transaction) -> bool:
        """Check if either transaction is from an FX-enabled account."""
        fx_accounts = self.criteria.fx_enabled_accounts or []
        for txn in [txn1, txn2]:
            if txn.account:
                account_name = txn.account.get("name", "")
                for fx_name in fx_accounts:
                    if fx_name.lower() in account_name.lower():
                        return True
        return False

    def _date_difference_days(self, txn1: Transaction, txn2: Transaction) -> int:
        """Calculate absolute difference in days."""
        date1 = self._parse_date(txn1.date)
        date2 = self._parse_date(txn2.date)
        return abs((date1 - date2).days)

    def _parse_date(self, date_value: Any) -> date:
        """Parse date from various formats."""
        if isinstance(date_value, date):
            return date_value
        if isinstance(date_value, str):
            from datetime import datetime

            return datetime.fromisoformat(date_value.replace("Z", "+00:00")).date()
        raise ValueError(f"Cannot parse date: {date_value}")

    def _description_suggests_transfer(self, txn: Transaction) -> bool:
        """Check if description contains 'transfer' and name pattern."""
        description = " ".join(
            [
                txn.payee or "",
                txn.memo or "",
                txn.note or "",
            ]
        ).lower()

        if "transfer" not in description:
            return False

        # Regex pattern for name variations
        name_pattern = (
            r"\b(l(ok\s+sun\s+nelson)?|n(elson)?|s(ophia)?|ls(n)?|ss)\s+s?\s*tam\b"
        )
        return re.search(name_pattern, description, re.IGNORECASE) is not None

    def _create_pair(
        self,
        txn1: Transaction,
        txn2: Transaction,
        confidence: str,
        reason: Optional[str] = None,
    ) -> TransferPair:
        """Create a TransferPair with proper source/dest ordering."""
        # Source is negative (money leaving), dest is positive (money entering)
        if txn1.amount < 0:
            source, dest = txn1, txn2
        else:
            source, dest = txn2, txn1

        return TransferPair(
            source_transaction=source,
            dest_transaction=dest,
            confidence=confidence,
            reason=reason,
        )

    def _notify_patterns(
        self, confirmed: List[TransferPair], suspected: List[TransferPair]
    ) -> None:
        """Detect and print patterns that might warrant criteria adjustment."""
        # Count date delays in suspected transfers
        delay_counts: Dict[int, int] = defaultdict(int)
        for pair in suspected:
            if pair.reason and "date-delay" in pair.reason:
                match = re.search(r"date-delay-(\d+)days", pair.reason)
                if match:
                    days = int(match.group(1))
                    delay_counts[days] += 1

        # Notify if systematic delays detected (threshold: 1+)
        for days, count in sorted(delay_counts.items()):
            if count >= 1:
                print(f"⚠️  Pattern detected: {count} transfer(s) with {days}-day delay")
                print(
                    f"   Consider adjusting max_date_difference_days from "
                    f"{self.criteria.max_date_difference_days} to {days}"
                )

        # Count FX mismatches
        fx_count = sum(
            1 for p in suspected if p.reason and "amount-mismatch-fx" in p.reason
        )
        if fx_count >= 1:
            print(f"⚠️  Pattern detected: {fx_count} suspected FX transfer(s)")
            print("   Review if these should be confirmed transfers")
