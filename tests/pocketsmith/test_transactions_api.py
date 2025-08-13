"""Tests for pocketsmith transaction get/put modules.

All HTTP is mocked to avoid network calls.
"""

from typing import Any
from unittest.mock import patch, MagicMock

import pytest

from src.pocketsmith.common import PocketSmithClient, PocketSmithAPIError
from src.pocketsmith.transaction_get import get_transactions, get_transaction
from src.pocketsmith.transaction_put import update_transaction


class DummyResp:
    def __init__(
        self,
        json_data: Any,
        status: int = 200,
        headers: dict[str, str] | None = None,
        text: str = "OK",
    ) -> None:
        self._json = json_data
        self.status_code = status
        self.headers = headers or {}
        self.text = text

    def json(self) -> Any:
        return self._json

    def raise_for_status(self) -> None:
        if not (200 <= self.status_code < 400):
            raise Exception(f"HTTP {self.status_code}")


@patch("src.pocketsmith.transaction_get.get_user", autospec=True)
@patch("requests.get", autospec=True)
def test_get_transactions_pagination(mock_get: MagicMock, mock_get_user: MagicMock):
    client = PocketSmithClient(api_key="k")

    mock_get_user.return_value = {"id": 1}

    # First page with Link header to next
    first_headers = {
        "Link": "<https://api.pocketsmith.com/v2/users/1/transactions?page=2>; rel=next, <https://api.pocketsmith.com/v2/users/1/transactions?page=1>; rel=prev",
    }
    second_headers = {"Link": ""}

    mock_get.side_effect = [
        DummyResp([{"id": 1}], headers=first_headers),
        DummyResp([{"id": 2}], headers=second_headers),
    ]

    # Pass optional params to cover param mapping branches
    txns = get_transactions(
        start_date="2024-01-01",
        end_date="2024-01-31",
        account_id=123,
        updated_since="2024-02-01T00:00:00Z",
        client=client,
    )
    assert [t["id"] for t in txns] == [1, 2]


@patch("src.pocketsmith.transaction_get.get_user", autospec=True)
@patch("requests.get", autospec=True)
def test_get_transactions_single_page(mock_get: MagicMock, mock_get_user: MagicMock):
    client = PocketSmithClient(api_key="k")
    mock_get_user.return_value = {"id": 1}
    mock_get.return_value = DummyResp([{"id": 1}], headers={"Link": ""})
    txns = get_transactions(client=client)
    assert len(txns) == 1


def test_get_single_transaction_delegates(monkeypatch):
    client = PocketSmithClient(api_key="k")

    def fake_make_request(endpoint: str, params: Any | None = None) -> Any:
        assert endpoint == "transactions/123"
        return {"id": 123}

    monkeypatch.setattr(client, "_make_request", fake_make_request)
    assert get_transaction(123, client=client)["id"] == 123


@patch("requests.put", autospec=True)
def test_update_transaction_dry_run(mock_put: MagicMock):
    # Should not call requests when dry_run=True
    ok = update_transaction(
        "1", {"note": "x"}, dry_run=True, client=PocketSmithClient(api_key="k")
    )
    assert ok is True
    mock_put.assert_not_called()


@patch("requests.put", autospec=True)
def test_update_transaction_retry_after_then_success(mock_put: MagicMock):
    client = PocketSmithClient(api_key="k")
    # First 429 with Retry-After 0, then 200
    mock_put.side_effect = [
        DummyResp({}, status=429, headers={"Retry-After": "0"}),
        DummyResp({}, status=200),
    ]
    ok = update_transaction("1", {"note": "x"}, client=client)
    assert ok is True
    assert mock_put.call_count == 2


@patch("requests.put", autospec=True)
def test_update_transaction_failure_raises(mock_put: MagicMock):
    client = PocketSmithClient(api_key="k")
    mock_put.return_value = DummyResp({}, status=500, text="boom")
    with pytest.raises(PocketSmithAPIError):
        update_transaction("1", {"note": "x"}, client=client)


@patch("requests.put", autospec=True)
def test_update_transaction_requests_exception(mock_put: MagicMock):
    client = PocketSmithClient(api_key="k")

    def raise_exc(*args: Any, **kwargs: Any) -> Any:
        raise Exception("net")

    mock_put.side_effect = raise_exc
    with pytest.raises(PocketSmithAPIError):
        update_transaction("1", {"note": "x"}, client=client)
