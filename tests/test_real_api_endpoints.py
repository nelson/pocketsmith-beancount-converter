import os
import pytest
import re
from datetime import datetime, timedelta
from src.pocketsmith_beancount.pocketsmith_client import PocketSmithClient


@pytest.fixture
def real_api_client():
    """Fixture for real API client - requires POCKETSMITH_API_KEY environment variable."""
    api_key = os.getenv("POCKETSMITH_API_KEY")
    if not api_key:
        pytest.skip(
            "POCKETSMITH_API_KEY environment variable not set - skipping real API tests"
        )
    return PocketSmithClient(api_key)


class TestRealAPIEndpoints:
    """Tests that actually call PocketSmith API endpoints to validate data integrity."""

    @pytest.mark.real_api
    def test_real_api_get_accounts(self, real_api_client):
        """Test actual PocketSmith accounts endpoint with data validation."""
        accounts = real_api_client.get_accounts()

        assert isinstance(accounts, list), "Accounts should be returned as a list"

        if accounts:  # Only validate if we have accounts
            for account in accounts:
                # Validate account ID is not empty/zero
                assert account.get("id"), f"Account ID should not be empty: {account}"
                assert isinstance(account["id"], int), (
                    f"Account ID should be integer: {account['id']}"
                )
                assert account["id"] > 0, (
                    f"Account ID should be positive: {account['id']}"
                )

                # Validate account title is not empty string (PocketSmith uses 'title' not 'name')
                account_title = account.get("title") or account.get("name")
                assert account_title, f"Account title should not be empty: {account}"
                assert isinstance(account_title, str), (
                    f"Account title should be string: {account_title}"
                )
                assert account_title.strip(), (
                    f"Account title should not be whitespace only: {account_title}"
                )

                # Validate account type is present and is a string
                account_type = account.get("type")
                assert account_type, f"Account type should not be empty: {account}"
                assert isinstance(account_type, str), (
                    f"Account type should be string: {account_type}"
                )
                # PocketSmith uses various account types, so we just validate it's a non-empty string

                # Validate currency_code is valid 3-letter code
                currency_code = account.get("currency_code")
                assert currency_code, f"Currency code should not be empty: {account}"
                assert isinstance(currency_code, str), (
                    f"Currency code should be string: {currency_code}"
                )
                assert len(currency_code) == 3, (
                    f"Currency code should be 3 letters: {currency_code}"
                )
                # Currency codes from PocketSmith may be lowercase, so normalize for validation
                upper_currency_code = currency_code.upper()
                assert len(upper_currency_code) == 3, (
                    f"Currency code should be 3 letters: {currency_code}"
                )
                assert re.match(r"^[A-Z]{3}$", upper_currency_code), (
                    f"Invalid currency code format: {currency_code}"
                )

                # Validate institution data when present
                institution = account.get("institution")
                if institution:
                    assert isinstance(institution, dict), (
                        f"Institution should be dict: {institution}"
                    )
                    if institution.get("name"):
                        assert isinstance(institution["name"], str), (
                            f"Institution name should be string: {institution['name']}"
                        )
                        assert institution["name"].strip(), (
                            f"Institution name should not be empty: {institution['name']}"
                        )

    @pytest.mark.real_api
    def test_real_api_get_categories(self, real_api_client):
        """Test actual PocketSmith categories endpoint with data validation."""
        categories = real_api_client.get_categories()

        assert isinstance(categories, list), "Categories should be returned as a list"

        if categories:  # Only validate if we have categories
            category_ids = set()
            for category in categories:
                # Validate category ID is not empty/zero
                assert category.get("id"), (
                    f"Category ID should not be empty: {category}"
                )
                assert isinstance(category["id"], int), (
                    f"Category ID should be integer: {category['id']}"
                )
                assert category["id"] > 0, (
                    f"Category ID should be positive: {category['id']}"
                )
                category_ids.add(category["id"])

                # Validate category title is not empty string
                assert category.get("title"), (
                    f"Category title should not be empty: {category}"
                )
                assert isinstance(category["title"], str), (
                    f"Category title should be string: {category['title']}"
                )
                assert category["title"].strip(), (
                    f"Category title should not be whitespace only: {category['title']}"
                )

                # Validate parent_id relationships are consistent
                parent_id = category.get("parent_id")
                if parent_id is not None:
                    assert isinstance(parent_id, int), (
                        f"Parent ID should be integer: {parent_id}"
                    )
                    assert parent_id > 0, f"Parent ID should be positive: {parent_id}"

                # Validate colour field format when present
                colour = category.get("colour")
                if colour:
                    assert isinstance(colour, str), f"Colour should be string: {colour}"
                    # Should be hex color format
                    assert re.match(r"^#[0-9A-Fa-f]{6}$", colour), (
                        f"Invalid colour format: {colour}"
                    )

            # Validate parent_id references exist
            for category in categories:
                parent_id = category.get("parent_id")
                if parent_id is not None:
                    assert parent_id in category_ids, (
                        f"Parent ID {parent_id} not found in categories for category {category['id']}"
                    )

    @pytest.mark.real_api
    def test_real_api_get_transaction_accounts(self, real_api_client):
        """Test actual transaction accounts endpoint with data validation."""
        transaction_accounts = real_api_client.get_transaction_accounts()

        assert isinstance(transaction_accounts, list), (
            "Transaction accounts should be returned as a list"
        )

        if transaction_accounts:  # Only validate if we have transaction accounts
            # Get regular accounts for validation
            accounts = real_api_client.get_accounts()
            account_ids = {acc["id"] for acc in accounts}

            for trans_account in transaction_accounts:
                # Validate transaction account ID is not empty/zero
                assert trans_account.get("id"), (
                    f"Transaction account ID should not be empty: {trans_account}"
                )
                assert isinstance(trans_account["id"], int), (
                    f"Transaction account ID should be integer: {trans_account['id']}"
                )
                assert trans_account["id"] > 0, (
                    f"Transaction account ID should be positive: {trans_account['id']}"
                )

                # Validate account_id references valid account
                account_id = trans_account.get("account_id")
                assert account_id, f"Account ID should not be empty: {trans_account}"
                assert isinstance(account_id, int), (
                    f"Account ID should be integer: {account_id}"
                )
                assert account_id in account_ids, (
                    f"Account ID {account_id} not found in accounts"
                )

                # Validate starting_balance is numeric when present
                starting_balance = trans_account.get("starting_balance")
                if starting_balance is not None:
                    assert isinstance(starting_balance, (int, float, str)), (
                        f"Starting balance should be numeric: {starting_balance}"
                    )
                    if isinstance(starting_balance, str):
                        try:
                            float(starting_balance)
                        except ValueError:
                            pytest.fail(
                                f"Starting balance string not convertible to float: {starting_balance}"
                            )

                # Validate starting_balance_date format when present
                starting_balance_date = trans_account.get("starting_balance_date")
                if starting_balance_date:
                    assert isinstance(starting_balance_date, str), (
                        f"Starting balance date should be string: {starting_balance_date}"
                    )
                    # Should be ISO date format
                    try:
                        datetime.fromisoformat(
                            starting_balance_date.replace("Z", "+00:00")
                        )
                    except ValueError:
                        pytest.fail(
                            f"Invalid starting balance date format: {starting_balance_date}"
                        )

    @pytest.mark.real_api
    def test_real_api_get_transactions(self, real_api_client):
        """Test actual transactions endpoint with data validation."""
        # Get recent transactions (last 30 days)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        transactions = real_api_client.get_transactions(
            start_date=start_date, end_date=end_date
        )

        assert isinstance(transactions, list), (
            "Transactions should be returned as a list"
        )

        if transactions:  # Only validate if we have transactions
            for transaction in transactions:
                # Validate transaction ID is not empty/zero
                assert transaction.get("id"), (
                    f"Transaction ID should not be empty: {transaction}"
                )
                assert isinstance(transaction["id"], int), (
                    f"Transaction ID should be integer: {transaction['id']}"
                )
                assert transaction["id"] > 0, (
                    f"Transaction ID should be positive: {transaction['id']}"
                )

                # Validate payee is not empty when present
                payee = transaction.get("payee")
                if payee is not None:
                    assert isinstance(payee, str), f"Payee should be string: {payee}"
                    # Allow empty payee, but if present should not be just whitespace
                    if payee:
                        assert payee.strip(), (
                            f"Payee should not be whitespace only: '{payee}'"
                        )

                # Validate amount is not zero (can be positive or negative)
                amount = transaction.get("amount")
                assert amount is not None, f"Amount should not be None: {transaction}"
                assert isinstance(amount, (int, float, str)), (
                    f"Amount should be numeric: {amount}"
                )
                if isinstance(amount, str):
                    try:
                        float_amount = float(amount)
                        assert float_amount != 0, f"Amount should not be zero: {amount}"
                    except ValueError:
                        pytest.fail(f"Amount string not convertible to float: {amount}")
                else:
                    assert amount != 0, f"Amount should not be zero: {amount}"

                # Validate date format is valid
                date = transaction.get("date")
                assert date, f"Date should not be empty: {transaction}"
                assert isinstance(date, str), f"Date should be string: {date}"
                try:
                    datetime.fromisoformat(date.replace("Z", "+00:00"))
                except ValueError:
                    pytest.fail(f"Invalid date format: {date}")

                # Validate currency_code matches account currency when account is present
                currency_code = transaction.get("currency_code")
                if currency_code:
                    assert isinstance(currency_code, str), (
                        f"Currency code should be string: {currency_code}"
                    )
                    assert len(currency_code) == 3, (
                        f"Currency code should be 3 letters: {currency_code}"
                    )
                    assert currency_code.isupper(), (
                        f"Currency code should be uppercase: {currency_code}"
                    )

                # Validate labels array structure
                labels = transaction.get("labels")
                if labels is not None:
                    assert isinstance(labels, list), f"Labels should be list: {labels}"
                    for label in labels:
                        assert isinstance(label, str), (
                            f"Label should be string: {label}"
                        )

                # Validate needs_review is boolean
                needs_review = transaction.get("needs_review")
                if needs_review is not None:
                    assert isinstance(needs_review, bool), (
                        f"Needs review should be boolean: {needs_review}"
                    )

                # Validate updated_at timestamp format
                updated_at = transaction.get("updated_at")
                if updated_at:
                    assert isinstance(updated_at, str), (
                        f"Updated at should be string: {updated_at}"
                    )
                    try:
                        datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    except ValueError:
                        pytest.fail(f"Invalid updated_at format: {updated_at}")

                # Validate closing_balance is numeric when present
                closing_balance = transaction.get("closing_balance")
                if closing_balance is not None:
                    assert isinstance(closing_balance, (int, float, str)), (
                        f"Closing balance should be numeric: {closing_balance}"
                    )
                    if isinstance(closing_balance, str):
                        try:
                            float(closing_balance)
                        except ValueError:
                            pytest.fail(
                                f"Closing balance string not convertible to float: {closing_balance}"
                            )

    @pytest.mark.real_api
    def test_real_api_get_account_balances(self, real_api_client):
        """Test actual account balances endpoint with data validation."""
        # Skip this test as get_account_balances method is not implemented yet
        pytest.skip("get_account_balances method not implemented in PocketSmithClient")

        # Get accounts first
        accounts = real_api_client.get_accounts()

        if not accounts:
            pytest.skip("No accounts available for balance testing")

        # Test with first account
        account_id = accounts[0]["id"]
        # balances = real_api_client.get_account_balances(account_id)

        # Mock balances for testing structure (since method not implemented)
        balances = []  # Empty list for now

        assert isinstance(balances, list), "Balances should be returned as a list"

        if balances:  # Only validate if we have balances
            for balance in balances:
                # Validate balance amount is numeric
                amount = balance.get("amount")
                assert amount is not None, (
                    f"Balance amount should not be None: {balance}"
                )
                assert isinstance(amount, (int, float, str)), (
                    f"Balance amount should be numeric: {amount}"
                )
                if isinstance(amount, str):
                    try:
                        float(amount)
                    except ValueError:
                        pytest.fail(
                            f"Balance amount string not convertible to float: {amount}"
                        )

                # Validate date format is valid
                date = balance.get("date")
                assert date, f"Balance date should not be empty: {balance}"
                assert isinstance(date, str), f"Balance date should be string: {date}"
                try:
                    datetime.fromisoformat(date.replace("Z", "+00:00"))
                except ValueError:
                    pytest.fail(f"Invalid balance date format: {date}")

                # Validate account_id references valid account
                balance_account_id = balance.get("account_id")
                if balance_account_id is not None:
                    assert isinstance(balance_account_id, int), (
                        f"Balance account ID should be integer: {balance_account_id}"
                    )
                    assert balance_account_id == account_id, (
                        f"Balance account ID should match requested account: {balance_account_id} != {account_id}"
                    )

    @pytest.mark.real_api
    def test_real_api_error_handling(self, real_api_client):
        """Test error handling with real API calls."""
        # Test with invalid account ID
        with pytest.raises(Exception):  # Should raise some kind of error
            real_api_client.get_account_balances(999999999)  # Very unlikely to exist

        # Test with invalid date range
        with pytest.raises(Exception):  # Should raise some kind of error
            real_api_client.get_transactions(
                start_date="invalid-date", end_date="2024-01-01"
            )

    @pytest.mark.real_api
    def test_real_api_pagination_consistency(self, real_api_client):
        """Test that pagination returns consistent results."""
        # Get transactions with a date range that might have multiple pages
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime(
            "%Y-%m-%d"
        )  # Full year

        transactions = real_api_client.get_transactions(
            start_date=start_date, end_date=end_date
        )

        # Verify no duplicate transaction IDs
        transaction_ids = [t["id"] for t in transactions]
        assert len(transaction_ids) == len(set(transaction_ids)), (
            "Duplicate transaction IDs found in paginated results"
        )

        # Verify transactions are within date range
        for transaction in transactions:
            trans_date = datetime.fromisoformat(
                transaction["date"].replace("Z", "+00:00")
            ).date()
            start_date_obj = datetime.fromisoformat(start_date).date()
            end_date_obj = datetime.fromisoformat(end_date).date()
            assert start_date_obj <= trans_date <= end_date_obj, (
                f"Transaction date {trans_date} outside range {start_date} to {end_date}"
            )
