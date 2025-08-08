import pytest
import sys
from unittest.mock import Mock, patch
from src.pocketsmith_beancount.main import main


class TestMain:
    @patch("src.pocketsmith_beancount.main.load_dotenv")
    @patch("src.pocketsmith_beancount.main.argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    def test_main_argument_parsing(self, mock_print, mock_parse_args, mock_load_dotenv):
        """Test CLI argument parsing"""
        mock_args = Mock()
        mock_args.sync = False
        mock_args.dry_run = False
        mock_args.sync_verbose = False
        mock_args.start_date = "2024-01-01"
        mock_args.end_date = "2024-01-31"
        mock_args.output_dir = None
        mock_args.filename = None
        mock_args.account_id = None
        mock_args.hierarchical = False
        mock_parse_args.return_value = mock_args

        with patch(
            "src.pocketsmith_beancount.main.PocketSmithClient"
        ) as mock_client_class:
            with patch(
                "src.pocketsmith_beancount.main.BeancountConverter"
            ) as mock_converter_class:
                with patch(
                    "src.pocketsmith_beancount.main.BeancountFileWriter"
                ) as mock_writer_class:
                    # Mock the client to return empty transactions
                    mock_client = Mock()
                    mock_client.get_user.return_value = {"login": "test_user"}
                    mock_client.get_transaction_accounts.return_value = []
                    mock_client.get_categories.return_value = []
                    mock_client.get_transactions.return_value = []  # Empty list
                    mock_client_class.return_value = mock_client

                    mock_converter_class.return_value = Mock()
                    mock_writer_class.return_value = Mock()

                    main()

                    # Should print message about no transactions
                    mock_print.assert_any_call(
                        "No transactions found for the specified criteria."
                    )

    @patch("src.pocketsmith_beancount.main.load_dotenv")
    @patch("src.pocketsmith_beancount.main.argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    def test_main_api_key_missing(self, mock_print, mock_parse_args, mock_load_dotenv):
        """Test error handling for missing API key"""
        mock_args = Mock()
        mock_args.sync = False
        mock_args.dry_run = False
        mock_args.sync_verbose = False
        mock_args.hierarchical = False
        mock_args.start_date = None
        mock_args.end_date = None
        mock_args.account_id = None
        mock_args.output_dir = None
        mock_args.filename = None
        mock_parse_args.return_value = mock_args

        with patch(
            "src.pocketsmith_beancount.main.PocketSmithClient"
        ) as mock_client_class:
            # Mock PocketSmithClient to raise ValueError for missing API key
            mock_client_class.side_effect = ValueError(
                "PocketSmith API key is required"
            )

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            mock_print.assert_any_call(
                "Configuration error: PocketSmith API key is required", file=sys.stderr
            )

    @patch("src.pocketsmith_beancount.main.load_dotenv")
    @patch("src.pocketsmith_beancount.main.argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    def test_main_api_error_handling(
        self, mock_print, mock_parse_args, mock_load_dotenv
    ):
        """Test handling of API errors"""
        mock_args = Mock()
        mock_args.sync = False
        mock_args.dry_run = False
        mock_args.sync_verbose = False
        mock_args.hierarchical = False
        mock_args.start_date = None
        mock_args.end_date = None
        mock_args.account_id = None
        mock_args.output_dir = None
        mock_args.filename = None
        mock_parse_args.return_value = mock_args

        with patch(
            "src.pocketsmith_beancount.main.PocketSmithClient"
        ) as mock_client_class:
            with patch(
                "src.pocketsmith_beancount.main.BeancountConverter"
            ) as mock_converter_class:
                with patch(
                    "src.pocketsmith_beancount.main.BeancountFileWriter"
                ) as mock_writer_class:
                    # Mock the client to raise an API error
                    mock_client = Mock()
                    mock_client.get_user.side_effect = Exception(
                        "API connection failed"
                    )
                    mock_client_class.return_value = mock_client

                    mock_converter_class.return_value = Mock()
                    mock_writer_class.return_value = Mock()

                    with pytest.raises(SystemExit) as exc_info:
                        main()

                    assert exc_info.value.code == 1
                    mock_print.assert_any_call(
                        "Error: API connection failed", file=sys.stderr
                    )

    @patch("src.pocketsmith_beancount.main.load_dotenv")
    @patch("src.pocketsmith_beancount.main.argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    def test_main_file_write_error(self, mock_print, mock_parse_args, mock_load_dotenv):
        """Test handling of file write errors"""
        mock_args = Mock()
        mock_args.hierarchical = False
        mock_args.sync = False
        mock_args.dry_run = False
        mock_args.sync_verbose = False
        mock_args.start_date = None
        mock_args.end_date = None
        mock_args.account_id = None
        mock_args.output_dir = None
        mock_args.filename = None
        mock_parse_args.return_value = mock_args

        with patch(
            "src.pocketsmith_beancount.main.PocketSmithClient"
        ) as mock_client_class:
            with patch(
                "src.pocketsmith_beancount.main.BeancountConverter"
            ) as mock_converter_class:
                with patch(
                    "src.pocketsmith_beancount.main.BeancountFileWriter"
                ) as mock_writer_class:
                    # Mock successful API calls
                    mock_client = Mock()
                    mock_client.get_user.return_value = {"login": "test_user"}
                    mock_client.get_transaction_accounts.return_value = []
                    mock_client.get_categories.return_value = []
                    mock_client.get_transactions.return_value = [
                        {"id": 1, "amount": "10.00"}
                    ]
                    mock_client_class.return_value = mock_client

                    mock_converter = Mock()
                    mock_converter.convert_transactions.return_value = "test content"
                    mock_converter_class.return_value = mock_converter

                    # Mock file writer to raise an error
                    mock_writer = Mock()
                    mock_writer.write_beancount_file.side_effect = IOError(
                        "Permission denied"
                    )
                    mock_writer_class.return_value = mock_writer

                    with pytest.raises(SystemExit) as exc_info:
                        main()

                    assert exc_info.value.code == 1
                    mock_print.assert_any_call(
                        "Error: Permission denied", file=sys.stderr
                    )

    @patch("src.pocketsmith_beancount.main.load_dotenv")
    @patch("src.pocketsmith_beancount.main.argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    def test_main_success_flow(self, mock_print, mock_parse_args, mock_load_dotenv):
        """Test successful end-to-end execution (mocked)"""
        mock_args = Mock()
        mock_args.sync = False
        mock_args.dry_run = False
        mock_args.sync_verbose = False
        mock_args.start_date = "2024-01-01"
        mock_args.end_date = "2024-01-31"
        mock_args.output_dir = None
        mock_args.filename = None
        mock_args.account_id = None
        mock_args.hierarchical = False
        mock_parse_args.return_value = mock_args

        with patch(
            "src.pocketsmith_beancount.main.PocketSmithClient"
        ) as mock_client_class:
            with patch(
                "src.pocketsmith_beancount.main.BeancountConverter"
            ) as mock_converter_class:
                with patch(
                    "src.pocketsmith_beancount.main.BeancountFileWriter"
                ) as mock_writer_class:
                    # Mock successful API calls
                    mock_client = Mock()
                    mock_client.get_user.return_value = {"login": "test_user"}
                    mock_client.get_transaction_accounts.return_value = [
                        {"id": 1, "name": "Checking", "account_id": 101}
                    ]
                    mock_client.get_categories.return_value = [
                        {"id": 1, "title": "Groceries"}
                    ]
                    mock_client.get_transactions.return_value = [
                        {"id": 1, "amount": "10.00"},
                        {"id": 2, "amount": "20.00"},
                    ]
                    mock_client.get_account_balances.return_value = []
                    mock_client_class.return_value = mock_client

                    mock_converter = Mock()
                    mock_converter.convert_transactions.return_value = (
                        "beancount content"
                    )
                    mock_converter_class.return_value = mock_converter

                    mock_writer = Mock()
                    mock_writer.write_beancount_file.return_value = (
                        "/output/transactions.beancount"
                    )
                    mock_writer.get_output_directory.return_value = "/output"
                    mock_writer_class.return_value = mock_writer

                    main()

                    # Verify success messages were printed
                    mock_print.assert_any_call("Connected as: test_user")
                    mock_print.assert_any_call("Found 1 transaction accounts")
                    mock_print.assert_any_call("Found 1 categories")
                    mock_print.assert_any_call("Found 2 transactions")
                    mock_print.assert_any_call(
                        "Successfully wrote 2 transactions to: /output/transactions.beancount"
                    )
                    mock_print.assert_any_call("Output directory: /output")

                    # Verify the conversion was called with correct parameters
                    mock_converter.convert_transactions.assert_called_once()
                    call_args = mock_converter.convert_transactions.call_args
                    assert (
                        len(call_args[0]) == 4
                    )  # transactions, accounts, categories, balances
                    assert len(call_args[0][0]) == 2  # 2 transactions
                    assert len(call_args[0][1]) == 1  # 1 account
                    assert len(call_args[0][2]) == 1  # 1 category
                    assert isinstance(call_args[0][3], dict)  # balances dict

    @patch("src.pocketsmith_beancount.main.load_dotenv")
    @patch("src.pocketsmith_beancount.main.argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    def test_main_with_balance_fetching(
        self, mock_print, mock_parse_args, mock_load_dotenv
    ) -> None:
        """Test successful balance extraction from transaction accounts"""
        mock_args = Mock()
        mock_args.sync = False
        mock_args.dry_run = False
        mock_args.sync_verbose = False
        mock_args.start_date = "2024-01-01"
        mock_args.end_date = "2024-01-31"
        mock_args.output_dir = None
        mock_args.filename = None
        mock_args.account_id = None
        mock_args.hierarchical = False
        mock_parse_args.return_value = mock_args

        with patch(
            "src.pocketsmith_beancount.main.PocketSmithClient"
        ) as mock_client_class:
            with patch(
                "src.pocketsmith_beancount.main.BeancountConverter"
            ) as mock_converter_class:
                with patch(
                    "src.pocketsmith_beancount.main.BeancountFileWriter"
                ) as mock_writer_class:
                    # Mock successful API calls with balance data in transaction accounts
                    mock_client = Mock()
                    mock_client.get_user.return_value = {"login": "test_user"}
                    mock_client.get_transaction_accounts.return_value = [
                        {
                            "id": 1,
                            "name": "Checking",
                            "account_id": 101,
                            "current_balance": "1000.00",
                            "current_balance_date": "2024-01-01T00:00:00Z",
                        },
                        {
                            "id": 2,
                            "name": "Savings",
                            "account_id": 102,
                            "current_balance": "500.00",
                            "current_balance_date": "2024-01-01T00:00:00Z",
                        },
                    ]
                    mock_client.get_categories.return_value = [
                        {"id": 1, "title": "Groceries"}
                    ]
                    mock_client.get_transactions.return_value = [
                        {"id": 1, "amount": "10.00"}
                    ]
                    mock_client_class.return_value = mock_client

                    mock_converter = Mock()
                    mock_converter.convert_transactions.return_value = (
                        "beancount content"
                    )
                    mock_converter_class.return_value = mock_converter

                    mock_writer = Mock()
                    mock_writer.write_beancount_file.return_value = (
                        "/output/transactions.beancount"
                    )
                    mock_writer.get_output_directory.return_value = "/output"
                    mock_writer_class.return_value = mock_writer

                    main()

                    # Verify balance extraction message
                    mock_print.assert_any_call("Extracting account balances...")
                    mock_print.assert_any_call("Extracted balances for 2 accounts")

                    # Verify conversion was called with balance data
                    mock_converter.convert_transactions.assert_called_once()
                    call_args = mock_converter.convert_transactions.call_args
                    assert (
                        len(call_args[0]) == 4
                    )  # transactions, accounts, categories, balances
                    assert len(call_args[0][0]) == 1  # 1 transaction
                    assert len(call_args[0][1]) == 2  # 2 accounts
                    assert len(call_args[0][2]) == 1  # 1 category
                    balances_dict = call_args[0][3]
                    assert len(balances_dict) == 2  # 2 accounts with balances
                    assert 1 in balances_dict and 2 in balances_dict

    @patch("src.pocketsmith_beancount.main.load_dotenv")
    @patch("src.pocketsmith_beancount.main.argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    def test_main_balance_fetch_error(
        self, mock_print, mock_parse_args, mock_load_dotenv
    ) -> None:
        """Test handling of missing balance data in transaction accounts"""
        mock_args = Mock()
        mock_args.sync = False
        mock_args.dry_run = False
        mock_args.sync_verbose = False
        mock_args.start_date = "2024-01-01"
        mock_args.end_date = "2024-01-31"
        mock_args.output_dir = None
        mock_args.filename = None
        mock_args.account_id = None
        mock_args.hierarchical = False
        mock_parse_args.return_value = mock_args

        with patch(
            "src.pocketsmith_beancount.main.PocketSmithClient"
        ) as mock_client_class:
            with patch(
                "src.pocketsmith_beancount.main.BeancountConverter"
            ) as mock_converter_class:
                with patch(
                    "src.pocketsmith_beancount.main.BeancountFileWriter"
                ) as mock_writer_class:
                    # Mock API calls with missing balance data
                    mock_client = Mock()
                    mock_client.get_user.return_value = {"login": "test_user"}
                    mock_client.get_transaction_accounts.return_value = [
                        {
                            "id": 1,
                            "name": "Checking",
                            "account_id": 101,
                        }  # No balance fields
                    ]
                    mock_client.get_categories.return_value = [
                        {"id": 1, "title": "Groceries"}
                    ]
                    mock_client.get_transactions.return_value = [
                        {"id": 1, "amount": "10.00"}
                    ]
                    mock_client_class.return_value = mock_client

                    mock_converter = Mock()
                    mock_converter.convert_transactions.return_value = (
                        "beancount content"
                    )
                    mock_converter_class.return_value = mock_converter

                    mock_writer = Mock()
                    mock_writer.write_beancount_file.return_value = (
                        "/output/transactions.beancount"
                    )
                    mock_writer.get_output_directory.return_value = "/output"
                    mock_writer_class.return_value = mock_writer

                    main()

                    # Verify balance extraction message
                    mock_print.assert_any_call("Extracting account balances...")
                    mock_print.assert_any_call("Extracted balances for 0 accounts")

                    # Verify conversion was called with empty balance data
                    mock_converter.convert_transactions.assert_called_once()
                    call_args = mock_converter.convert_transactions.call_args
                    assert (
                        len(call_args[0]) == 4
                    )  # transactions, accounts, categories, balances
                    balances_dict = call_args[0][3]
                    assert len(balances_dict) == 0  # Empty due to missing data

    @patch("src.pocketsmith_beancount.main.load_dotenv")
    @patch("src.pocketsmith_beancount.main.argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    def test_main_balance_fetch_partial_failure(
        self, mock_print, mock_parse_args, mock_load_dotenv
    ) -> None:
        """Test when some accounts have balance data and others don't"""
        mock_args = Mock()
        mock_args.sync = False
        mock_args.dry_run = False
        mock_args.sync_verbose = False
        mock_args.start_date = "2024-01-01"
        mock_args.end_date = "2024-01-31"
        mock_args.output_dir = None
        mock_args.filename = None
        mock_args.account_id = None
        mock_args.hierarchical = False
        mock_parse_args.return_value = mock_args

        with patch(
            "src.pocketsmith_beancount.main.PocketSmithClient"
        ) as mock_client_class:
            with patch(
                "src.pocketsmith_beancount.main.BeancountConverter"
            ) as mock_converter_class:
                with patch(
                    "src.pocketsmith_beancount.main.BeancountFileWriter"
                ) as mock_writer_class:
                    # Mock API calls with partial balance data
                    mock_client = Mock()
                    mock_client.get_user.return_value = {"login": "test_user"}
                    mock_client.get_transaction_accounts.return_value = [
                        {
                            "id": 1,
                            "name": "Checking",
                            "account_id": 101,
                            "current_balance": "1000.00",
                            "current_balance_date": "2024-01-01T00:00:00Z",
                        },
                        {
                            "id": 2,
                            "name": "Savings",
                            "account_id": 102,
                        },  # No balance data
                    ]
                    mock_client.get_categories.return_value = [
                        {"id": 1, "title": "Groceries"}
                    ]
                    mock_client.get_transactions.return_value = [
                        {"id": 1, "amount": "10.00"}
                    ]
                    mock_client_class.return_value = mock_client

                    mock_converter = Mock()
                    mock_converter.convert_transactions.return_value = (
                        "beancount content"
                    )
                    mock_converter_class.return_value = mock_converter

                    mock_writer = Mock()
                    mock_writer.write_beancount_file.return_value = (
                        "/output/transactions.beancount"
                    )
                    mock_writer.get_output_directory.return_value = "/output"
                    mock_writer_class.return_value = mock_writer

                    main()

                    # Verify balance extraction message
                    mock_print.assert_any_call("Extracting account balances...")
                    mock_print.assert_any_call("Extracted balances for 1 accounts")

                    # Verify conversion was called with partial balance data
                    mock_converter.convert_transactions.assert_called_once()
                    call_args = mock_converter.convert_transactions.call_args
                    assert (
                        len(call_args[0]) == 4
                    )  # transactions, accounts, categories, balances
                    balances_dict = call_args[0][3]
                    assert len(balances_dict) == 1  # Only 1 account succeeded
                    assert 1 in balances_dict  # Account 1 succeeded
                    assert 2 not in balances_dict  # Account 2 failed
