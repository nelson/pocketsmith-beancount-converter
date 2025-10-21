"""Tests for beancount.write module functionality."""

import pytest
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st

from src.beancount.write import (
    write_ledger,
    update_ledger,
    write_hierarchical_ledger,
    generate_transactions_content,
    generate_monthly_transactions_content,
    generate_main_file_content,
    convert_transaction_to_beancount,
    generate_account_declarations,
    generate_category_declarations,
    get_account_name_from_transaction_account,
    get_category_account_from_category,
)
from src.beancount.common import BeancountError


class TestWriteLedger:
    """Test ledger file writing functionality."""

    def test_write_ledger_basic(self):
        """Test writing basic content to ledger file."""
        content = """
        1900-01-01 open Assets:Checking USD
        
        2024-01-15 * "Test Transaction"
          Assets:Checking  100.00 USD
          Expenses:Food   -100.00 USD
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.beancount"
            result_path = write_ledger(content, str(file_path))

            assert Path(result_path).exists()
            assert Path(result_path).read_text() == content

    def test_write_ledger_creates_directories(self):
        """Test that write_ledger creates parent directories."""
        content = "test content"

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "subdir" / "nested" / "test.beancount"
            result_path = write_ledger(content, str(file_path))

            assert Path(result_path).exists()
            assert Path(result_path).read_text() == content

    def test_write_ledger_append_mode(self):
        """Test writing to ledger in append mode."""
        initial_content = "Initial content\n"
        append_content = "Appended content\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.beancount"

            # Write initial content
            write_ledger(initial_content, str(file_path))

            # Append content
            write_ledger(append_content, str(file_path), mode="a")

            final_content = Path(file_path).read_text()
            assert final_content == initial_content + append_content

    def test_write_ledger_invalid_path(self):
        """Test writing to invalid path raises BeancountError."""
        with pytest.raises(BeancountError) as exc_info:
            write_ledger("test", "/invalid/readonly/path/file.beancount")

        assert "Failed to write to" in str(exc_info.value)


class TestUpdateLedger:
    """Test ledger update functionality."""

    def test_update_ledger_append_mode(self):
        """Test updating ledger in append mode."""
        transactions = [
            {
                "id": "123",
                "date": "2024-01-15",
                "payee": "Test Merchant",
                "amount": "-50.00",
                "currency_code": "USD",
                "memo": "Test transaction",
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.beancount"
            result_path = update_ledger(str(file_path), transactions, mode="append")

            assert Path(result_path).exists()
            content = Path(result_path).read_text()
            assert "Test Merchant" in content
            assert "2024-01-15" in content

    def test_update_ledger_overwrite_mode(self):
        """Test updating ledger in overwrite mode."""
        transactions = [
            {
                "id": "123",
                "date": "2024-01-15",
                "payee": "Test Merchant",
                "amount": "-50.00",
                "currency_code": "USD",
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.beancount"

            # Create initial file
            Path(file_path).write_text("Initial content")

            # Update in overwrite mode
            result_path = update_ledger(str(file_path), transactions, mode="overwrite")

            content = Path(result_path).read_text()
            assert "Initial content" not in content
            assert "Test Merchant" in content


class TestWriteHierarchicalLedger:
    """Test hierarchical ledger structure writing."""

    def test_write_hierarchical_ledger_basic(self):
        """Test writing basic hierarchical ledger structure."""
        transactions = [
            {
                "id": "123",
                "date": "2024-01-15",
                "payee": "Test Merchant",
                "amount": "-50.00",
                "currency_code": "USD",
                "transaction_account": {
                    "id": "1",
                    "name": "Checking",
                    "currency_code": "USD",
                },
            },
            {
                "id": "124",
                "date": "2024-03-10",
                "payee": "Another Merchant",
                "amount": "-25.00",
                "currency_code": "USD",
                "transaction_account": {
                    "id": "1",
                    "name": "Checking",
                    "currency_code": "USD",
                },
            },
        ]

        transaction_accounts = [
            {
                "id": "1",
                "name": "Checking",
                "institution": {"title": "Test Bank"},
                "currency_code": "USD",
            }
        ]

        categories = [{"id": "1", "title": "Food & Dining"}]

        with tempfile.TemporaryDirectory() as temp_dir:
            result = write_hierarchical_ledger(
                transactions, transaction_accounts, categories, temp_dir
            )

            assert isinstance(result, dict)

            # Check main file was created
            main_file = Path(temp_dir) / "main.beancount"
            assert main_file.exists()

            # Check year directories were created
            year_2024_dir = Path(temp_dir) / "2024"
            assert year_2024_dir.exists()

            # Check monthly files were created
            jan_file = year_2024_dir / "2024-01.beancount"
            mar_file = year_2024_dir / "2024-03.beancount"
            assert jan_file.exists()
            assert mar_file.exists()

    def test_write_hierarchical_ledger_empty_transactions(self):
        """Test writing hierarchical ledger with no transactions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            write_hierarchical_ledger([], [], [], temp_dir)

            # Should still create main file
            main_file = Path(temp_dir) / "main.beancount"
            assert main_file.exists()

            # No year directories should be created
            year_dirs = list(Path(temp_dir).glob("20*"))
            assert len(year_dirs) == 0

    def test_write_hierarchical_ledger_with_balances(self):
        """Test writing hierarchical ledger with account balances."""
        transactions = []
        transaction_accounts = [
            {
                "id": "1",
                "name": "Checking",
                "institution": {"title": "Test Bank"},
                "currency_code": "USD",
            }
        ]
        categories = []
        account_balances = {
            "1": [{"date": "2024-01-15T00:00:00Z", "balance": "1000.00"}]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            write_hierarchical_ledger(
                transactions,
                transaction_accounts,
                categories,
                temp_dir,
                account_balances,
            )

            main_file = Path(temp_dir) / "main.beancount"
            content = main_file.read_text()

            # Should include balance assertions
            assert "balance" in content.lower()
            assert "1000.00" in content


class TestGenerateTransactionsContent:
    """Test transaction content generation."""

    def test_generate_transactions_content_basic(self):
        """Test generating basic transaction content."""
        transactions = [
            {
                "id": "123",
                "date": "2024-01-15",
                "payee": "Test Merchant",
                "amount": "-50.00",
                "currency_code": "USD",
                "memo": "Test transaction",
                "transaction_account": {
                    "id": "1",
                    "name": "Checking",
                    "currency_code": "USD",
                },
                "category": {"id": "1", "title": "Food"},
            }
        ]

        content = generate_transactions_content(transactions)

        assert "2024-01-15" in content
        assert "Test Merchant" in content
        assert "50.00 USD" in content
        assert "Test transaction" in content

    def test_generate_transactions_content_empty(self):
        """Test generating content from empty transaction list."""
        content = generate_transactions_content([])
        assert content == ""

    def test_generate_transactions_content_sorting(self):
        """Test that transactions are sorted by date."""
        transactions = [
            {
                "id": "123",
                "date": "2024-01-20",
                "payee": "Second",
                "amount": "-50.00",
                "currency_code": "USD",
            },
            {
                "id": "124",
                "date": "2024-01-10",
                "payee": "First",
                "amount": "-25.00",
                "currency_code": "USD",
            },
        ]

        content = generate_transactions_content(transactions)
        first_pos = content.find("First")
        second_pos = content.find("Second")

        assert first_pos < second_pos  # First should appear before Second


class TestGenerateMonthlyTransactionsContent:
    """Test monthly transaction content generation."""

    def test_generate_monthly_content_basic(self):
        """Test generating monthly transaction content."""
        transactions = [
            {
                "id": "123",
                "date": "2024-01-15",
                "payee": "Test Merchant",
                "amount": "-50.00",
                "currency_code": "USD",
            }
        ]

        content = generate_monthly_transactions_content(transactions, 2024, 1)

        assert "2024-01-15" in content
        assert "Test Merchant" in content

    def test_generate_monthly_content_filtering(self):
        """Test that monthly content filters by year and month."""
        transactions = [
            {
                "id": "123",
                "date": "2024-01-15",
                "payee": "January Transaction",
                "amount": "-50.00",
                "currency_code": "USD",
            },
            {
                "id": "124",
                "date": "2024-02-15",
                "payee": "February Transaction",
                "amount": "-25.00",
                "currency_code": "USD",
            },
        ]

        content = generate_monthly_transactions_content(transactions, 2024, 1)

        assert "January Transaction" in content
        assert "February Transaction" not in content


class TestGenerateMainFileContent:
    """Test main file content generation."""

    def test_generate_main_file_content_basic(self):
        """Test generating basic main file content."""
        year_months = [(2024, 1), (2024, 2)]
        transaction_accounts = [
            {
                "id": "1",
                "name": "Checking",
                "institution": {"title": "Test Bank"},
                "currency_code": "USD",
            }
        ]
        categories = [{"id": "1", "title": "Food & Dining"}]

        content = generate_main_file_content(
            year_months, transaction_accounts, categories
        )

        assert "include" in content
        assert "2024/2024-01.beancount" in content
        assert "2024/2024-02.beancount" in content
        assert "Assets:Test-Bank:Checking" in content
        assert "Expenses:Food-Dining" in content

    def test_generate_main_file_content_with_balances(self):
        """Test generating main file content with account balances."""
        year_months = []
        transaction_accounts = [
            {
                "id": "1",
                "name": "Checking",
                "institution": {"title": "Test Bank"},
                "currency_code": "USD",
            }
        ]
        categories = []
        account_balances = {
            "1": [{"date": "2024-01-15T00:00:00Z", "balance": "1000.00"}]
        }

        content = generate_main_file_content(
            year_months, transaction_accounts, categories, account_balances
        )

        assert "2024-01-15 balance" in content
        assert "1000.00 USD" in content


class TestConvertTransactionToBeancount:
    """Test individual transaction conversion to beancount format."""

    def test_convert_transaction_basic(self):
        """Test converting basic transaction to beancount."""
        transaction = {
            "id": "123",
            "date": "2024-01-15",
            "payee": "Test Merchant",
            "amount": "-50.00",
            "currency_code": "USD",
            "memo": "Test transaction",
            "transaction_account": {
                "id": "1",
                "name": "Checking",
                "institution": {"title": "Test Bank"},
            },
            "category": {"id": "1", "title": "Food & Dining"},
        }

        result = convert_transaction_to_beancount(transaction)

        assert "2024-01-15" in result
        assert "Test Merchant" in result
        assert "Test transaction" in result
        assert "50.00 USD" in result
        assert "Assets:Test-Bank:Checking" in result
        assert "Expenses:Food-Dining" in result

    def test_convert_transaction_with_tags(self):
        """Test converting transaction with tags."""
        transaction = {
            "id": "123",
            "date": "2024-01-15",
            "payee": "Test Merchant",
            "amount": "-50.00",
            "currency_code": "USD",
            "labels": ["food", "dinner", "restaurant"],
        }

        result = convert_transaction_to_beancount(transaction)

        assert "#food" in result
        assert "#dinner" in result
        assert "#restaurant" in result

    def test_convert_transaction_positive_amount(self):
        """Test converting transaction with positive amount (income)."""
        transaction = {
            "id": "123",
            "date": "2024-01-15",
            "payee": "Employer",
            "amount": "1000.00",
            "currency_code": "USD",
            "transaction_account": {
                "id": "1",
                "name": "Checking",
                "institution": {"title": "Test Bank"},
            },
        }

        result = convert_transaction_to_beancount(transaction)

        # For positive amounts, account gets positive, income gets negative
        assert "1000.00 USD" in result
        assert "-1000.00 USD" in result
        assert "Income:Unknown" in result

    def test_convert_transaction_missing_fields(self):
        """Test converting transaction with missing optional fields."""
        transaction = {
            "id": "123",
            "date": "2024-01-15",
            "amount": "-50.00",
            "currency_code": "USD",
        }

        result = convert_transaction_to_beancount(transaction)

        # Should handle missing fields gracefully
        assert "2024-01-15" in result
        assert "50.00 USD" in result
        assert "Unknown" in result  # For missing payee/category


class TestAccountAndCategoryGeneration:
    """Test account and category declaration generation."""

    def test_generate_account_declarations(self):
        """Test generating account declarations."""
        transaction_accounts = [
            {
                "id": "1",
                "name": "Checking",
                "institution": {"title": "Test Bank"},
                "currency_code": "USD",
            },
            {
                "id": "2",
                "name": "Savings",
                "institution": {"title": "Another Bank"},
                "currency_code": "CAD",
            },
        ]

        content = generate_account_declarations(transaction_accounts)
        content_str = "\n".join(content)

        assert "open Assets:Test-Bank:Checking USD" in content_str
        assert "open Assets:Another-Bank:Savings CAD" in content_str

    def test_generate_category_declarations(self):
        """Test generating category declarations."""
        categories = [
            {"id": "1", "title": "Food & Dining"},
            {"id": "2", "title": "Transportation"},
            {"id": "3", "title": "Income"},
        ]

        content = generate_category_declarations(categories)
        content_str = "\n".join(content)

        assert "open Expenses:Food-Dining" in content_str
        assert "open Expenses:Transportation" in content_str
        assert (
            "open Income:Income" in content_str
        )  # Income category should use Income: prefix

    def test_get_account_name_from_transaction_account(self):
        """Test getting account name from transaction account."""
        transaction_account = {
            "name": "Checking Account",
            "institution": {"title": "Test Bank & Trust"},
        }

        result = get_account_name_from_transaction_account(transaction_account)
        assert result == "Assets:Test-Bank-Trust:Checking-Account"

    def test_get_category_account_from_category(self):
        """Test getting category account from category."""
        # Expense category
        expense_category = {"title": "Food & Dining"}
        result = get_category_account_from_category(expense_category)
        assert result == "Expenses:Food-Dining"

        # Income category
        income_category = {"title": "Salary"}
        result = get_category_account_from_category(income_category, is_income=True)
        assert result == "Income:Salary"


class TestPropertyBasedTests:
    """Property-based tests for write module functions."""

    @given(
        st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(blacklist_categories=["Cc", "Cs"]),
        )
    )
    def test_write_ledger_content_preservation(self, content):
        """Property test: written content should be preserved exactly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.beancount"
            write_ledger(content, str(file_path))

            read_content = Path(file_path).read_text()
            assert read_content == content

    @given(
        st.lists(
            st.dictionaries(
                keys=st.sampled_from(
                    ["id", "date", "payee", "amount", "currency_code"]
                ),
                values=st.text(min_size=1, max_size=50),
                min_size=1,
            ),
            min_size=0,
            max_size=10,
        )
    )
    def test_generate_transactions_content_properties(self, transactions):
        """Property test: transaction content generation should not fail."""
        try:
            content = generate_transactions_content(transactions)
            assert isinstance(content, str)
        except (KeyError, ValueError, TypeError):
            # Expected for malformed transaction data
            pass

    @given(
        st.integers(min_value=2000, max_value=2030),
        st.integers(min_value=1, max_value=12),
    )
    def test_generate_monthly_content_date_filtering(self, year, month):
        """Property test: monthly content should only include specified month."""
        transactions = [
            {
                "id": "123",
                "date": f"{year}-{month:02d}-15",
                "payee": "Test",
                "amount": "-50.00",
                "currency_code": "USD",
            },
            {
                "id": "124",
                "date": f"{year}-{(month % 12) + 1:02d}-15",  # Different month
                "payee": "Other",
                "amount": "-25.00",
                "currency_code": "USD",
            },
        ]

        content = generate_monthly_transactions_content(transactions, year, month)

        # Should contain the transaction from the specified month
        assert "Test" in content
        # Should not contain transaction from different month
        assert "Other" not in content
