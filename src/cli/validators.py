"""Input validation utilities for CLI commands."""

from typing import Optional


class ValidationError(Exception):
    """Raised when input validation fails."""

    pass


def validate_transaction_limit_options(
    limit: Optional[int], all_transactions: bool
) -> None:
    """Validate transaction limit options for mutual exclusion.

    Args:
        limit: Transaction limit number
        all_transactions: Whether to fetch all transactions

    Raises:
        ValidationError: If options conflict
    """
    if all_transactions and limit is not None and limit != 30:
        # Note: typer sets default to 30, so we need to check if it was explicitly changed
        raise ValidationError("Cannot specify both --all and --limit/-n options")


def validate_date_options(
    from_date: Optional[str],
    to_date: Optional[str],
    this_month: bool,
    last_month: bool,
    this_year: bool,
    last_year: bool,
) -> None:
    """Validate date options for mutual exclusion and dependencies.

    Args:
        from_date: Start date string
        to_date: End date string
        this_month: This month flag
        last_month: Last month flag
        this_year: This year flag
        last_year: Last year flag

    Raises:
        ValidationError: If options conflict or are invalid
    """
    # Check for --to without --from
    if to_date and not from_date:
        raise ValidationError("Cannot specify --to without --from")

    # Count convenience date options
    convenience_options = [this_month, last_month, this_year, last_year]
    convenience_count = sum(convenience_options)

    # Check for multiple convenience options
    if convenience_count > 1:
        active_options = []
        if this_month:
            active_options.append("--this-month")
        if last_month:
            active_options.append("--last-month")
        if this_year:
            active_options.append("--this-year")
        if last_year:
            active_options.append("--last-year")

        raise ValidationError(
            f"Cannot specify multiple date convenience options: {', '.join(active_options)}"
        )

    # Check for convenience options with explicit dates
    if convenience_count > 0 and (from_date or to_date):
        active_convenience = []
        if this_month:
            active_convenience.append("--this-month")
        if last_month:
            active_convenience.append("--last-month")
        if this_year:
            active_convenience.append("--this-year")
        if last_year:
            active_convenience.append("--last-year")

        explicit_dates = []
        if from_date:
            explicit_dates.append("--from")
        if to_date:
            explicit_dates.append("--to")

        raise ValidationError(
            f"Cannot combine convenience date options ({', '.join(active_convenience)}) "
            f"with explicit date options ({', '.join(explicit_dates)})"
        )


def validate_all_clone_options(
    limit: Optional[int],
    all_transactions: bool,
    from_date: Optional[str],
    to_date: Optional[str],
    this_month: bool,
    last_month: bool,
    this_year: bool,
    last_year: bool,
) -> None:
    """Validate all clone command options together.

    Args:
        limit: Transaction limit number
        all_transactions: Whether to fetch all transactions
        from_date: Start date string
        to_date: End date string
        this_month: This month flag
        last_month: Last month flag
        this_year: This year flag
        last_year: Last year flag

    Raises:
        ValidationError: If any validation fails
    """
    validate_transaction_limit_options(limit, all_transactions)
    validate_date_options(
        from_date, to_date, this_month, last_month, this_year, last_year
    )
