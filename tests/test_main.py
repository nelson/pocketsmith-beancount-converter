import pytest
import sys
from unittest.mock import Mock, patch
from src.pocketsmith_beancount.main import main


class TestMain:
    @patch("src.pocketsmith_beancount.main.load_dotenv")
    @patch("src.pocketsmith_beancount.main.argparse.ArgumentParser.parse_args")
    def test_main_argument_parsing(self, mock_parse_args, mock_load_dotenv):
        """Test CLI argument parsing"""
        mock_args = Mock()
        mock_args.start_date = "2024-01-01"
        mock_args.end_date = "2024-01-31"
        mock_args.output_dir = "/tmp/output"
        mock_args.filename = "test"
        mock_args.account_id = 123
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
                    # Mock the client instance and its methods
                    mock_client = Mock()
                    mock_client.get_user.return_value = {"login": "test_user"}
                    mock_client.get_transaction_accounts.return_value = []
                    mock_client.get_categories.return_value = []
                    mock_client.get_transactions.return_value = [
                        {"id": 1, "amount": "10.00"}
                    ]  # Non-empty for file write
                    mock_client_class.return_value = mock_client

                    # Mock converter and writer
                    mock_converter = Mock()
                    mock_converter.convert_transactions.return_value = "test content"
                    mock_converter_class.return_value = mock_converter

                    mock_writer = Mock()
                    mock_writer.write_beancount_file.return_value = (
                        "/tmp/output/test.beancount"
                    )
                    mock_writer.get_output_directory.return_value = "/tmp/output"
                    mock_writer_class.return_value = mock_writer

                    main()

                    # Verify arguments were passed correctly
                    mock_client.get_transactions.assert_called_once_with(
                        start_date="2024-01-01",
                        end_date="2024-01-31",
                        account_id=123,
                    )
                    mock_writer_class.assert_called_once_with("/tmp/output")
                    mock_writer.write_beancount_file.assert_called_once_with(
                        "test content", "test"
                    )

    @patch("src.pocketsmith_beancount.main.load_dotenv")
    @patch("src.pocketsmith_beancount.main.argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    def test_main_no_transactions_found(
        self, mock_print, mock_parse_args, mock_load_dotenv
    ):
        """Test behavior when no transactions are returned"""
        mock_args = Mock()
        mock_args.start_date = None
        mock_args.end_date = None
        mock_args.output_dir = None
        mock_args.filename = None
        mock_args.account_id = None
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
        mock_args.start_date = "2024-01-01"
        mock_args.end_date = "2024-01-31"
        mock_args.output_dir = None
        mock_args.filename = None
        mock_args.account_id = None
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
                        {"id": 1, "name": "Checking"}
                    ]
                    mock_client.get_categories.return_value = [
                        {"id": 1, "title": "Groceries"}
                    ]
                    mock_client.get_transactions.return_value = [
                        {"id": 1, "amount": "10.00"},
                        {"id": 2, "amount": "20.00"},
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
                    mock_converter.convert_transactions.assert_called_once_with(
                        [{"id": 1, "amount": "10.00"}, {"id": 2, "amount": "20.00"}],
                        [{"id": 1, "name": "Checking"}],
                        [{"id": 1, "title": "Groceries"}],
                    )
