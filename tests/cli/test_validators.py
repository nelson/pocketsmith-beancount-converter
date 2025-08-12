"""Tests for input validation utilities."""

import pytest
from src.cli.validators import (
    validate_transaction_limit_options,
    validate_date_options,
    validate_all_clone_options,
    ValidationError,
)


class TestValidateTransactionLimitOptions:
    """Test transaction limit option validation."""

    def test_valid_limit_only(self):
        """Test valid limit without all flag."""
        # Should not raise any exception
        validate_transaction_limit_options(limit=100, all_transactions=False)

    def test_valid_all_only(self):
        """Test valid all flag without explicit limit."""
        # Should not raise any exception (limit=30 is default, not explicitly set)
        validate_transaction_limit_options(limit=30, all_transactions=True)

    def test_valid_default_limit_with_all(self):
        """Test that default limit (30) with all flag is allowed."""
        # This represents the case where user didn't specify -n but used --all
        validate_transaction_limit_options(limit=30, all_transactions=True)

    def test_invalid_explicit_limit_with_all(self):
        """Test that explicit limit with all flag fails."""
        with pytest.raises(
            ValidationError, match="Cannot specify both --all and --limit"
        ):
            validate_transaction_limit_options(limit=100, all_transactions=True)

    def test_none_limit_with_all(self):
        """Test None limit with all flag."""
        # Should not raise any exception
        validate_transaction_limit_options(limit=None, all_transactions=True)


class TestValidateDateOptions:
    """Test date option validation."""

    def test_valid_from_to_dates(self):
        """Test valid from and to dates."""
        validate_date_options(
            from_date="2024-01-01",
            to_date="2024-12-31",
            this_month=False,
            last_month=False,
            this_year=False,
            last_year=False,
        )

    def test_valid_from_date_only(self):
        """Test valid from date without to date."""
        validate_date_options(
            from_date="2024-01-01",
            to_date=None,
            this_month=False,
            last_month=False,
            this_year=False,
            last_year=False,
        )

    def test_valid_this_month_only(self):
        """Test valid this month convenience option."""
        validate_date_options(
            from_date=None,
            to_date=None,
            this_month=True,
            last_month=False,
            this_year=False,
            last_year=False,
        )

    def test_valid_last_month_only(self):
        """Test valid last month convenience option."""
        validate_date_options(
            from_date=None,
            to_date=None,
            this_month=False,
            last_month=True,
            this_year=False,
            last_year=False,
        )

    def test_valid_this_year_only(self):
        """Test valid this year convenience option."""
        validate_date_options(
            from_date=None,
            to_date=None,
            this_month=False,
            last_month=False,
            this_year=True,
            last_year=False,
        )

    def test_valid_last_year_only(self):
        """Test valid last year convenience option."""
        validate_date_options(
            from_date=None,
            to_date=None,
            this_month=False,
            last_month=False,
            this_year=False,
            last_year=True,
        )

    def test_valid_no_date_options(self):
        """Test valid case with no date options."""
        validate_date_options(
            from_date=None,
            to_date=None,
            this_month=False,
            last_month=False,
            this_year=False,
            last_year=False,
        )

    def test_invalid_to_without_from(self):
        """Test that to date without from date fails."""
        with pytest.raises(ValidationError, match="Cannot specify --to without --from"):
            validate_date_options(
                from_date=None,
                to_date="2024-12-31",
                this_month=False,
                last_month=False,
                this_year=False,
                last_year=False,
            )

    def test_invalid_multiple_convenience_options(self):
        """Test that multiple convenience options fail."""
        with pytest.raises(
            ValidationError, match="Cannot specify multiple date convenience options"
        ):
            validate_date_options(
                from_date=None,
                to_date=None,
                this_month=True,
                last_month=True,
                this_year=False,
                last_year=False,
            )

    def test_invalid_all_convenience_options(self):
        """Test that all convenience options together fail."""
        with pytest.raises(
            ValidationError, match="Cannot specify multiple date convenience options"
        ):
            validate_date_options(
                from_date=None,
                to_date=None,
                this_month=True,
                last_month=True,
                this_year=True,
                last_year=True,
            )

    def test_invalid_convenience_with_from_date(self):
        """Test that convenience option with from date fails."""
        with pytest.raises(
            ValidationError, match="Cannot combine convenience date options"
        ):
            validate_date_options(
                from_date="2024-01-01",
                to_date=None,
                this_month=True,
                last_month=False,
                this_year=False,
                last_year=False,
            )

    def test_invalid_convenience_with_to_date(self):
        """Test that convenience option with to date fails."""
        # This should fail with --to without --from first, not convenience combination
        with pytest.raises(ValidationError, match="Cannot specify --to without --from"):
            validate_date_options(
                from_date=None,
                to_date="2024-12-31",
                this_month=False,
                last_month=False,
                this_year=True,
                last_year=False,
            )

    def test_invalid_convenience_with_both_dates(self):
        """Test that convenience option with both dates fails."""
        with pytest.raises(
            ValidationError, match="Cannot combine convenience date options"
        ):
            validate_date_options(
                from_date="2024-01-01",
                to_date="2024-12-31",
                this_month=False,
                last_month=True,
                this_year=False,
                last_year=False,
            )


