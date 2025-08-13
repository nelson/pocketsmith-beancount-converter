"""Tests for beancount.read module functionality."""

import pytest
import tempfile
from pathlib import Path
from decimal import Decimal
from datetime import date
from unittest.mock import Mock
from hypothesis import given, strategies as st

from beancount.core import data
from beancount.core.data import Transaction, Posting, Amount

from src.beancount.read import (
    read_ledger,
    parse_transactions_from_file,
    parse_transaction_entry,
    extract_accounts_from_entries,
    extract_commodities_from_entries,
    find_transactions_by_id,
    extract_balance_directives,
    get_transaction_by_id,
)
from src.beancount.common import BeancountError


class TestReadLedger:
    """Test ledger file reading functionality."""

    def test_read_valid_beancount_file(self):
        """Test reading a valid beancount file."""
        beancount_content = """
        1900-01-01 open Assets:Checking USD
        
        2024-01-15 * "Test Transaction"
          Assets:Checking  100.00 USD
          Expenses:Food   -100.00 USD
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".beancount", delete=False
        ) as f:
            f.write(beancount_content)
            f.flush()

            try:
                entries, errors, options_map = read_ledger(f.name)

                assert isinstance(entries, list)
                assert isinstance(errors, list)
                assert isinstance(options_map, dict)
                assert len(entries) >= 2  # At least open and transaction
            finally:
                Path(f.name).unlink()

    def test_read_nonexistent_file(self):
        """Test reading a nonexistent file raises BeancountError."""
        with pytest.raises(BeancountError) as exc_info:
            read_ledger("/nonexistent/path/file.beancount")

        assert "Failed to load beancount file" in str(exc_info.value)

    def test_read_malformed_beancount_file(self):
        """Test reading a malformed beancount file."""
        malformed_content = """
        invalid beancount syntax here
        2024-01-15 * "Test"
          Missing posting amounts
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".beancount", delete=False
        ) as f:
            f.write(malformed_content)
            f.flush()

            try:
                entries, errors, options_map = read_ledger(f.name)
                # Should not raise exception but may have errors
                assert isinstance(entries, list)
                assert isinstance(errors, list)
            finally:
                Path(f.name).unlink()

    def test_read_empty_file(self):
        """Test reading an empty beancount file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".beancount", delete=False
        ) as f:
            f.write("")
            f.flush()

            try:
                entries, errors, options_map = read_ledger(f.name)
                assert entries == []
                assert isinstance(errors, list)
                assert isinstance(options_map, dict)
            finally:
                Path(f.name).unlink()


class TestParseTransactionsFromFile:
    """Test transaction parsing from beancount files."""

    def test_parse_transactions_from_valid_file(self):
        """Test parsing transactions from a valid file."""
        beancount_content = """
        1900-01-01 open Assets:Checking USD
        1900-01-01 open Expenses:Food USD
        
        2024-01-15 * "Grocery Store" "Food shopping"
          id: "123"
          Assets:Checking  -50.00 USD
          Expenses:Food     50.00 USD
        
        2024-01-16 * "Restaurant"
          id: "124"
          Assets:Checking  -25.00 USD
          Expenses:Food     25.00 USD
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".beancount", delete=False
        ) as f:
            f.write(beancount_content)
            f.flush()

            try:
                transactions = parse_transactions_from_file(f.name)

                assert len(transactions) == 2
                assert all(isinstance(t, dict) for t in transactions)
                assert transactions[0]["id"] == "123"
                assert transactions[1]["id"] == "124"
            finally:
                Path(f.name).unlink()

    def test_parse_transactions_no_transactions(self):
        """Test parsing file with no transactions."""
        beancount_content = """
        1900-01-01 open Assets:Checking USD
        1900-01-01 commodity USD
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".beancount", delete=False
        ) as f:
            f.write(beancount_content)
            f.flush()

            try:
                transactions = parse_transactions_from_file(f.name)
                assert transactions == []
            finally:
                Path(f.name).unlink()


class TestParseTransactionEntry:
    """Test individual transaction entry parsing."""

    def test_parse_basic_transaction(self):
        """Test parsing a basic transaction entry."""
        # Create a mock transaction entry
        transaction = Transaction(
            meta={"id": "123", "last_modified": "2024-01-15T10:00:00Z"},
            date=date(2024, 1, 15),
            flag="*",
            payee="Grocery Store",
            narration="Food shopping",
            tags=frozenset(["food"]),
            links=frozenset(),
            postings=[
                Posting(
                    account="Assets:Checking",
                    units=Amount(Decimal("-50.00"), "USD"),
                    cost=None,
                    price=None,
                    flag=None,
                    meta={},
                ),
                Posting(
                    account="Expenses:Food",
                    units=Amount(Decimal("50.00"), "USD"),
                    cost=None,
                    price=None,
                    flag=None,
                    meta={},
                ),
            ],
        )

        result = parse_transaction_entry(transaction)

        assert result["id"] == "123"
        assert result["date"] == "2024-01-15"
        assert result["flag"] == "*"
        assert result["payee"] == "Grocery Store"
        assert result["narration"] == "Food shopping"
        assert "food" in result["tags"]
        assert len(result["postings"]) == 2
        assert result["last_modified"] == "2024-01-15T10:00:00Z"

    def test_parse_transaction_without_metadata(self):
        """Test parsing transaction without metadata."""
        transaction = Transaction(
            meta={},
            date=date(2024, 1, 15),
            flag="*",
            payee=None,
            narration="Simple transaction",
            tags=frozenset(),
            links=frozenset(),
            postings=[],
        )

        result = parse_transaction_entry(transaction)

        assert result["id"] is None
        assert result["payee"] == ""
        assert result["tags"] == []
        assert result["postings"] == []

    def test_parse_transaction_with_cost_and_price(self):
        """Test parsing transaction with cost and price information."""
        transaction = Transaction(
            meta={"id": "123"},
            date=date(2024, 1, 15),
            flag="*",
            payee="Exchange",
            narration="Currency exchange",
            tags=frozenset(),
            links=frozenset(),
            postings=[
                Posting(
                    account="Assets:USD",
                    units=Amount(Decimal("100.00"), "USD"),
                    cost=Amount(Decimal("130.00"), "CAD"),
                    price=Amount(Decimal("1.30"), "CAD"),
                    flag=None,
                    meta={},
                )
            ],
        )

        result = parse_transaction_entry(transaction)
        posting = result["postings"][0]

        assert posting["cost"]["number"] == Decimal("130.00")
        assert posting["cost"]["currency"] == "CAD"
        assert posting["price"]["number"] == Decimal("1.30")
        assert posting["price"]["currency"] == "CAD"

    def test_parse_malformed_transaction(self):
        """Test parsing a malformed transaction returns None."""
        # Create an object that will cause an exception during parsing
        malformed_transaction = Mock()
        malformed_transaction.date = None  # This should cause an error

        result = parse_transaction_entry(malformed_transaction)
        assert result is None


class TestExtractAccountsFromEntries:
    """Test account extraction from beancount entries."""

    def test_extract_accounts_basic(self):
        """Test extracting accounts from entries."""
        open_entry = data.Open(
            meta={},
            date=date(2024, 1, 1),
            account="Assets:Checking",
            currencies=["USD", "CAD"],
            booking=None,
        )

        accounts = extract_accounts_from_entries([open_entry])

        assert len(accounts) == 1
        account = accounts[0]
        assert account["name"] == "Assets:Checking"
        assert account["open_date"] == "2024-01-01"
        assert set(account["currencies"]) == {"USD", "CAD"}

    def test_extract_accounts_with_metadata(self):
        """Test extracting accounts with metadata."""
        open_entry = data.Open(
            meta={"description": "Main checking account"},
            date=date(2024, 1, 1),
            account="Assets:Checking",
            currencies=["USD"],
            booking=None,
        )

        accounts = extract_accounts_from_entries([open_entry])
        account = accounts[0]

        assert account["meta"]["description"] == "Main checking account"

    def test_extract_no_accounts(self):
        """Test extracting accounts when none exist."""
        # Create some non-account entries
        commodity_entry = data.Commodity(meta={}, date=date(2024, 1, 1), currency="USD")

        accounts = extract_accounts_from_entries([commodity_entry])
        assert accounts == []


class TestExtractCommoditiesFromEntries:
    """Test commodity extraction from beancount entries."""

    def test_extract_commodities_basic(self):
        """Test extracting commodities from entries."""
        commodity_entry = data.Commodity(
            meta={"precision": "2"}, date=date(2024, 1, 1), currency="USD"
        )

        commodities = extract_commodities_from_entries([commodity_entry])

        assert len(commodities) == 1
        commodity = commodities[0]
        assert commodity["currency"] == "USD"
        assert commodity["date"] == "2024-01-01"
        assert commodity["meta"]["precision"] == "2"

    def test_extract_no_commodities(self):
        """Test extracting commodities when none exist."""
        open_entry = data.Open(
            meta={},
            date=date(2024, 1, 1),
            account="Assets:Checking",
            currencies=["USD"],
            booking=None,
        )

        commodities = extract_commodities_from_entries([open_entry])
        assert commodities == []


class TestFindTransactionsById:
    """Test finding transactions by ID."""

    def test_find_transactions_by_id_success(self):
        """Test finding transactions by ID when they exist."""
        transaction1 = Transaction(
            meta={"id": "123"},
            date=date(2024, 1, 15),
            flag="*",
            payee="Test",
            narration="Test transaction",
            tags=frozenset(),
            links=frozenset(),
            postings=[],
        )

        transaction2 = Transaction(
            meta={"id": "124"},
            date=date(2024, 1, 16),
            flag="*",
            payee="Test2",
            narration="Test transaction 2",
            tags=frozenset(),
            links=frozenset(),
            postings=[],
        )

        entries = [transaction1, transaction2]
        found = find_transactions_by_id(entries, "123")

        assert len(found) == 1
        assert found[0].meta["id"] == "123"

    def test_find_transactions_by_id_not_found(self):
        """Test finding transactions by ID when they don't exist."""
        transaction = Transaction(
            meta={"id": "123"},
            date=date(2024, 1, 15),
            flag="*",
            payee="Test",
            narration="Test transaction",
            tags=frozenset(),
            links=frozenset(),
            postings=[],
        )

        entries = [transaction]
        found = find_transactions_by_id(entries, "999")

        assert found == []

    def test_find_transactions_multiple_matches(self):
        """Test finding transactions when multiple have same ID."""
        transaction1 = Transaction(
            meta={"id": "123"},
            date=date(2024, 1, 15),
            flag="*",
            payee="Test1",
            narration="Test transaction 1",
            tags=frozenset(),
            links=frozenset(),
            postings=[],
        )

        transaction2 = Transaction(
            meta={"id": "123"},
            date=date(2024, 1, 16),
            flag="*",
            payee="Test2",
            narration="Test transaction 2",
            tags=frozenset(),
            links=frozenset(),
            postings=[],
        )

        entries = [transaction1, transaction2]
        found = find_transactions_by_id(entries, "123")

        assert len(found) == 2
        assert all(t.meta["id"] == "123" for t in found)


