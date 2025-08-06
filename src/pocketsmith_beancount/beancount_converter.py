from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
import re


class BeancountConverter:
    def __init__(self) -> None:
        self.account_mapping: Dict[int, str] = {}
        self.category_mapping: Dict[int, str] = {}
        self.currencies: set[str] = set()

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
        self, transaction_accounts: List[Dict[str, Any]]
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
                    open_date = datetime.now().strftime("%Y-%m-%d")

                metadata = f'\n    id: "{account_id}"' if account_id else ""
                declarations.append(
                    f"{open_date} open {account_name} {currency}{metadata}"
                )
                account_names.add(account_name)

        return sorted(declarations)

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
                metadata = f'\n    id: "{category_id}"' if category_id else ""
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

        lines = [f'{date} * "{payee}" "{narration}"']

        # Add transaction ID metadata
        transaction_id = transaction.get("id")
        if transaction_id:
            lines.append(f'    id: "{transaction_id}"')

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
        account_declarations = self.generate_account_declarations(transaction_accounts)
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

        return "\n\n".join(beancount_entries)
