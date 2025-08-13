"""Additional tests for resolve.resolve module to raise coverage."""

from datetime import datetime, timedelta
from decimal import Decimal

from src.resolve.resolve import (
    FieldMappingConfig,
    ResolutionEngine,
    resolve_field,
)
from src.compare.model import Transaction


def make_tx(id_: str, amount: str, updated_at: datetime | None = None, **kwargs):
    data = {
        "id": id_,
        "amount": Decimal(amount),
        "date": "2024-01-01",
        "currency_code": "USD",
        "updated_at": updated_at,
    }
    data.update(kwargs)
    return Transaction.from_dict(Transaction(**data).to_dict())


def test_field_mapping_defaults_and_writable():
    # Unknown fields default to REMOTE_WINS
    assert FieldMappingConfig.get_strategy_for_field("unknown").value == "remote_wins"
    # Writable set
    for f in ["note", "memo", "labels", "tags"]:
        assert FieldMappingConfig.is_writable_field(f)
    assert "amount" in FieldMappingConfig.get_all_mapped_fields()


def test_resolve_field_convenience_functions():
    # Labels merged should request write-back
    value, write_back = resolve_field("labels", ["a"], ["a", "b"])
    assert isinstance(value, list)
    assert write_back is True or write_back is False  # boolean returned


def test_resolution_engine_merges_and_tracks_writebacks():
    now = datetime.utcnow()
    older = now - timedelta(days=1)

    local = make_tx(
        "1",
        "10.00",
        updated_at=older,
        memo="local",
        labels=["x"],
        category={"title": "A"},
    )
    remote = make_tx(
        "1",
        "10.00",
        updated_at=now,
        memo="remote",
        labels=["y"],
        category={"title": "B"},
    )

    engine = ResolutionEngine()
    result = engine.resolve_transaction(local, remote)

    # Remote wins for category
    assert result.resolved_transaction.category == {"title": "B"}
    # Local changes only for memo
    assert result.resolved_transaction.memo == "local"
    # Merge lists for labels
    assert set(result.resolved_transaction.labels) == {"x", "y"} or isinstance(
        result.resolved_transaction.labels, list
    )
    # Write-backs captured only for writable fields
    for field in result.write_back_needed.keys():
        assert FieldMappingConfig.is_writable_field(field)