class TestValidateAllCloneOptions:
    """Test comprehensive clone option validation."""

    def test_valid_basic_options(self):
        """Test valid basic option combination."""
        validate_all_clone_options(
            limit=50,
            all_transactions=False,
            from_date="2024-01-01",
            to_date="2024-12-31",
            this_month=False,
            last_month=False,
            this_year=False,
            last_year=False,
        )

    def test_valid_all_transactions_with_date_range(self):
        """Test valid all transactions with date range."""
        validate_all_clone_options(
            limit=30,  # Default limit
            all_transactions=True,
            from_date="2024-01-01",
            to_date="2024-12-31",
            this_month=False,
            last_month=False,
            this_year=False,
            last_year=False,
        )

    def test_valid_convenience_date_with_limit(self):
        """Test valid convenience date with limit."""
        validate_all_clone_options(
            limit=100,
            all_transactions=False,
            from_date=None,
            to_date=None,
            this_month=True,
            last_month=False,
            this_year=False,
            last_year=False,
        )

    def test_invalid_limit_and_all_transactions(self):
        """Test invalid combination of explicit limit and all transactions."""
        with pytest.raises(
            ValidationError, match="Cannot specify both --all and --limit"
        ):
            validate_all_clone_options(
                limit=100,
                all_transactions=True,
                from_date=None,
                to_date=None,
                this_month=False,
                last_month=False,
                this_year=False,
                last_year=False,
            )

    def test_invalid_multiple_date_options(self):
        """Test invalid multiple date options."""
        with pytest.raises(
            ValidationError, match="Cannot specify multiple date convenience options"
        ):
            validate_all_clone_options(
                limit=30,
                all_transactions=False,
                from_date=None,
                to_date=None,
                this_month=True,
                last_month=True,
                this_year=False,
                last_year=False,
            )

    def test_invalid_convenience_with_explicit_dates(self):
        """Test invalid convenience date with explicit dates."""
        with pytest.raises(
            ValidationError, match="Cannot combine convenience date options"
        ):
            validate_all_clone_options(
                limit=30,
                all_transactions=False,
                from_date="2024-01-01",
                to_date=None,
                this_month=False,
                last_month=False,
                this_year=True,
                last_year=False,
            )

    def test_invalid_to_without_from(self):
        """Test invalid to date without from date."""
        with pytest.raises(ValidationError, match="Cannot specify --to without --from"):
            validate_all_clone_options(
                limit=30,
                all_transactions=False,
                from_date=None,
                to_date="2024-12-31",
                this_month=False,
                last_month=False,
                this_year=False,
                last_year=False,
            )


class TestValidationErrorMessages:
    """Test that validation error messages are clear and helpful."""

    def test_limit_all_error_message(self):
        """Test error message for limit and all conflict."""
        with pytest.raises(ValidationError) as exc_info:
            validate_transaction_limit_options(limit=100, all_transactions=True)

        assert "--all" in str(exc_info.value)
        assert "--limit" in str(exc_info.value) or "-n" in str(exc_info.value)

    def test_multiple_convenience_error_message(self):
        """Test error message for multiple convenience options."""
        with pytest.raises(ValidationError) as exc_info:
            validate_date_options(
                from_date=None,
                to_date=None,
                this_month=True,
                last_month=True,
                this_year=False,
                last_year=False,
            )

        error_msg = str(exc_info.value)
        assert "--this-month" in error_msg
        assert "--last-month" in error_msg
        assert "multiple" in error_msg.lower()

    def test_convenience_explicit_error_message(self):
        """Test error message for convenience with explicit dates."""
        with pytest.raises(ValidationError) as exc_info:
            validate_date_options(
                from_date="2024-01-01",
                to_date=None,
                this_month=True,
                last_month=False,
                this_year=False,
                last_year=False,
            )

        error_msg = str(exc_info.value)
        assert "--this-month" in error_msg
        assert "--from" in error_msg
        assert "combine" in error_msg.lower()

    def test_to_without_from_error_message(self):
        """Test error message for to without from."""
        with pytest.raises(ValidationError) as exc_info:
            validate_date_options(
                from_date=None,
                to_date="2024-12-31",
                this_month=False,
                last_month=False,
                this_year=False,
                last_year=False,
            )

        error_msg = str(exc_info.value)
        assert "--to" in error_msg
        assert "--from" in error_msg
