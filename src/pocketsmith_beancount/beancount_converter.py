from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any
import re


class BeancountConverter:
    def __init__(self):
        self.account_mapping = {}
        self.category_mapping = {}
        self.currencies = set()

    def _sanitize_account_name(self, name: str) -> str:
        name = re.sub(r"[^a-zA-Z0-9\-_]", "-", name)
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

        return self.account_mapping[account_id]

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

        return self.category_mapping[category["id"]]

    def generate_account_declarations(
        self, accounts: List[Dict[str, Any]]
    ) -> List[str]:
        declarations = []
        account_names = set()

        for account in accounts:
            account_name = self._get_account_name(account)
            if account_name not in account_names:
                currency = account.get("currency_code", "USD")
                self.currencies.add(currency)
                declarations.append(
                    f"{datetime.now().strftime('%Y-%m-%d')} open {account_name} {currency}"
                )
                account_names.add(account_name)

        return sorted(declarations)

    def generate_commodity_declarations(self) -> List[str]:
        declarations = []
        for currency in sorted(self.currencies):
            declarations.append(
                f"{datetime.now().strftime('%Y-%m-%d')} commodity {currency}"
            )
        return declarations

    def convert_transaction(
        self, transaction: Dict[str, Any], accounts: Dict[int, Dict[str, Any]]
    ) -> str:
        date = datetime.fromisoformat(
            transaction["date"].replace("Z", "+00:00")
        ).strftime("%Y-%m-%d")
        payee = (transaction.get("payee") or "").replace('"', '\\"')
        narration = (transaction.get("memo") or "").replace('"', '\\"')

        if not narration and payee:
            narration = payee
        elif not narration:
            narration = "Transaction"

        amount = Decimal(str(transaction["amount"]))
        currency = transaction.get("currency_code", "USD")
        self.currencies.add(currency)

        transaction_account = transaction.get("transaction_account", {})
        if not transaction_account:
            return ""

        account_name = self._get_account_name(transaction_account)

        category = transaction.get("category")
        category_account = self._get_category_account(category)

        lines = [f'{date} * "{payee}" "{narration}"']

        if amount > 0:
            lines.append(f"  {account_name}  {amount} {currency}")
            lines.append(f"  {category_account}")
        else:
            lines.append(f"  {category_account}  {abs(amount)} {currency}")
            lines.append(f"  {account_name}")

        return "\n".join(lines)

    def convert_transactions(
        self, transactions: List[Dict[str, Any]], accounts: List[Dict[str, Any]]
    ) -> str:
        account_dict = {acc["id"]: acc for acc in accounts}

        beancount_entries = []

        commodity_declarations = self.generate_commodity_declarations()
        if commodity_declarations:
            beancount_entries.extend(commodity_declarations)
            beancount_entries.append("")

        account_declarations = self.generate_account_declarations(accounts)
        if account_declarations:
            beancount_entries.extend(account_declarations)
            beancount_entries.append("")

        transaction_entries = []
        for transaction in sorted(transactions, key=lambda t: t["date"]):
            entry = self.convert_transaction(transaction, account_dict)
            if entry:
                transaction_entries.append(entry)

        if transaction_entries:
            beancount_entries.extend(transaction_entries)

        return "\n\n".join(beancount_entries)
