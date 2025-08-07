import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from collections import defaultdict
from .changelog import TransactionChangelog


class BeancountFileWriter:
    def __init__(self, output_dir: Optional[str] = None):
        output_path = output_dir or os.getenv("BEANCOUNT_OUTPUT_DIR") or "./output"
        self.output_dir = Path(output_path)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.changelog = TransactionChangelog(output_path)

    def write_beancount_file(self, content: str, filename: Optional[str] = None) -> str:
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pocketsmith_transactions_{timestamp}.beancount"

        if not filename.endswith(".beancount"):
            filename += ".beancount"

        file_path = self.output_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def append_to_file(self, content: str, filename: str) -> str:
        file_path = self.output_dir / filename

        with open(file_path, "a", encoding="utf-8") as f:
            f.write("\n\n" + content)

        return str(file_path)

    def get_output_directory(self) -> str:
        return str(self.output_dir)

    def write_hierarchical_beancount_files(
        self,
        transactions: List[Dict[str, Any]],
        transaction_accounts: List[Dict[str, Any]],
        categories: List[Dict[str, Any]],
        account_balances: Optional[Dict[int, List[Dict[str, Any]]]] = None,
        converter: Any = None,
    ) -> Dict[str, str]:
        """Write transactions to hierarchical file structure with yearly folders and monthly files."""
        if not converter:
            raise ValueError("BeancountConverter instance required")

        # Group transactions by year and month
        transactions_by_month = defaultdict(list)
        for transaction in transactions:
            date = datetime.fromisoformat(transaction["date"].replace("Z", "+00:00"))
            year_month = date.strftime("%Y-%m")
            transactions_by_month[year_month].append(transaction)

        written_files = {}

        # Create yearly directories and monthly transaction files
        for year_month, month_transactions in transactions_by_month.items():
            year, month = year_month.split("-")
            year_dir = self.output_dir / year
            year_dir.mkdir(exist_ok=True)

            # Convert transactions for this month
            month_content = converter.convert_monthly_transactions(
                month_transactions, transaction_accounts
            )

            # Write monthly file
            monthly_filename = f"{year_month}.beancount"
            monthly_file_path = year_dir / monthly_filename

            with open(monthly_file_path, "w", encoding="utf-8") as f:
                f.write(month_content)

            written_files[f"{year}/{monthly_filename}"] = str(monthly_file_path)

        # Create top-level main file with declarations and includes
        main_content = self._generate_main_file_content(
            list(transactions_by_month.keys()),
            transaction_accounts,
            categories,
            account_balances,
            converter,
        )

        main_file_path = self.output_dir / "main.beancount"
        with open(main_file_path, "w", encoding="utf-8") as f:
            f.write(main_content)

        written_files["main.beancount"] = str(main_file_path)

        # Log transaction operations to changelog
        for transaction in transactions:
            self.changelog.log_transaction_create(transaction)

        return written_files

    def _generate_main_file_content(
        self,
        year_months: List[str],
        transaction_accounts: List[Dict[str, Any]],
        categories: List[Dict[str, Any]],
        account_balances: Optional[Dict[int, List[Dict[str, Any]]]],
        converter: Any,
    ) -> str:
        """Generate the main beancount file with declarations and includes."""
        content_lines = []

        # Add header comment
        content_lines.append("; PocketSmith to Beancount - Main File")
        content_lines.append(
            f"; Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        content_lines.append("")

        # Generate commodity declarations
        # We need to process all transactions to collect currencies
        all_currencies = set()
        for account in transaction_accounts:
            currency = account.get("currency_code", "USD").upper()
            all_currencies.add(currency)

        commodity_declarations = []
        for currency in sorted(all_currencies):
            commodity_declarations.append(
                f"{datetime.now().strftime('%Y-%m-%d')} commodity {currency}"
            )

        if commodity_declarations:
            content_lines.extend(commodity_declarations)
            content_lines.append("")

        # Find earliest transaction date for account declarations
        earliest_date = None
        if year_months:
            earliest_year_month = min(year_months)
            earliest_date = f"{earliest_year_month}-01"

        # Generate account declarations
        account_declarations = converter.generate_account_declarations(
            transaction_accounts, earliest_date
        )
        if account_declarations:
            content_lines.extend(account_declarations)
            content_lines.append("")

        # Generate category declarations
        if categories:
            # Find earliest date from year_months for category declarations
            earliest_date = None
            if year_months:
                earliest_year_month = min(year_months)
                earliest_date = f"{earliest_year_month}-01"

            category_declarations = converter.generate_category_declarations(
                categories, earliest_date
            )
            if category_declarations:
                content_lines.extend(category_declarations)
                content_lines.append("")

        # Add starting balance directives
        starting_balance_directives = converter.generate_starting_balance_directives(
            transaction_accounts
        )
        if starting_balance_directives:
            content_lines.extend(starting_balance_directives)
            content_lines.append("")

        # Add balance directives if provided
        if account_balances:
            balance_directives = converter.generate_balance_directives(
                account_balances, transaction_accounts
            )
            if balance_directives:
                content_lines.extend(balance_directives)
                content_lines.append("")

        # Add include statements for monthly files
        content_lines.append("; Monthly transaction files")
        for year_month in sorted(year_months):
            year, month = year_month.split("-")
            include_path = f"{year}/{year_month}.beancount"
            content_lines.append(f'include "{include_path}"')

        return "\n".join(content_lines)

    def update_hierarchical_beancount_files(
        self,
        old_transactions: List[Dict[str, Any]],
        new_transactions: List[Dict[str, Any]],
        transaction_accounts: List[Dict[str, Any]],
        categories: List[Dict[str, Any]],
        account_balances: Optional[Dict[int, List[Dict[str, Any]]]] = None,
        converter: Any = None,
    ) -> Dict[str, str]:
        """Update existing hierarchical beancount files with incremental changes."""
        if not converter:
            raise ValueError("BeancountConverter instance required")

        # Compare transactions and log changes
        self.changelog.compare_transactions(old_transactions, new_transactions)

        # For now, do a full rewrite (incremental updates would be more complex)
        # In a full implementation, this would:
        # 1. Detect which monthly files need updates
        # 2. Only rewrite changed monthly files
        # 3. Update the main file if account/category declarations changed
        return self.write_hierarchical_beancount_files(
            new_transactions,
            transaction_accounts,
            categories,
            account_balances,
            converter,
        )
