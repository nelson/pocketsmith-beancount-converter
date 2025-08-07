from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Optional, Union
import re
import pytz


class BeancountConverter:
    def __init__(self) -> None:
        self.account_mapping: Dict[int, str] = {}
        self.category_mapping: Dict[int, str] = {}
        self.currencies: set[str] = set()

    def _convert_id_to_decimal(self, id_value: Any) -> Optional[Decimal]:
        """Convert ID to decimal number with error handling."""
        if id_value is None:
            return None

        try:
            # Handle both string and numeric IDs
            if isinstance(id_value, str):
                # Remove any non-numeric characters except decimal point
                cleaned_id = re.sub(r"[^\d.]", "", id_value)
                if not cleaned_id:
                    return None
                return Decimal(cleaned_id)
            else:
                return Decimal(str(id_value))
        except (InvalidOperation, ValueError):
            # Log warning but don't fail - return None for invalid IDs
            return None

    def _convert_to_aest(self, timestamp: Union[str, datetime]) -> str:
        """Convert timestamp to Australian Eastern Standard Time."""
        try:
            # Handle datetime objects
            if isinstance(timestamp, datetime):
                dt = timestamp
            else:
                # Handle string timestamps
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

            # Convert to AEST (UTC+10) or AEDT (UTC+11) depending on date
            aest_tz = pytz.timezone("Australia/Sydney")
            aest_dt = dt.astimezone(aest_tz)

            # Return formatted string with milliseconds
            return aest_dt.strftime("%b %d %H:%M:%S.%f")[
                :-3
            ]  # Remove last 3 digits for milliseconds
        except (ValueError, AttributeError):
            # Fallback to string representation
            return str(timestamp)

    def _sanitize_account_name(self, name: str) -> str:
        # Strip initial underscores and convert spaces to hyphens
        name = name.lstrip("_")
        name = name.replace(" ", "-")
        # Replace other invalid characters with hyphens
        name = re.sub(r"[^a-zA-Z0-9\-]", "-", name)
        name = re.sub(r"-+", "-", name)
        return name.strip("-").title()

    def _get_account_name(self, account: Dict[str, Any]) -> str:
        account_id = account.get("id")
        if not account_id:
            return "Assets:Unknown:Unknown"

        if account_id not in self.account_mapping:
            institution = account.get("institution", {}).get("title", "Unknown")
            account_name = account.get("name", f"Account-{account_id}")

            sanitized_institution = self._sanitize_account_name(institution)
            sanitized_account = self._sanitize_account_name(account_name)

            account_type = account.get("type", "Assets")
            if account_type.lower() in ["credit_card", "loan"]:
                account_type = "Liabilities"
            elif account_type.lower() in ["checking", "savings", "investment", "bank"]:
                account_type = "Assets"
            else:
                account_type = "Assets"

            full_account = f"{account_type}:{sanitized_institution}:{sanitized_account}"
            self.account_mapping[account_id] = full_account

        return str(self.account_mapping[account_id])

    def _get_category_account(self, category: Dict[str, Any]) -> str:
        if not category:
            return "Expenses:Uncategorized"

        if category["id"] not in self.category_mapping:
            title = category.get("title", "Uncategorized")
            sanitized = self._sanitize_account_name(title)

            if category.get("is_transfer", False):
                account_name = f"Transfers:{sanitized}"
            elif category.get("is_income", False):
                account_name = f"Income:{sanitized}"
            else:
                account_name = f"Expenses:{sanitized}"

            self.category_mapping[category["id"]] = account_name

        return str(self.category_mapping[category["id"]])

    def generate_account_declarations(
        self,
        transaction_accounts: List[Dict[str, Any]],
        earliest_date: Optional[str] = None,
    ) -> List[str]:
        declarations = []
        account_names = set()

        for account in transaction_accounts:
            account_name = self._get_account_name(account)
            if account_name not in account_names:
                account_id = account.get("id")

                # Use base currency from transaction account
                currency = account.get("currency_code", "USD").upper()
                self.currencies.add(currency)

                # Use starting_balance_date as account open date
                open_date = account.get("starting_balance_date")
                if open_date:
                    # Parse and format the date
                    open_date = datetime.fromisoformat(
                        open_date.replace("Z", "+00:00")
                    ).strftime("%Y-%m-%d")
                else:
                    # Use earliest transaction date if available, otherwise today
                    open_date = earliest_date or datetime.now().strftime("%Y-%m-%d")

                # Convert account ID to decimal
                decimal_id = self._convert_id_to_decimal(account_id)
                metadata = f"\n    id: {decimal_id}" if decimal_id is not None else ""
                declarations.append(
                    f"{open_date} open {account_name} {currency}{metadata}"
                )
                account_names.add(account_name)

        return sorted(declarations)

    def generate_starting_balance_directives(
        self, transaction_accounts: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate starting balance directives from PocketSmith account data."""
        directives = []

        for account in transaction_accounts:
            account_name = self._get_account_name(account)
            currency = account.get("currency_code", "USD").upper()

            # Look for starting balance data
            starting_balance = account.get("starting_balance")
            starting_balance_date = account.get("starting_balance_date")

            if starting_balance is not None and starting_balance_date:
                try:
                    # Parse and format the date
                    balance_date = datetime.fromisoformat(
                        starting_balance_date.replace("Z", "+00:00")
                    ).strftime("%Y-%m-%d")

                    # Convert balance to decimal
                    balance_amount = Decimal(str(starting_balance))

                    directives.append(
                        f"{balance_date} balance {account_name} {balance_amount} {currency}"
                    )
                except (ValueError, InvalidOperation):
                    # Skip invalid balance data
                    continue

        return sorted(directives)

    def generate_category_declarations(
        self, categories: List[Dict[str, Any]], open_date: Optional[str] = None
    ) -> List[str]:
        declarations = []
        category_names = set()

        if not open_date:
            open_date = datetime.now().strftime("%Y-%m-%d")

        for category in categories:
            category_account = self._get_category_account(category)
            if category_account not in category_names:
                category_id = category.get("id")
                # Convert category ID to decimal
                decimal_id = self._convert_id_to_decimal(category_id)
                metadata = f"\n    id: {decimal_id}" if decimal_id is not None else ""
                declarations.append(f"{open_date} open {category_account}{metadata}")
                category_names.add(category_account)

        return sorted(declarations)

    def generate_commodity_declarations(self) -> List[str]:
        declarations = []
        for currency in sorted(self.currencies):
            declarations.append(
                f"{datetime.now().strftime('%Y-%m-%d')} commodity {currency.upper()}"
            )
        return declarations

    def generate_balance_directives(
        self,
        account_balances: Dict[int, List[Dict[str, Any]]],
        transaction_accounts: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate balance directives from PocketSmith account balance history."""
        directives = []
        account_dict = {acc["id"]: acc for acc in transaction_accounts}

        for account_id, balances in account_balances.items():
            if account_id not in account_dict:
                continue

            account = account_dict[account_id]
            account_name = self._get_account_name(account)
            currency = account.get("currency_code", "USD").upper()

            # Sort balances by date and take the most recent ones
            sorted_balances = sorted(balances, key=lambda b: b.get("date", ""))

            # Add balance directives for key dates (e.g., month-end balances)
            for balance in sorted_balances[-5:]:  # Last 5 balance entries
                balance_date = balance.get("date")
                balance_amount = balance.get("balance")

                if balance_date and balance_amount is not None:
                    # Parse date and add one day for balance directive
                    balance_datetime = datetime.fromisoformat(
                        balance_date.replace("Z", "+00:00")
                    )
                    next_day = (balance_datetime + timedelta(days=1)).strftime(
                        "%Y-%m-%d"
                    )

                    directives.append(
                        f"{next_day} balance {account_name} {Decimal(str(balance_amount))} {currency}"
                    )

        return sorted(directives)

    def convert_transaction(
        self, transaction: Dict[str, Any], accounts: Dict[int, Dict[str, Any]]
    ) -> str:
        date = datetime.fromisoformat(
            transaction["date"].replace("Z", "+00:00")
        ).strftime("%Y-%m-%d")

        # Use merchant as payee, note as narration
        payee = (transaction.get("merchant") or transaction.get("payee") or "").replace(
            '"', '\\"'
        )
        narration = (transaction.get("note") or transaction.get("memo") or "").replace(
            '"', '\\"'
        )

        # Fallback logic for empty fields
        if not payee:
            payee = "Unknown"
        if not narration:
            narration = ""

        # Convert labels to tags
        labels = transaction.get("labels", [])
        tags = ""
        if labels:
            # Sanitize labels for beancount tags (alphanumeric, hyphens, underscores only)
            sanitized_labels = []
            for label in labels:
                sanitized = re.sub(r"[^a-zA-Z0-9\-_]", "-", label).strip("-")
                if sanitized:
                    sanitized_labels.append(sanitized)
            if sanitized_labels:
                tags = " " + " ".join(f"#{tag}" for tag in sanitized_labels)

        # Use transaction amount and get currency from transaction account
        amount = Decimal(str(transaction["amount"]))
        transaction_account = transaction.get("transaction_account", {})
        currency = (
            transaction.get("currency_code")
            or transaction_account.get("currency_code", "USD")
        ).upper()
        self.currencies.add(currency)

        transaction_account = transaction.get("transaction_account", {})
        if not transaction_account:
            return ""

        account_name = self._get_account_name(transaction_account)

        category = transaction.get("category")
        if category is not None:
            category_account = self._get_category_account(category)
        else:
            category_account = "Expenses:Uncategorized"

        # Check for needs_review flag
        flag = "!" if transaction.get("needs_review", False) else "*"

        lines = [f'{date} {flag} "{payee}" "{narration}"{tags}']

        # Add transaction ID metadata
        transaction_id = transaction.get("id")
        decimal_id = self._convert_id_to_decimal(transaction_id)
        if decimal_id is not None:
            lines.append(f"    id: {decimal_id}")

        # Add last modified datetime metadata
        updated_at = transaction.get("updated_at")
        if updated_at:
            aest_timestamp = self._convert_to_aest(updated_at)
            lines.append(f'    last_modified: "{aest_timestamp}"')

        # Add closing balance metadata if available
        closing_balance = transaction.get("closing_balance")
        if closing_balance is not None:
            try:
                balance_decimal = Decimal(str(closing_balance))
                lines.append(f"    closing_balance: {balance_decimal}")
            except (InvalidOperation, ValueError):
                # Skip invalid balance data
                pass

        if amount > 0:
            lines.append(f"  {account_name}  {amount} {currency}")
            lines.append(f"  {category_account}")
        else:
            lines.append(f"  {category_account}  {abs(amount)} {currency}")
            lines.append(f"  {account_name}")

        return "\n".join(lines)

    def convert_transactions(
        self,
        transactions: List[Dict[str, Any]],
        transaction_accounts: List[Dict[str, Any]],
        categories: Optional[List[Dict[str, Any]]] = None,
        account_balances: Optional[Dict[int, List[Dict[str, Any]]]] = None,
    ) -> str:
        account_dict = {acc["id"]: acc for acc in transaction_accounts}

        # Find the earliest transaction date for category declarations
        earliest_date = None
        if transactions:
            earliest_date = min(
                datetime.fromisoformat(t["date"].replace("Z", "+00:00")).strftime(
                    "%Y-%m-%d"
                )
                for t in transactions
            )

        beancount_entries = []

        # Process transactions first to collect currencies
        transaction_entries = []
        for transaction in sorted(transactions, key=lambda t: t["date"]):
            entry = self.convert_transaction(transaction, account_dict)
            if entry:
                transaction_entries.append(entry)

        # Now generate commodity declarations after currencies are collected
        commodity_declarations = self.generate_commodity_declarations()
        if commodity_declarations:
            beancount_entries.extend(commodity_declarations)
            beancount_entries.append("")

        # Use authoritative transaction accounts for declarations
        account_declarations = self.generate_account_declarations(
            transaction_accounts, earliest_date
        )
        if account_declarations:
            beancount_entries.extend(account_declarations)
            beancount_entries.append("")

        if categories:
            category_declarations = self.generate_category_declarations(
                categories, earliest_date or None
            )
            if category_declarations:
                beancount_entries.extend(category_declarations)
                beancount_entries.append("")

        # Check if Expenses:Uncategorized is used and add declaration if needed
        uses_uncategorized = any(
            not transaction.get("category") for transaction in transactions
        )
        if uses_uncategorized:
            open_date = earliest_date or datetime.now().strftime("%Y-%m-%d")
            uncategorized_declaration = f"{open_date} open Expenses:Uncategorized"
            beancount_entries.append(uncategorized_declaration)
            beancount_entries.append("")

        if transaction_entries:
            beancount_entries.extend(transaction_entries)

        # Add balance directives if provided
        if account_balances:
            balance_directives = self.generate_balance_directives(
                account_balances, transaction_accounts
            )
            if balance_directives:
                beancount_entries.append("")
                beancount_entries.extend(balance_directives)

        return "\n\n".join(beancount_entries)

    def convert_monthly_transactions(
        self,
        transactions: List[Dict[str, Any]],
        transaction_accounts: List[Dict[str, Any]],
    ) -> str:
        """Convert transactions for a single month without declarations."""
        if not transactions:
            return ""

        account_dict = {acc["id"]: acc for acc in transaction_accounts}

        # Add header comment with month/year
        first_transaction_date = datetime.fromisoformat(
            transactions[0]["date"].replace("Z", "+00:00")
        )
        month_year = first_transaction_date.strftime("%B %Y")

        content_lines = [
            f"; Transactions for {month_year}",
            f"; Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Convert transactions
        transaction_entries = []
        for transaction in sorted(transactions, key=lambda t: t["date"]):
            entry = self.convert_transaction(transaction, account_dict)
            if entry:
                transaction_entries.append(entry)

        if transaction_entries:
            content_lines.extend(transaction_entries)

        return "\n\n".join(content_lines)
