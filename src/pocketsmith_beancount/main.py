import argparse
import sys
from dotenv import load_dotenv

from .pocketsmith_client import PocketSmithClient
from .beancount_converter import BeancountConverter
from .file_writer import BeancountFileWriter


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Convert PocketSmith transactions to Beancount format"
    )
    parser.add_argument(
        "--start-date", type=str, help="Start date for transactions (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", type=str, help="End date for transactions (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--output-dir", type=str, help="Output directory for Beancount files"
    )
    parser.add_argument(
        "--filename", type=str, help="Output filename (without extension)"
    )
    parser.add_argument(
        "--account-id", type=int, help="Specific account ID to fetch transactions for"
    )

    args = parser.parse_args()

    try:
        client = PocketSmithClient()
        converter = BeancountConverter()
        writer = BeancountFileWriter(args.output_dir)

        print("Connecting to PocketSmith API...")
        user = client.get_user()
        print(f"Connected as: {user.get('login', 'Unknown User')}")

        print("Fetching transaction accounts...")
        transaction_accounts = client.get_transaction_accounts()
        print(f"Found {len(transaction_accounts)} transaction accounts")

        print("Fetching categories...")
        categories = client.get_categories()
        print(f"Found {len(categories)} categories")

        print("Fetching transactions...")
        transactions = client.get_transactions(
            start_date=args.start_date,
            end_date=args.end_date,
            account_id=args.account_id,
        )
        print(f"Found {len(transactions)} transactions")

        if not transactions:
            print("No transactions found for the specified criteria.")
            return

        print("Converting to Beancount format...")
        beancount_content = converter.convert_transactions(
            transactions, transaction_accounts, categories
        )

        print("Writing to file...")
        output_file = writer.write_beancount_file(beancount_content, args.filename)

        print(f"Successfully wrote {len(transactions)} transactions to: {output_file}")
        print(f"Output directory: {writer.get_output_directory()}")

    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
