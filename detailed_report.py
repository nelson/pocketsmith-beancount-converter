#!/usr/bin/env python3
"""Generate detailed categorization reports with visualizations."""

from beancount import loader
from beanquery import query
from collections import defaultdict
import sys


def run_query(ledger_file: str, bql_query: str):
    """Run a BQL query and return results."""
    entries, errors, options = loader.load_file(ledger_file)

    if errors:
        print(f"Errors loading ledger: {errors}", file=sys.stderr)
        return None, None

    result_types, result_rows = query.run_query(
        entries, options, bql_query, numberify=True
    )

    return result_types, result_rows


def format_currency(amount):
    """Format currency with proper sign and commas."""
    if amount >= 0:
        return f"${amount:,.2f}"
    else:
        return f"-${abs(amount):,.2f}"


def print_bar_chart(label, amount, max_amount, width=40):
    """Print a horizontal bar chart."""
    if max_amount == 0:
        bar_width = 0
    else:
        bar_width = int((abs(amount) / max_amount) * width)

    bar = "█" * bar_width
    percentage = (abs(amount) / max_amount * 100) if max_amount > 0 else 0

    print(f"  {label:35s} {format_currency(amount):>15s} ({percentage:5.1f}%) {bar}")


def generate_detailed_report(ledger_file: str):
    """Generate a detailed categorization report."""

    print("=" * 100)
    print(" " * 30 + "CATEGORIZATION REPORT - NOVEMBER 2025")
    print("=" * 100)
    print()

    # Get all expense categories with transaction counts
    expenses_detail_query = """
        SELECT
            account,
            count(*) as num_transactions,
            sum(convert(position, 'AUD')) as total_aud
        FROM
            OPEN ON 2025-11-01 CLOSE ON 2025-12-01
        WHERE
            account ~ '^Expenses:'
        GROUP BY account
        ORDER BY total_aud DESC
    """

    result_types, result_rows = run_query(ledger_file, expenses_detail_query)

    if result_rows:
        total_expenses = sum(row[2] for row in result_rows)

        print("EXPENSE BREAKDOWN")
        print("-" * 100)
        print(f"{'Category':<35s} {'Amount':>15s} {'Percent':>8s} {'Transactions':>15s}")
        print("-" * 100)

        for account, num_tx, amount in result_rows:
            category = account.replace('Expenses:', '').replace('-', ' ')
            percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
            print(f"{category:<35s} {format_currency(amount):>15s} {percentage:>7.1f}% {num_tx:>15,d} txns")

        print("-" * 100)
        print(f"{'TOTAL':<35s} {format_currency(total_expenses):>15s} {100.0:>7.1f}%")
        print()

        # Visual bar chart
        print("\nEXPENSE CATEGORIES (Visual)")
        print("-" * 100)
        max_expense = max(row[2] for row in result_rows)
        for account, num_tx, amount in result_rows:
            category = account.replace('Expenses:', '').replace('-', ' ')
            print_bar_chart(category, amount, max_expense, width=50)
        print()

    # Get all income categories
    income_detail_query = """
        SELECT
            account,
            count(*) as num_transactions,
            sum(convert(position, 'AUD')) as total_aud
        FROM
            OPEN ON 2025-11-01 CLOSE ON 2025-12-01
        WHERE
            account ~ '^Income:'
        GROUP BY account
        ORDER BY total_aud
    """

    result_types, result_rows = run_query(ledger_file, income_detail_query)

    if result_rows:
        total_income = sum(row[2] for row in result_rows)

        print("\nINCOME BREAKDOWN")
        print("-" * 100)
        print(f"{'Category':<35s} {'Amount':>15s} {'Percent':>8s} {'Transactions':>15s}")
        print("-" * 100)

        for account, num_tx, amount in result_rows:
            category = account.replace('Income:', '').replace('-', ' ')
            percentage = (abs(amount) / abs(total_income) * 100) if total_income != 0 else 0
            print(f"{category:<35s} {format_currency(-amount):>15s} {percentage:>7.1f}% {num_tx:>15,d} txns")

        print("-" * 100)
        print(f"{'TOTAL':<35s} {format_currency(-total_income):>15s} {100.0:>7.1f}%")
        print()

    # Summary statistics
    total_income_query = """
        SELECT sum(convert(position, 'AUD')) FROM OPEN ON 2025-11-01 CLOSE ON 2025-12-01 WHERE account ~ '^Income:'
    """
    _, income_rows = run_query(ledger_file, total_income_query)

    total_expenses_query = """
        SELECT sum(convert(position, 'AUD')) FROM OPEN ON 2025-11-01 CLOSE ON 2025-12-01 WHERE account ~ '^Expenses:'
    """
    _, expense_rows = run_query(ledger_file, total_expenses_query)

    if income_rows and expense_rows:
        income = -income_rows[0][0] if income_rows[0][0] else 0
        expenses = expense_rows[0][0] if expense_rows[0][0] else 0
        net = income - expenses
        savings_rate = (net / income * 100) if income > 0 else 0

        print("\n" + "=" * 100)
        print(" " * 40 + "FINANCIAL SUMMARY")
        print("=" * 100)
        print(f"\n  Total Income:        {format_currency(income):>20s}")
        print(f"  Total Expenses:      {format_currency(expenses):>20s}")
        print(f"  {'-' * 50}")
        print(f"  Net Income/Savings:  {format_currency(net):>20s}")
        print(f"  Savings Rate:        {savings_rate:>19.1f}%")
        print()

        # Category insights
        print("=" * 100)
        print(" " * 40 + "KEY INSIGHTS")
        print("=" * 100)

        # Re-query for expense details to ensure we have the right data
        expenses_for_insights_query = """
            SELECT account, sum(convert(position, 'AUD')) as total
            FROM OPEN ON 2025-11-01 CLOSE ON 2025-12-01
            WHERE account ~ '^Expenses:'
            GROUP BY account
            ORDER BY total DESC
            LIMIT 1
        """
        _, insight_rows = run_query(ledger_file, expenses_for_insights_query)

        if insight_rows:
            top_expense = insight_rows[0]
            top_category = top_expense[0].replace('Expenses:', '').replace('-', ' ')
            top_amount = top_expense[1]
            top_pct = (top_amount / expenses * 100) if expenses > 0 else 0

            print(f"\n  • Largest expense category: {top_category} ({format_currency(top_amount)}, {top_pct:.1f}% of total)")

            if len(result_rows) > 1:
                categories_count = len(result_rows)
                print(f"  • Number of expense categories used: {categories_count}")

            if net < 0:
                print(f"  • ⚠ WARNING: You spent {format_currency(abs(net))} more than you earned this month")
            else:
                print(f"  • ✓ You saved {format_currency(net)} this month ({savings_rate:.1f}% savings rate)")

        print()
        print("=" * 100)


if __name__ == "__main__":
    ledger_file = "/Users/nelson/.local/finance-vault/main.beancount"
    generate_detailed_report(ledger_file)
