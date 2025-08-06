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
            "  Assets:Test-Bank:Checking  2000.00 USD",
            "  Income:Salary",
        ]

        assert result == "\n".join(expected_lines)
