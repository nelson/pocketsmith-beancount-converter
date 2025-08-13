"""Shared date options for CLI commands."""

import typer
from typing import Optional, Dict, Any


def date_range_options() -> Dict[str, Any]:
    """Create shared date range options for commands."""
    from_date = typer.Option(
        None,
        "--from",
        help="Start date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)",
        hidden=True,
    )
    to_date = typer.Option(
        None,
        "--to",
        help="End date (YYYY-MM-DD, YYYYMMDD, YYYY-MM, or YYYY)",
        hidden=True,
    )
    this_month = typer.Option(
        False,
        "--this-month",
        help="Process transactions from current calendar month",
        hidden=True,
    )
    last_month = typer.Option(
        False,
        "--last-month",
        help="Process transactions from previous calendar month",
        hidden=True,
    )
    this_year = typer.Option(
        False,
        "--this-year",
        help="Process transactions from current calendar year",
        hidden=True,
    )
    last_year = typer.Option(
        False,
        "--last-year",
        help="Process transactions from previous calendar year",
        hidden=True,
    )

    return {
        "from_date": from_date,
        "to_date": to_date,
        "this_month": this_month,
        "last_month": last_month,
        "this_year": this_year,
        "last_year": last_year,
    }


class DateOptions:
    """Container for date options."""

    def __init__(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        this_month: bool = False,
        last_month: bool = False,
        this_year: bool = False,
        last_year: bool = False,
    ):
        self.from_date = from_date
        self.to_date = to_date
        self.this_month = this_month
        self.last_month = last_month
        self.this_year = this_year
        self.last_year = last_year
