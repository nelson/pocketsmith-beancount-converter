#!/usr/bin/env python3
"""Generate categorization reports from beancount ledger."""

from beancount import loader
from beancount.core import getters, data
from beancount.ops import summarize
from collections import defaultdict
from datetime import date
import sys


def generate_categorization_report(ledger_file: str, start_date: date, end_date: date):
    """Generate a categorization report for a specific period."""

    # Load the ledger
    entries, errors, options = loader.load_file(ledger_file)

    if errors:
        print(f"Errors loading ledger: {errors}", file=sys.stderr)
        return

    # Filter entries by date range
    filtered_entries = [
        entry for entry in entries
        if isinstance(entry, data.Transaction) and start_date <= entry.date <= end_date
    ]

    # Categorize transactions
    income_by_category = defaultdict(lambda: defaultdict(float))
    expense_by_category = defaultdict(lambda: defaultdict(float))

    for entry in filtered_entries:
        for posting in entry.postings:
            account = posting.account
            if posting.units is None:
                continue

            amount = float(posting.units.number)
            currency = posting.units.currency

            if account.startswith('Income:'):
                # Income accounts have negative amounts in double-entry
                # We want positive numbers for income
                income_by_category[account][currency] += -amount
            elif account.startswith('Expenses:'):
                expense_by_category[account][currency] += amount

    # Print report
    print("=" * 80)
    print(f"CATEGORIZATION REPORT: {start_date} to {end_date}")
    print("=" * 80)
    print()

    # Income section
    print("INCOME BY CATEGORY")
    print("-" * 80)
    total_income = defaultdict(float)

    for account in sorted(income_by_category.keys()):
        category_name = account.replace('Income:', '').replace('-', ' ')
        for currency, amount in sorted(income_by_category[account].items()):
            if amount != 0:
                print(f"  {category_name:50s} {amount:15,.2f} {currency}")
                total_income[currency] += amount

    print("-" * 80)
    for currency, amount in sorted(total_income.items()):
        print(f"  {'TOTAL INCOME':50s} {amount:15,.2f} {currency}")
    print()

    # Expenses section
    print("EXPENSES BY CATEGORY")
    print("-" * 80)
    total_expenses = defaultdict(float)

    for account in sorted(expense_by_category.keys()):
        category_name = account.replace('Expenses:', '').replace('-', ' ')
        for currency, amount in sorted(expense_by_category[account].items()):
            if amount != 0:
                print(f"  {category_name:50s} {amount:15,.2f} {currency}")
                total_expenses[currency] += amount

    print("-" * 80)
    for currency, amount in sorted(total_expenses.items()):
        print(f"  {'TOTAL EXPENSES':50s} {amount:15,.2f} {currency}")
    print()

    # Net section
    print("NET INCOME/SAVINGS")
    print("-" * 80)
    all_currencies = set(total_income.keys()) | set(total_expenses.keys())
    for currency in sorted(all_currencies):
        income = total_income.get(currency, 0)
        expenses = total_expenses.get(currency, 0)
        net = income - expenses
        print(f"  {'Net':50s} {net:15,.2f} {currency}")
        if income > 0:
            savings_rate = (net / income) * 100
            print(f"  {'Savings Rate':50s} {savings_rate:14,.1f}%")

    print("=" * 80)
    print()

    # Category breakdown percentages
    print("EXPENSE BREAKDOWN BY CATEGORY (%)")
    print("-" * 80)

    for currency in sorted(total_expenses.keys()):
        if total_expenses[currency] == 0:
            continue

        print(f"\nCurrency: {currency}")
        print("-" * 80)

        category_amounts = []
        for account in sorted(expense_by_category.keys()):
            if currency in expense_by_category[account]:
                amount = expense_by_category[account][currency]
                if amount != 0:
                    category_amounts.append((account, amount))

        # Sort by amount descending
        category_amounts.sort(key=lambda x: x[1], reverse=True)

        for account, amount in category_amounts:
            category_name = account.replace('Expenses:', '').replace('-', ' ')
            percentage = (amount / total_expenses[currency]) * 100
            bar = '█' * int(percentage / 2)
            print(f"  {category_name:30s} {amount:12,.2f} ({percentage:5.1f}%) {bar}")

    print("=" * 80)


if __name__ == "__main__":
    ledger_file = "/Users/nelson/.local/finance-vault/main.beancount"

    # November 2025
    start_date = date(2025, 11, 1)
    end_date = date(2025, 11, 30)

    generate_categorization_report(ledger_file, start_date, end_date)
