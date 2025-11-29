"""Data models for transfer detection."""

from dataclasses import dataclass
from typing import Optional, List
from decimal import Decimal

from ..compare.model import Transaction


@dataclass
class TransferPair:
    """Represents a matched pair of transfer transactions."""

    source_transaction: Transaction  # Money leaving account
    dest_transaction: Transaction  # Money entering account
    confidence: str  # "confirmed" or "suspected"
    reason: Optional[str] = None  # For suspected: why it's suspect

    @property
    def source_id(self) -> str:
        return self.source_transaction.id

    @property
    def dest_id(self) -> str:
        return self.dest_transaction.id

    @property
    def amount(self) -> Decimal:
        """Return absolute amount of transfer."""
        return abs(self.source_transaction.amount)

    def __str__(self) -> str:
        return (
            f"TransferPair({self.confidence}): "
            f"{self.source_id} → {self.dest_id} "
            f"({self.amount} {self.source_transaction.currency_code})"
        )


@dataclass
class DetectionCriteria:
    """Configuration for transfer detection."""

    # Confirmed transfer criteria
    max_date_difference_days: int = 2
    amount_tolerance: Decimal = Decimal("0.00")  # Exact match by default

    # Suspected transfer criteria
    max_suspected_date_days: int = 4  # Relaxed date window
    fx_amount_tolerance_percent: Decimal = Decimal("5.0")  # 5% for FX fees

    # Name variations for description matching
    name_variations: Optional[List[str]] = None

    # Accounts with foreign currency (for FX tolerance)
    fx_enabled_accounts: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.name_variations is None:
            self.name_variations = [
                "Lok Sun Nelson Tam",
                "Sophia S Tam",
                "LSN Tam",
                "N Tam",
                "L Tam",
                "S Tam",
                "SS Tam",
            ]

        if self.fx_enabled_accounts is None:
            self.fx_enabled_accounts = ["Wise"]


@dataclass
class DetectionResult:
    """Results from transfer detection."""

    confirmed_pairs: List[TransferPair]
    suspected_pairs: List[TransferPair]
    unmatched_transactions: List[Transaction]

    @property
    def total_pairs(self) -> int:
        return len(self.confirmed_pairs) + len(self.suspected_pairs)

    def __str__(self) -> str:
        return (
            f"DetectionResult: "
            f"{len(self.confirmed_pairs)} confirmed, "
            f"{len(self.suspected_pairs)} suspected, "
            f"{len(self.unmatched_transactions)} unmatched"
        )
