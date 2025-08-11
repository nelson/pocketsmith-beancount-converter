import argparse
import sys
import logging
from typing import Any, Dict
from dotenv import load_dotenv

from .pocketsmith_client import PocketSmithClient
from .beancount_converter import BeancountConverter
from .file_writer import BeancountFileWriter
from .synchronizer import PocketSmithSynchronizer
from .api_writer import PocketSmithAPIWriter
from .changelog import TransactionChangelog


def handle_sync_mode(
    args: Any,
    client: Any,
    remote_transactions: Any,
    transaction_accounts: Any,
    categories: Any,
) -> None:
    """Handle synchronization mode."""
    print("Synchronization mode enabled")

    if args.dry_run:
        print("DRY RUN MODE: No actual changes will be made")

    try:
        # Set up synchronization components
        api_writer = PocketSmithAPIWriter(client.api_key, client.base_url)
        changelog = TransactionChangelog(args.output_dir)
        synchronizer = PocketSmithSynchronizer(
            api_writer=api_writer, changelog=changelog
        )

        # For now, we'll use empty local transactions since we don't have
        # a way to read existing beancount files yet
        # TODO: Implement beancount file reading to get local transactions
        local_transactions: list[Dict[str, Any]] = []

        print("Starting synchronization...")
        print(f"Remote transactions: {len(remote_transactions)}")
        print(f"Local transactions: {len(local_transactions)}")

        # Perform synchronization
        results = synchronizer.synchronize(
            local_transactions=local_transactions,
            remote_transactions=remote_transactions,
            dry_run=args.dry_run,
        )

        # Print summary
        successful = sum(1 for r in results if r.status.name == "SUCCESS")
        errors = sum(1 for r in results if r.has_errors)
        warnings = sum(1 for r in results if r.has_warnings)
        changes = sum(len(r.changes) for r in results)

        print("\nSynchronization completed:")
        print(f"  Processed: {len(results)} transactions")
        print(f"  Successful: {successful}")
        print(f"  Changes made: {changes}")
        print(f"  Warnings: {warnings}")
        print(f"  Errors: {errors}")

        if args.dry_run:
            print("\nDRY RUN: No actual changes were made to PocketSmith")

        # Show detailed results if verbose
        if args.sync_verbose:
            print("\nDetailed results:")
            for result in results:
                if result.has_changes or result.has_errors or result.has_warnings:
                    print(f"  Transaction {result.transaction_id}:")
                    for change in result.changes:
                        print(
                            f"    {change.field_name}: {change.old_value} -> {change.new_value}"
                        )
                    for error in result.errors:
                        print(f"    ERROR: {error}")
                    for warning in result.warnings:
                        print(f"    WARNING: {warning}")

        return

    except Exception as e:
        print(f"Synchronization failed: {e}", file=sys.stderr)
        if args.sync_verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


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
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Synchronize changes between PocketSmith and beancount",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making actual changes (requires --sync)",
    )
    parser.add_argument(
        "--sync-verbose",
        action="store_true",
        help="Enable verbose logging for synchronization operations",
    )
    parser.add_argument(
        "--sync-batch-size",
        type=int,
        default=100,
        help="Batch size for API write-back operations (default: 100)",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.dry_run and not args.sync:
        print("Error: --dry-run requires --sync", file=sys.stderr)
        sys.exit(1)

    # Set up logging level based on verbosity
    if args.sync_verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

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

        # Handle synchronization mode
        if args.sync:
            handle_sync_mode(
                args, client, transactions, transaction_accounts, categories
            )
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
