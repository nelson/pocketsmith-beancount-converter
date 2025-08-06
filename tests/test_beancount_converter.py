from typing import Any

from src.pocketsmith_beancount.beancount_converter import BeancountConverter


class TestBeancountConverter:
    def setup_method(self):
        self.converter = BeancountConverter()

    def test_sanitize_account_name(self):
        assert self.converter._sanitize_account_name("Test Account!") == "Test-Account"
        assert (
            self.converter._sanitize_account_name("My Bank & Trust") == "My-Bank-Trust"
        )
        assert self.converter._sanitize_account_name("---test---") == "Test"
        # Test underscore stripping and space conversion
        assert self.converter._sanitize_account_name("_Test Account") == "Test-Account"
        assert (
            self.converter._sanitize_account_name("__Multiple Underscores")
            == "Multiple-Underscores"
        )
        assert (
            self.converter._sanitize_account_name("Test Account With Spaces")
            == "Test-Account-With-Spaces"
        )

    def test_get_account_name(self):
        account = {
            "id": 1,
            "name": "Checking Account",
            "type": "checking",
            "institution": {"title": "Test Bank"},
        }

        result = self.converter._get_account_name(account)
        assert result == "Assets:Test-Bank:Checking-Account"

    def test_get_category_account_expense(self):
        category = {
            "id": 1,
            "title": "Groceries",
            "is_transfer": False,
            "is_income": False,
        }

        result = self.converter._get_category_account(category)
        assert result == "Expenses:Groceries"

    def test_get_category_account_income(self):
        category = {"id": 2, "title": "Salary", "is_transfer": False, "is_income": True}

        result = self.converter._get_category_account(category)
        assert result == "Income:Salary"

    def test_convert_transaction_expense(self):
        transaction = {
            "id": 1,
            "date": "2024-01-15T00:00:00Z",
            "payee": "Test Store",
            "memo": "Grocery shopping",
            "amount": "-50.00",
            "currency_code": "USD",
            "transaction_account": {
                "id": 1,
                "name": "Checking",
                "type": "bank",
                "institution": {"title": "Test Bank"},
            },
            "category": {
                "id": 1,
                "title": "Groceries",
                "is_transfer": False,
                "is_income": False,
            },
        }

        accounts = {
            1: {
                "id": 1,
                "name": "Checking",
                "type": "checking",
                "institution": {"title": "Test Bank"},
            }
        }

        result = self.converter.convert_transaction(transaction, accounts)

        expected_lines = [
            '2024-01-15 * "Test Store" "Grocery shopping"',
            '    id: "1"',
            "  Expenses:Groceries  50.00 USD",
            "  Assets:Test-Bank:Checking",
        ]

        assert result == "\n".join(expected_lines)

    def test_convert_transaction_income(self):
        transaction = {
            "id": 2,
            "date": "2024-01-01T00:00:00Z",
            "payee": "Employer",
            "memo": "Salary",
            "amount": "2000.00",
            "currency_code": "USD",
            "transaction_account": {
                "id": 1,
                "name": "Checking",
                "type": "bank",
                "institution": {"title": "Test Bank"},
            },
            "category": {
                "id": 2,
                "title": "Salary",
                "is_transfer": False,
                "is_income": True,
            },
        }

        accounts = {
            1: {
                "id": 1,
                "name": "Checking",
                "type": "checking",
                "institution": {"title": "Test Bank"},
            }
        }

        result = self.converter.convert_transaction(transaction, accounts)

        expected_lines = [
            '2024-01-01 * "Employer" "Salary"',
            '    id: "2"',
            "  Assets:Test-Bank:Checking  2000.00 USD",
            "  Income:Salary",
        ]

        assert result == "\n".join(expected_lines)

    def test_commodity_capitalization(self):
        """Test that commodities are properly capitalized"""
        self.converter.currencies.add("aud")
        self.converter.currencies.add("usd")
        self.converter.currencies.add("eur")

        declarations = self.converter.generate_commodity_declarations()

        # Check that all currencies are uppercase in declarations
        assert any("AUD" in decl for decl in declarations)
        assert any("USD" in decl for decl in declarations)
        assert any("EUR" in decl for decl in declarations)
        assert not any("aud" in decl for decl in declarations)

    def test_account_declarations_with_metadata(self):
        """Test that account declarations include PocketSmith ID metadata"""
        accounts = [
            {
                "id": 123,
                "name": "Test Account",
                "type": "checking",
                "currency_code": "usd",
                "institution": {"title": "Test Bank"},
            }
        ]

        declarations = self.converter.generate_account_declarations(accounts)

        assert len(declarations) == 1
        assert "Assets:Test-Bank:Test-Account USD" in declarations[0]
        assert 'id: "123"' in declarations[0]

    def test_category_declarations(self):
        """Test that category account declarations are generated"""
        categories = [
            {"id": 1, "title": "Groceries", "is_transfer": False, "is_income": False},
            {"id": 2, "title": "Salary", "is_transfer": False, "is_income": True},
            {"id": 3, "title": "Transfer", "is_transfer": True, "is_income": False},
        ]

        declarations = self.converter.generate_category_declarations(categories)

        assert len(declarations) == 3
        assert any("Expenses:Groceries" in decl for decl in declarations)
        assert any("Income:Salary" in decl for decl in declarations)
        assert any("Transfers:Transfer" in decl for decl in declarations)
        assert all("id:" in decl for decl in declarations)

    def test_payee_narration_mapping(self):
        """Test that merchant maps to payee and note maps to narration"""
        transaction = {
            "id": 1,
            "date": "2024-01-15T00:00:00Z",
            "merchant": "Test Merchant",
            "note": "Test note",
            "payee": "Old Payee",  # Should be ignored in favor of merchant
            "memo": "Old memo",  # Should be ignored in favor of note
            "amount": "-50.00",
            "currency_code": "USD",
            "transaction_account": {
                "id": 1,
                "name": "Checking",
                "type": "bank",
                "institution": {"title": "Test Bank"},
            },
            "category": {
                "id": 1,
                "title": "Groceries",
                "is_transfer": False,
                "is_income": False,
            },
        }

        accounts = {
            1: {
                "id": 1,
                "name": "Checking",
                "type": "checking",
                "institution": {"title": "Test Bank"},
            }
        }

        result = self.converter.convert_transaction(transaction, accounts)

        # Should use merchant as payee and note as narration
        assert '"Test Merchant" "Test note"' in result

    def test_empty_narration_allowed(self):
        """Test that empty narration is allowed when note is empty"""
        transaction = {
            "id": 1,
            "date": "2024-01-15T00:00:00Z",
            "merchant": "Test Merchant",
            "note": "",  # Empty note should result in empty narration
            "amount": "-50.00",
            "currency_code": "USD",
            "transaction_account": {
                "id": 1,
                "name": "Checking",
                "type": "bank",
                "institution": {"title": "Test Bank"},
            },
            "category": {
                "id": 1,
                "title": "Groceries",
                "is_transfer": False,
                "is_income": False,
            },
        }

        accounts = {
            1: {
                "id": 1,
                "name": "Checking",
                "type": "checking",
                "institution": {"title": "Test Bank"},
            }
        }

        result = self.converter.convert_transaction(transaction, accounts)

        # Should have empty narration
        assert '"Test Merchant" ""' in result

    def test_currency_capitalization_in_transactions(self):
        """Test that currency codes are capitalized in transaction output"""
        transaction = {
            "id": 1,
            "date": "2024-01-15T00:00:00Z",
            "merchant": "Test Store",
            "note": "Test",
            "amount": "-50.00",
            "currency_code": "aud",  # lowercase
            "transaction_account": {
                "id": 1,
                "name": "Checking",
                "type": "bank",
                "institution": {"title": "Test Bank"},
            },
            "category": {
                "id": 1,
                "title": "Groceries",
                "is_transfer": False,
                "is_income": False,
            },
        }

        accounts = {
            1: {
                "id": 1,
                "name": "Checking",
                "type": "checking",
                "institution": {"title": "Test Bank"},
            }
        }

        result = self.converter.convert_transaction(transaction, accounts)

        # Should use uppercase AUD
        assert "50.00 AUD" in result
        assert "aud" not in result

    def test_get_category_account_transfer(self):
        """Test transfer category handling"""
        category = {
            "id": 3,
            "title": "Transfer",
            "is_transfer": True,
            "is_income": False,
        }

        result = self.converter._get_category_account(category)
        assert result == "Transfers:Transfer"

    def test_get_category_account_none(self):
        """Test null/missing category handling"""
        # Test with None - this will test the None check in the method
        result = self.converter._get_category_account({})  # Empty dict instead of None
        assert result == "Expenses:Uncategorized"

    def test_get_account_name_credit_card(self):
        """Test credit card account type mapping to Liabilities"""
        account = {
            "id": 1,
            "name": "Credit Card",
            "type": "credit_card",
            "institution": {"title": "Test Bank"},
        }

        result = self.converter._get_account_name(account)
        assert result == "Liabilities:Test-Bank:Credit-Card"

    def test_get_account_name_loan(self):
        """Test loan account type mapping to Liabilities"""
        account = {
            "id": 1,
            "name": "Personal Loan",
            "type": "loan",
            "institution": {"title": "Test Bank"},
        }

        result = self.converter._get_account_name(account)
        assert result == "Liabilities:Test-Bank:Personal-Loan"

    def test_get_account_name_missing_institution(self):
        """Test accounts without institution data"""
        account = {
            "id": 1,
            "name": "Cash Account",
            "type": "checking",
        }

        result = self.converter._get_account_name(account)
        assert result == "Assets:Unknown:Cash-Account"

    def test_convert_transaction_missing_category(self):
        """Test transactions without categories"""
        transaction = {
            "id": 1,
            "date": "2024-01-15T00:00:00Z",
            "merchant": "Test Store",
            "note": "Test purchase",
            "amount": "-50.00",
            "currency_code": "USD",
            "transaction_account": {
                "id": 1,
                "name": "Checking",
                "type": "bank",
                "institution": {"title": "Test Bank"},
            },
            # No category field
        }

        accounts = {
            1: {
                "id": 1,
                "name": "Checking",
                "type": "checking",
                "institution": {"title": "Test Bank"},
            }
        }

        result = self.converter.convert_transaction(transaction, accounts)

        # Should use Expenses:Uncategorized
        assert "Expenses:Uncategorized" in result

    def test_convert_transaction_missing_transaction_account(self):
        """Test transactions without account data"""
        transaction = {
            "id": 1,
            "date": "2024-01-15T00:00:00Z",
            "merchant": "Test Store",
            "note": "Test purchase",
            "amount": "-50.00",
            "currency_code": "USD",
            # No transaction_account field
        }

        accounts: dict[int, dict[str, Any]] = {}

        result = self.converter.convert_transaction(transaction, accounts)

        # Should return empty string for invalid transaction
        assert result == ""

    def test_convert_transaction_quote_escaping(self):
        """Test payee/narration with quotes"""
        transaction = {
            "id": 1,
            "date": "2024-01-15T00:00:00Z",
            "merchant": 'Store "The Best"',
            "note": 'Purchase with "quotes"',
            "amount": "-50.00",
            "currency_code": "USD",
            "transaction_account": {
                "id": 1,
                "name": "Checking",
                "type": "bank",
                "institution": {"title": "Test Bank"},
            },
            "category": {
                "id": 1,
                "title": "Groceries",
                "is_transfer": False,
                "is_income": False,
            },
        }

        accounts = {
            1: {
                "id": 1,
                "name": "Checking",
                "type": "checking",
                "institution": {"title": "Test Bank"},
            }
        }

        result = self.converter.convert_transaction(transaction, accounts)

        # Should escape quotes properly
        assert 'Store \\"The Best\\"' in result
        assert 'Purchase with \\"quotes\\"' in result

    def test_convert_transactions_full_integration(self):
        """Test the full convert_transactions() method"""
        transactions = [
            {
                "id": 1,
                "date": "2024-01-15T00:00:00Z",
                "merchant": "Test Store",
                "note": "Grocery shopping",
                "amount": "-50.00",
                "currency_code": "USD",
                "transaction_account": {
                    "id": 1,
                    "name": "Checking",
                    "type": "bank",
                    "institution": {"title": "Test Bank"},
                },
                "category": {
                    "id": 1,
                    "title": "Groceries",
                    "is_transfer": False,
                    "is_income": False,
                },
            }
        ]

        transaction_accounts = [
            {
                "id": 1,
                "name": "Checking",
                "type": "checking",
                "currency_code": "USD",
                "institution": {"title": "Test Bank"},
                "starting_balance_date": "2024-01-01T00:00:00Z",
            }
        ]

        categories = [
            {"id": 1, "title": "Groceries", "is_transfer": False, "is_income": False}
        ]

        result = self.converter.convert_transactions(
            transactions, transaction_accounts, categories
        )

        # Should contain commodity, account, and category declarations
        assert "commodity USD" in result
        assert "open Assets:Test-Bank:Checking USD" in result
        assert "open Expenses:Groceries" in result
        assert "Test Store" in result
        assert "Grocery shopping" in result

    def test_generate_account_declarations_missing_dates(self):
        """Test accounts without starting_balance_date"""
        accounts = [
            {
                "id": 1,
                "name": "Test Account",
                "type": "checking",
                "currency_code": "USD",
                "institution": {"title": "Test Bank"},
                # No starting_balance_date
            }
        ]

        declarations = self.converter.generate_account_declarations(accounts)

        assert len(declarations) == 1
        # Should use current date when no starting_balance_date
        from datetime import datetime

        current_date = datetime.now().strftime("%Y-%m-%d")
        assert current_date in declarations[0]

    def test_generate_commodity_declarations_empty(self):
        """Test when no currencies are tracked"""
        # Don't add any currencies to the converter
        declarations = self.converter.generate_commodity_declarations()

        assert declarations == []
