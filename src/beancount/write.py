"""Write and update beancount ledger files using the beancount library."""

from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from decimal import Decimal
from collections import defaultdict

from .common import (
    BeancountError,
    format_account_name,
    sanitize_account_name,
    convert_id_to_decimal,
    convert_to_aest,
    sanitize_tags_for_beancount,
)


def write_ledger(
    content: str,
    file_path: str,
    mode: str = "w",
) -> str:
    """Write content to a beancount ledger file."""
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, mode, encoding="utf-8") as f:
            f.write(content)

        return str(path)
    except Exception as e:
        raise BeancountError(f"Failed to write to {file_path}: {e}")


def update_ledger(
    file_path: str,
    transactions: List[Dict[str, Any]],
    mode: str = "append",
) -> str:
    """Update an existing ledger file with new transactions."""
    if mode == "append":
        content = generate_transactions_content(transactions)
        return write_ledger(content, file_path, mode="a")
    elif mode == "overwrite":
        content = generate_transactions_content(transactions)
        return write_ledger(content, file_path, mode="w")
    else:
        # For other modes like "merge", we'd need to read existing and merge
        raise NotImplementedError(f"Mode '{mode}' not yet implemented")


def write_hierarchical_ledger(
    transactions: List[Dict[str, Any]],
    transaction_accounts: List[Dict[str, Any]],
    categories: List[Dict[str, Any]],
    output_dir: str,
    account_balances: Optional[Dict[int, List[Dict[str, Any]]]] = None,
) -> Dict[str, str]:
    """Write transactions to hierarchical file structure with yearly folders and monthly files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

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
        year_dir = output_path / year
        year_dir.mkdir(exist_ok=True)

        # Convert transactions for this month
        month_content = generate_monthly_transactions_content(
            month_transactions, int(year), int(month)
        )

        # Write monthly file
        monthly_filename = f"{year_month}.beancount"
        monthly_file_path = year_dir / monthly_filename

        write_ledger(month_content, str(monthly_file_path))
        written_files[f"{year}/{monthly_filename}"] = str(monthly_file_path)

    # Create top-level main file with declarations and includes
    main_content = generate_main_file_content(
        list(transactions_by_month.keys()),
        transaction_accounts,
        categories,
        account_balances,
    )

    main_file_path = output_path / "main.beancount"
    write_ledger(main_content, str(main_file_path))
    written_files["main.beancount"] = str(main_file_path)

    return written_files


def generate_transactions_content(transactions: List[Dict[str, Any]]) -> str:
    """Generate beancount content for a list of transactions."""
    if not transactions:
        return ""

    content_lines = []

    for transaction in sorted(transactions, key=lambda t: t.get("date", "")):
        transaction_content = convert_transaction_to_beancount(transaction)
        if transaction_content:
            content_lines.append(transaction_content)

    return "\n\n".join(content_lines)


def generate_monthly_transactions_content(
    transactions: List[Dict[str, Any]],
    year: int,
    month: int,
) -> str:
    """Convert transactions for a single month without declarations."""
    if not transactions:
        return ""

    # Filter transactions by year and month
    filtered_transactions = []
    for transaction in transactions:
        try:
            date = datetime.fromisoformat(transaction["date"].replace("Z", "+00:00"))
            if date.year == year and date.month == month:
                filtered_transactions.append(transaction)
        except (ValueError, KeyError):
            continue

    if not filtered_transactions:
        return ""

    # Add header comment with month/year
    month_year = datetime(year, month, 1).strftime("%B %Y")

    content_lines = [
        f"; Transactions for {month_year}",
        f"; Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    # Convert transactions
    transaction_entries = []
    for transaction in sorted(filtered_transactions, key=lambda t: t.get("date", "")):
        entry = convert_transaction_to_beancount(transaction)
        if entry:
            transaction_entries.append(entry)

    if transaction_entries:
        content_lines.extend(transaction_entries)

    return "\n\n".join(content_lines)


def generate_main_file_content(
    year_months: List[str],
    transaction_accounts: List[Dict[str, Any]],
    categories: List[Dict[str, Any]],
    account_balances: Optional[Dict[int, List[Dict[str, Any]]]] = None,
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
        # Handle both tuple format [(year, month)] and string format ["YYYY-MM"]
        if isinstance(year_months[0], tuple):
            earliest_year, earliest_month = min(year_months)
            earliest_date = f"{earliest_year}-{earliest_month:02d}-01"
        else:
            earliest_year_month = min(year_months)
            earliest_date = f"{earliest_year_month}-01"

    # Generate account declarations
    account_declarations = generate_account_declarations(
        transaction_accounts, earliest_date
    )
    if account_declarations:
        content_lines.extend(account_declarations)
        content_lines.append("")

    # Generate category declarations
    if categories:
        category_declarations = generate_category_declarations(
            categories, earliest_date
        )
        if category_declarations:
            content_lines.extend(category_declarations)
            content_lines.append("")

    # Always add Expenses:Uncategorized declaration
    open_date = earliest_date or datetime.now().strftime("%Y-%m-%d")
    uncategorized_declaration = f"{open_date} open Expenses:Uncategorized"
    content_lines.append(uncategorized_declaration)
    content_lines.append("")

    # Generate balance directives if provided
    if account_balances:
        # Convert integer keys to strings for the function
        string_keyed_balances = {str(k): v for k, v in account_balances.items()}
        balance_declarations = generate_balance_declarations(
            string_keyed_balances, transaction_accounts
        )
        if balance_declarations:
            content_lines.extend(balance_declarations)
            content_lines.append("")

    # Add include statements for monthly files
    content_lines.append("; Monthly transaction files")
    for year_month in sorted(year_months):
        # Handle both tuple format and string format
        if isinstance(year_month, tuple):
            year, month = year_month
            include_path = f"{year}/{year}-{month:02d}.beancount"
            content_lines.append(f'include "{include_path}"')
        else:
            year, month = year_month.split("-")
            include_path = f"{year}/{year_month}.beancount"
            content_lines.append(f'include "{include_path}"')

    return "\n".join(content_lines)


def generate_balance_declarations(
    account_balances: Dict[str, List[Dict[str, Any]]],
    transaction_accounts: List[Dict[str, Any]],
) -> List[str]:
    """Generate balance directive declarations."""
    balance_lines = []

    # Create lookup for account names
    account_lookup = {}
    for account in transaction_accounts:
        account_id = str(account.get("id"))
        institution = account.get("institution", {}).get("title", "Unknown")
        account_name = account.get("name", "Unknown")

        from .common import sanitize_account_name

        sanitized_institution = sanitize_account_name(institution)
        sanitized_account = sanitize_account_name(account_name)
        full_account_name = f"Assets:{sanitized_institution}:{sanitized_account}"
        account_lookup[account_id] = full_account_name

    # Generate balance directives
    for account_id, balances in account_balances.items():
        account_name = account_lookup.get(
            str(account_id), f"Assets:Unknown-Account-{account_id}"
        )

        for balance_data in balances:
            balance_date = balance_data.get("date", "")
            balance_amount = balance_data.get("balance", "0.00")

            # Parse date
            if "T" in balance_date:
                balance_date = balance_date.split("T")[0]

            balance_lines.append(
                f"{balance_date} balance {account_name} {balance_amount} USD"
            )

    return balance_lines


def convert_transaction_to_beancount(transaction: Dict[str, Any]) -> str:
    """Convert a PocketSmith transaction to beancount format."""
    try:
        # Extract date
        date = transaction.get("date", "")
        if "T" in date:
            date = datetime.fromisoformat(date.replace("Z", "+00:00")).strftime(
                "%Y-%m-%d"
            )

        # Extract flag
        flag = "!" if transaction.get("needs_review", False) else "*"

        # Extract payee and narration
        payee = (transaction.get("merchant") or transaction.get("payee") or "").replace(
            '"', '\\"'
        )
        narration = (transaction.get("note") or transaction.get("memo") or "").replace(
            '"', '\\"'
        )

        # Fallback logic for empty fields
        if not payee:
            payee = "Unknown"

        # Convert labels to tags
        labels = transaction.get("labels", [])
        tags = ""
        if labels:
            sanitized_labels = sanitize_tags_for_beancount(labels)
            if sanitized_labels:
                tags = " " + " ".join(f"#{tag}" for tag in sanitized_labels)

        # Build transaction line
        lines = [f'{date} {flag} "{payee}" "{narration}"{tags}']

        # Add transaction ID metadata
        transaction_id = transaction.get("id")
        decimal_id = convert_id_to_decimal(transaction_id)
        if decimal_id is not None:
            lines.append(f"    id: {decimal_id}")

        # Add last modified datetime metadata
        updated_at = transaction.get("updated_at")
        if updated_at:
            aest_timestamp = convert_to_aest(updated_at)
            lines.append(f'    last_modified: "{aest_timestamp}"')

        # Add closing balance metadata if available
        closing_balance = transaction.get("closing_balance")
        if closing_balance is not None:
            try:
                balance_decimal = Decimal(str(closing_balance))
                lines.append(f"    closing_balance: {balance_decimal}")
            except (ValueError, TypeError):
                pass

        # Handle postings - simplified for PocketSmith transactions
        amount = Decimal(str(transaction.get("amount", 0)))
        currency = transaction.get("currency_code", "USD").upper()

        # Get account information
        transaction_account = transaction.get("transaction_account", {})
        account_name = get_account_name_from_transaction_account(transaction_account)

        # Get category
        category = transaction.get("category")

        # For positive amounts (income) without a category, default to Income:Unknown
        if amount > 0 and not category:
            category_account = "Income:Unknown"
        else:
            category_account = get_category_account_from_category(category or {})

        # Add postings
        if amount > 0:
            lines.append(f"  {account_name}  {amount} {currency}")
            lines.append(f"  {category_account}  -{amount} {currency}")
        else:
            lines.append(f"  {category_account}  {abs(amount)} {currency}")
            lines.append(f"  {account_name}  -{abs(amount)} {currency}")

        return "\n".join(lines)

    except Exception as e:
        return f"; Error converting transaction {transaction.get('id', 'unknown')}: {e}"


def generate_account_declarations(
    transaction_accounts: List[Dict[str, Any]],
    earliest_date: Optional[str] = None,
) -> List[str]:
    """Generate account open declarations."""
    declarations = []
    account_names = set()

    for account in transaction_accounts:
        account_name = get_account_name_from_transaction_account(account)
        if account_name not in account_names:
            account_id = account.get("id")

            # Use base currency from transaction account
            currency = account.get("currency_code", "USD").upper()

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
            decimal_id = convert_id_to_decimal(account_id)
            metadata = f"\n    id: {decimal_id}" if decimal_id is not None else ""
            declarations.append(f"{open_date} open {account_name} {currency}{metadata}")
            account_names.add(account_name)

    return sorted(declarations)


def generate_category_declarations(
    categories: List[Dict[str, Any]], open_date: Optional[str] = None
) -> List[str]:
    """Generate category account open declarations."""
    declarations = []
    category_names = set()

    if not open_date:
        open_date = datetime.now().strftime("%Y-%m-%d")

    for category in categories:
        category_account = get_category_account_from_category(category)
        if category_account not in category_names:
            category_id = category.get("id")
            # Convert category ID to decimal
            decimal_id = convert_id_to_decimal(category_id)
            metadata = f"\n    id: {decimal_id}" if decimal_id is not None else ""
            declarations.append(f"{open_date} open {category_account}{metadata}")
            category_names.add(category_account)

    return sorted(declarations)


def get_account_name_from_transaction_account(account: Dict[str, Any]) -> str:
    """Generate beancount account name from PocketSmith transaction account."""
    if not account:
        return "Assets:Unknown:Unknown"

    institution_data = account.get("institution") or {}
    institution = institution_data.get("title", "Unknown")
    account_name = account.get("name", f"Account-{account.get('id', 'Unknown')}")

    account_type = account.get("type", "Assets")
    if account_type.lower() in ["credit_card", "loan"]:
        account_type = "Liabilities"
    elif account_type.lower() in ["checking", "savings", "investment", "bank"]:
        account_type = "Assets"
    else:
        account_type = "Assets"

    return format_account_name(account_type, institution, account_name)


def get_category_account_from_category(
    category: Dict[str, Any], is_income: bool = False
) -> str:
    """Generate beancount account name from PocketSmith category."""
    if not category:
        return "Expenses:Uncategorized"

    title = category.get("title", "Uncategorized")
    sanitized = sanitize_account_name(title)

    if category.get("is_transfer", False):
        return f"Transfers:{sanitized}"
    elif category.get("is_income", False) or is_income or title.lower() == "income":
        return f"Income:{sanitized}"
    else:
        return f"Expenses:{sanitized}"
