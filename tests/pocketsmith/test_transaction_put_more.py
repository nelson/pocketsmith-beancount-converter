"""Cover remaining branches in transaction_put.update_transaction."""

from typing import Any
from unittest.mock import patch

import requests

from src.pocketsmith.transaction_put import update_transaction
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

    try:
        update_transaction("1", {"note": "x"}, client=client)
    except Exception as e:  # PocketSmithAPIError
        assert "Network error updating transaction" in str(e)
    else:
        raise AssertionError("Expected PocketSmithAPIError")