class TestExtractBalanceDirectives:
    """Test balance directive extraction."""

    def test_extract_balance_directives_basic(self):
        """Test extracting balance directives."""
        balance_entry = data.Balance(
            meta={"tolerance": "0.01"},
            date=date(2024, 1, 15),
            account="Assets:Checking",
            amount=Amount(Decimal("1000.00"), "USD"),
            tolerance=None,
            diff_amount=None,
        )

        balances = extract_balance_directives([balance_entry])

        assert len(balances) == 1
        balance = balances[0]
        assert balance["account"] == "Assets:Checking"
        assert balance["amount"] == Decimal("1000.00")
        assert balance["currency"] == "USD"
        assert balance["date"] == "2024-01-15"

    def test_extract_balance_directives_no_amount(self):
        """Test extracting balance directives without amount."""
        balance_entry = data.Balance(
            meta={},
            date=date(2024, 1, 15),
            account="Assets:Checking",
            amount=None,
            tolerance=None,
            diff_amount=None,
        )

        balances = extract_balance_directives([balance_entry])
        balance = balances[0]

        assert balance["amount"] is None
        assert balance["currency"] is None


class TestGetTransactionById:
    """Test getting specific transaction by ID from file."""

    def test_get_transaction_by_id_success(self):
        """Test getting transaction by ID from file."""
        beancount_content = """
        2024-01-15 * "Test Transaction"
          id: "123"
          Assets:Checking  -50.00 USD
          Expenses:Food     50.00 USD
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".beancount", delete=False
        ) as f:
            f.write(beancount_content)
            f.flush()

            try:
                transaction = get_transaction_by_id(f.name, "123")

                assert transaction is not None
                assert transaction["id"] == "123"
                assert transaction["narration"] == "Test Transaction"
            finally:
                Path(f.name).unlink()

    def test_get_transaction_by_id_not_found(self):
        """Test getting transaction by ID when not found."""
        beancount_content = """
        2024-01-15 * "Test Transaction"
          id: "123"
          Assets:Checking  -50.00 USD
          Expenses:Food     50.00 USD
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".beancount", delete=False
        ) as f:
            f.write(beancount_content)
            f.flush()

            try:
                transaction = get_transaction_by_id(f.name, "999")
                assert transaction is None
            finally:
                Path(f.name).unlink()

    @given(
        st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(categories=["Nd", "Lu", "Ll"]),
        )
    )
    def test_get_transaction_by_id_property(self, transaction_id):
        """Property test: getting transaction by ID should be consistent."""
        beancount_content = f'''
        2024-01-15 * "Test Transaction"
          id: "{transaction_id}"
          Assets:Checking  -50.00 USD
          Expenses:Food     50.00 USD
        '''

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".beancount", delete=False
        ) as f:
            f.write(beancount_content)
            f.flush()

            try:
                transaction = get_transaction_by_id(f.name, transaction_id)
                if transaction is not None:
                    assert transaction["id"] == transaction_id
            finally:
                Path(f.name).unlink()
