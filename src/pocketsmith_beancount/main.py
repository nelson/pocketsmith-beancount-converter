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
        "--hierarchical",
        action="store_true",
        help="Use hierarchical file structure with yearly folders and monthly files",
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

        print("Extracting account balances...")
        account_balances = {}
        for transaction_account in transaction_accounts:
            transaction_account_id = transaction_account.get("id")
            current_balance = transaction_account.get("current_balance")
            current_balance_date = transaction_account.get("current_balance_date")

            if (
                transaction_account_id
                and current_balance is not None
                and current_balance_date
            ):
                account_balances[transaction_account_id] = [
                    {
                        "date": f"{current_balance_date}T00:00:00Z",
                        "balance": str(current_balance),
                    }
                ]
        print(f"Extracted balances for {len(account_balances)} accounts")

        print("Converting to Beancount format...")

        if args.hierarchical:
            print("Using hierarchical file structure...")
            written_files = writer.write_hierarchical_beancount_files(
                transactions,
                transaction_accounts,
                categories,
                account_balances,
                converter,
            )

            print(
                f"Successfully wrote {len(transactions)} transactions to hierarchical structure:"
            )
            for relative_path, full_path in written_files.items():
                print(f"  {relative_path}")
            print(f"Output directory: {writer.get_output_directory()}")
        else:
            beancount_content = converter.convert_transactions(
                transactions, transaction_accounts, categories, account_balances
            )

            print("Writing to file...")
            output_file = writer.write_beancount_file(beancount_content, args.filename)

            print(
                f"Successfully wrote {len(transactions)} transactions to: {output_file}"
            )
            print(f"Output directory: {writer.get_output_directory()}")

    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
