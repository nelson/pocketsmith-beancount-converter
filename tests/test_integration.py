import tempfile
from pathlib import Path
from src.pocketsmith_beancount.beancount_converter import BeancountConverter
from src.pocketsmith_beancount.file_writer import BeancountFileWriter


class TestIntegration:
    def test_end_to_end_conversion(self):
        """Test full pipeline with mock data"""
        # Mock transaction data
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
            },
            {
                "id": 2,
                "date": "2024-01-01T00:00:00Z",
                "merchant": "Employer",
                "note": "Salary",
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
            },
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
            {"id": 1, "title": "Groceries", "is_transfer": False, "is_income": False},
            {"id": 2, "title": "Salary", "is_transfer": False, "is_income": True},
        ]

        # Test the full conversion pipeline
        converter = BeancountConverter()

        with tempfile.TemporaryDirectory() as temp_dir:
            writer = BeancountFileWriter(temp_dir)

            # Convert transactions
            beancount_content = converter.convert_transactions(
                transactions, transaction_accounts, categories
            )

            # Write to file
            output_file = writer.write_beancount_file(
                beancount_content, "test_integration"
            )

            # Verify file was created
            assert Path(output_file).exists()

            # Read and verify content
            with open(output_file, "r") as f:
                content = f.read()

            # Should contain commodity declarations
            assert "commodity USD" in content

            # Should contain account declarations
            assert "open Assets:Test-Bank:Checking USD" in content

            # Should contain category declarations
            assert "open Expenses:Groceries" in content
            assert "open Income:Salary" in content

            # Should contain transactions in chronological order
            lines = content.split("\n")
            salary_line_idx = next(
                i for i, line in enumerate(lines) if "Employer" in line
            )
            grocery_line_idx = next(
                i for i, line in enumerate(lines) if "Test Store" in line
            )
            assert (
                salary_line_idx < grocery_line_idx
            )  # Salary (Jan 1) before Groceries (Jan 15)

            # Should contain transaction metadata
            assert "id: 1" in content
            assert "id: 2" in content

    def test_multiple_currencies(self):
        """Test handling of multiple currencies in one conversion"""
        transactions = [
            {
                "id": 1,
                "date": "2024-01-15T00:00:00Z",
                "merchant": "US Store",
                "note": "Purchase in USD",
                "amount": "-50.00",
                "currency_code": "USD",
                "transaction_account": {
                    "id": 1,
                    "name": "US Account",
                    "type": "bank",
                    "institution": {"title": "US Bank"},
                },
                "category": {
                    "id": 1,
                    "title": "Shopping",
                    "is_transfer": False,
                    "is_income": False,
                },
            },
            {
                "id": 2,
                "date": "2024-01-16T00:00:00Z",
                "merchant": "AU Store",
                "note": "Purchase in AUD",
                "amount": "-75.00",
                "currency_code": "AUD",
                "transaction_account": {
                    "id": 2,
                    "name": "AU Account",
                    "type": "bank",
                    "institution": {"title": "AU Bank"},
                },
                "category": {
                    "id": 1,
                    "title": "Shopping",
                    "is_transfer": False,
                    "is_income": False,
                },
            },
        ]

        transaction_accounts = [
            {
                "id": 1,
                "name": "US Account",
                "type": "checking",
                "currency_code": "USD",
                "institution": {"title": "US Bank"},
                "starting_balance_date": "2024-01-01T00:00:00Z",
            },
            {
                "id": 2,
                "name": "AU Account",
                "type": "checking",
                "currency_code": "AUD",
                "institution": {"title": "AU Bank"},
                "starting_balance_date": "2024-01-01T00:00:00Z",
            },
        ]

        categories = [
            {"id": 1, "title": "Shopping", "is_transfer": False, "is_income": False}
        ]

        converter = BeancountConverter()
        beancount_content = converter.convert_transactions(
            transactions, transaction_accounts, categories
        )

        # Should contain both currency declarations
        assert "commodity AUD" in beancount_content
        assert "commodity USD" in beancount_content

        # Should contain both account declarations with correct currencies
        assert "open Assets:Us-Bank:Us-Account USD" in beancount_content
        assert "open Assets:Au-Bank:Au-Account AUD" in beancount_content

        # Should contain transactions with correct currencies
        assert "50.00 USD" in beancount_content
        assert "75.00 AUD" in beancount_content

    def test_large_transaction_set(self):
        """Test performance with large datasets"""
        # Create 1000 mock transactions
        transactions = []
        for i in range(1000):
            transactions.append(
                {
                    "id": i + 1,
                    "date": f"2024-01-{(i % 28) + 1:02d}T00:00:00Z",
                    "merchant": f"Merchant {i + 1}",
                    "note": f"Transaction {i + 1}",
                    "amount": f"-{(i % 100) + 1}.00",
                    "currency_code": "USD",
                    "transaction_account": {
                        "id": 1,
                        "name": "Checking",
                        "type": "bank",
                        "institution": {"title": "Test Bank"},
                    },
                    "category": {
                        "id": 1,
                        "title": "Expenses",
                        "is_transfer": False,
                        "is_income": False,
                    },
                }
            )

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
            {"id": 1, "title": "Expenses", "is_transfer": False, "is_income": False}
        ]

        converter = BeancountConverter()

        with tempfile.TemporaryDirectory() as temp_dir:
            writer = BeancountFileWriter(temp_dir)

            # This should complete without performance issues
            beancount_content = converter.convert_transactions(
                transactions, transaction_accounts, categories
            )

            output_file = writer.write_beancount_file(beancount_content, "large_test")

            # Verify file was created and has reasonable size
            assert Path(output_file).exists()
            file_size = Path(output_file).stat().st_size
            assert file_size > 50000  # Should be substantial for 1000 transactions

            # Verify content structure
            with open(output_file, "r") as f:
                content = f.read()

            # Should contain all transactions
            transaction_count = content.count('* "Merchant')
            assert transaction_count == 1000

    def test_special_characters_in_data(self):
        """Test handling of special characters in account names, payees, etc."""
        transactions = [
            {
                "id": 1,
                "date": "2024-01-15T00:00:00Z",
                "merchant": 'Store "The Best" & Co.',
                "note": 'Purchase with "quotes" & symbols!',
                "amount": "-50.00",
                "currency_code": "USD",
                "transaction_account": {
                    "id": 1,
                    "name": "Checking & Savings!",
                    "type": "bank",
                    "institution": {"title": "Bank & Trust Co."},
                },
                "category": {
                    "id": 1,
                    "title": "Food & Dining",
                    "is_transfer": False,
                    "is_income": False,
                },
            }
        ]

        transaction_accounts = [
            {
                "id": 1,
                "name": "Checking & Savings!",
                "type": "checking",
                "currency_code": "USD",
                "institution": {"title": "Bank & Trust Co."},
                "starting_balance_date": "2024-01-01T00:00:00Z",
            }
        ]

        categories = [
            {
                "id": 1,
                "title": "Food & Dining",
                "is_transfer": False,
                "is_income": False,
            }
        ]

        converter = BeancountConverter()
        beancount_content = converter.convert_transactions(
            transactions, transaction_accounts, categories
        )

        # Should sanitize account names properly
        assert "Assets:Bank-Trust-Co:Checking-Savings" in beancount_content
        assert "Expenses:Food-Dining" in beancount_content

        # Should escape quotes in payee and narration
        assert 'Store \\"The Best\\" & Co.' in beancount_content
        assert 'Purchase with \\"quotes\\" & symbols!' in beancount_content

        # Should not contain problematic characters in account names
        assert (
            "&"
            not in [line for line in beancount_content.split("\n") if "open " in line][
                0
            ]
        )
        assert (
            "!"
            not in [line for line in beancount_content.split("\n") if "open " in line][
                0
            ]
        )

    def test_end_to_end_with_labels_and_flags(self) -> None:
        """Test full pipeline with labels and needs_review"""
        converter = BeancountConverter()

        # Mock data with labels and needs_review flags
        transactions = [
            {
                "id": 1,
                "date": "2024-01-01T00:00:00Z",
                "amount": "25.50",
                "merchant": "Coffee Shop",
                "note": "Morning coffee",
                "labels": ["coffee", "daily-expense"],
                "needs_review": False,
                "transaction_account": {"id": 1},
                "category": {"id": 1, "title": "Food & Drink"},
            },
            {
                "id": 2,
                "date": "2024-01-02T00:00:00Z",
                "amount": "150.00",
                "merchant": "Unknown Merchant",
                "note": "Large purchase",
                "labels": ["review-needed", "large-expense"],
                "needs_review": True,
                "transaction_account": {"id": 1},
                "category": {"id": 2, "title": "Miscellaneous"},
            },
        ]

        transaction_accounts = [
            {
                "id": 1,
                "name": "Checking Account",
                "institution": {"title": "Test Bank"},
                "currency_code": "USD",
                "starting_balance_date": "2024-01-01T00:00:00Z",
            }
        ]

        categories = [
            {"id": 1, "title": "Food & Drink"},
            {"id": 2, "title": "Miscellaneous"},
        ]

        beancount_content = converter.convert_transactions(
            transactions, transaction_accounts, categories
        )

        # Should contain tags for both transactions
        assert "#coffee #daily-expense" in beancount_content
        assert "#review-needed #large-expense" in beancount_content

        # Should have correct flags
        assert (
            '2024-01-01 * "Coffee Shop" "Morning coffee" #coffee #daily-expense'
            in beancount_content
        )
        assert (
            '2024-01-02 ! "Unknown Merchant" "Large purchase" #review-needed #large-expense'
            in beancount_content
        )

    def test_end_to_end_with_balance_directives(self) -> None:
        """Test full pipeline with balance directives"""
        converter = BeancountConverter()

        transactions = [
            {
                "id": 1,
                "date": "2024-01-01T00:00:00Z",
                "amount": "100.00",
                "merchant": "Test Merchant",
                "note": "Test transaction",
                "transaction_account": {"id": 1},
                "category": {"id": 1, "title": "Testing"},
            }
        ]

        transaction_accounts = [
            {
                "id": 1,
                "name": "Checking",
                "institution": {"title": "Test Bank"},
                "currency_code": "USD",
                "starting_balance_date": "2024-01-01T00:00:00Z",
            }
        ]

        categories = [{"id": 1, "title": "Testing"}]

        account_balances = {
            1: [
                {"date": "2024-01-01T00:00:00Z", "balance": "1000.00"},
                {"date": "2024-01-02T00:00:00Z", "balance": "900.00"},
            ]
        }

        beancount_content = converter.convert_transactions(
            transactions, transaction_accounts, categories, account_balances
        )

        # Should contain balance directives (account name may vary due to mapping)
        assert "balance" in beancount_content and "1000.00 USD" in beancount_content
        assert "balance" in beancount_content and "900.00 USD" in beancount_content

        # Should still contain transaction
        assert "Test Merchant" in beancount_content

    def test_pagination_integration(self) -> None:
        """Test pagination in full pipeline"""
        # This test would require mocking the PocketSmithClient
        # For now, we'll test the converter can handle large datasets
        converter = BeancountConverter()

        # Generate a large number of transactions to simulate pagination results
        transactions = []
        for i in range(2500):  # Simulate 2.5 pages of 1000 transactions each
            transactions.append(
                {
                    "id": i + 1,
                    "date": f"2024-01-{(i % 30) + 1:02d}T00:00:00Z",
                    "amount": f"{(i % 100) + 1}.00",
                    "merchant": f"Merchant {i + 1}",
                    "note": f"Transaction {i + 1}",
                    "transaction_account": {"id": 1},
                    "category": {"id": 1, "title": "Testing"},
                }
            )

        transaction_accounts = [
            {
                "id": 1,
                "name": "Checking",
                "institution": {"title": "Test Bank"},
                "currency_code": "USD",
                "starting_balance_date": "2024-01-01T00:00:00Z",
            }
        ]

        categories = [{"id": 1, "title": "Testing"}]

        # Should handle large dataset without issues
        beancount_content = converter.convert_transactions(
            transactions, transaction_accounts, categories
        )

        # Should contain all transactions
        assert "Merchant 1" in beancount_content
        assert "Merchant 2500" in beancount_content

        # Should have proper structure (dates may vary)
        assert "commodity USD" in beancount_content
        assert "open Assets:" in beancount_content and "USD" in beancount_content
        assert "open Expenses:Testing" in beancount_content
