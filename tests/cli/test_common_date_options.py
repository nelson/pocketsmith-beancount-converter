"""Tests for cli.common and cli.date_options small helpers."""

from pathlib import Path

from src.cli.common import handle_default_destination, transaction_id_option
from src.cli.date_options import date_range_options


def test_date_range_options_returns_expected_keys():
    opts = date_range_options()
    assert set(opts.keys()) == {
        "from_date",
        "to_date",
        "this_month",
        "last_month",
        "this_year",
        "last_year",
    }


def test_handle_default_destination_passthrough():
    # When destination is provided, it should be returned unchanged
    p = Path("/tmp/example.beancount")
    assert handle_default_destination(p) == p


def test_transaction_id_option_factory():
    opt = transaction_id_option()
    # Typer Option with help text
    assert hasattr(opt, "help") and "transaction ID" in opt.help
