"""Tests for pocketsmith.transaction_put module functionality."""

from typing import Any
from unittest.mock import patch

import pytest
import requests

from src.pocketsmith.transaction_put import (
    update_transaction,
    batch_update_transactions,
    update_transaction_note,
    update_transaction_labels,
)
from src.pocketsmith.common import PocketSmithClient


@patch("requests.put", autospec=True)
def test_update_transaction_invalid_updates_returns_false(mock_put):
    client = PocketSmithClient(api_key="k")
    # Invalid note type triggers validate_update_data -> False
    ok = update_transaction("1", {"note": 123}, client=client)
    assert ok is False
    mock_put.assert_not_called()


@patch("requests.put", autospec=True)
def test_update_transaction_requests_exception_branch(mock_put):
    client = PocketSmithClient(api_key="k")

    def raise_req_exc(*args: Any, **kwargs: Any) -> Any:
        raise requests.RequestException("net")

    mock_put.side_effect = raise_req_exc

    with pytest.raises(Exception) as exc:
        update_transaction("1", {"note": "x"}, client=client)
    assert "Network error updating transaction" in str(exc.value)


def test_batch_update_transactions_success_and_missing_id(monkeypatch):
    client = PocketSmithClient(api_key="k")

    # Stub update_transaction called inside batch_update_transactions
    def fake_update(
        transaction_id: str,
        field_updates: dict[str, Any],
        dry_run: bool,
        client: PocketSmithClient,
    ) -> bool:
        return transaction_id == "1"

    monkeypatch.setattr(
        "src.pocketsmith.transaction_put.update_transaction", fake_update
    )

    results = batch_update_transactions(
        [
            {"transaction_id": "1", "note": "a"},
            {"transaction_id": "2", "memo": "b"},
            {"note": "missing"},  # missing id -> False
        ],
        dry_run=True,
        client=client,
    )
    assert results == [True, False, False]


def test_update_transaction_note_and_labels_delegate(monkeypatch):
    client = PocketSmithClient(api_key="k")

    called = {"note": False, "labels": False}

    def fake_put(endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        if endpoint.startswith("transactions/") and "labels" in data:
            called["labels"] = True
        if endpoint.startswith("transactions/") and "note" in data:
            called["note"] = True
        return {"ok": True}

    monkeypatch.setattr(client, "_make_put_request", fake_put)

    update_transaction_note("123", "hi", client=client)
    update_transaction_labels("123", ["a"], client=client)

    assert all(called.values())
