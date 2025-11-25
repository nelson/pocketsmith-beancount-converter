#!/usr/bin/env python3
"""Generate categorization reports using BQL queries."""

from beancount import loader
from beanquery import query
import sys


def run_query(ledger_file: str, bql_query: str):
    """Run a BQL query and return results."""
    entries, errors, options = loader.load_file(ledger_file)

    if errors:
        print(f"Errors loading ledger: {errors}", file=sys.stderr)
        return None

    result_types, result_rows = query.run_query(
        entries, options, bql_query, numberify=True
    )

    return result_types, result_rows


def print_table(result_types, result_rows, title=""):
    """Print query results as a formatted table."""
    if title:
        print(f"\n{title}")
        print("=" * 80)

    if not result_rows:
        print("No data found.")
        return

    # Get column names
    col_names = [rt[0] for rt in result_types]

    # Calculate column widths
    col_widths = [len(name) for name in col_names]
    for row in result_rows:
        for i, cell in enumerate(row):
            cell_str = str(cell) if cell is not None else ""
            col_widths[i] = max(col_widths[i], len(cell_str))

    # Print header
    header = "  ".join(f"{name:{width}}" for name, width in zip(col_names, col_widths))
    print(header)
    print("-" * len(header))

    # Print rows
    for row in result_rows:
        row_str = "  ".join(
            f"{str(cell) if cell is not None else '':{width}}"
            for cell, width in zip(row, col_widths)
        )
        print(row_str)

    print()


def generate_reports(ledger_file: str):
    """Generate various categorization reports."""

    print("=" * 80)
    print("CATEGORIZATION REPORT - NOVEMBER 2025")
    print("=" * 80)

    # Query 1: Income by category
    income_query = """
        SELECT
            account,
            sum(position) as total
        FROM
            OPEN ON 2025-11-01 CLOSE ON 2025-12-01
        WHERE
            account ~ '^Income:'
        GROUP BY account
        ORDER BY account
    """

    result_types, result_rows = run_query(ledger_file, income_query)
    print_table(result_types, result_rows, "INCOME BY CATEGORY")

    # Query 2: Expenses by category
    expenses_query = """
        SELECT
            account,
            sum(position) as total
        FROM
            OPEN ON 2025-11-01 CLOSE ON 2025-12-01
        WHERE
            account ~ '^Expenses:'
        GROUP BY account
        ORDER BY account
    """

    result_types, result_rows = run_query(ledger_file, expenses_query)
    print_table(result_types, result_rows, "EXPENSES BY CATEGORY")

    # Query 3: Total income
    total_income_query = """
        SELECT
            sum(convert(position, 'AUD')) as total_income_aud
        FROM
            OPEN ON 2025-11-01 CLOSE ON 2025-12-01
        WHERE
            account ~ '^Income:'
    """

    result_types, result_rows = run_query(ledger_file, total_income_query)
    print("\nTOTAL INCOME")
    print("=" * 80)
    if result_rows:
        total_income = result_rows[0][0]
        print(f"Total Income (AUD): {-total_income:,.2f}")  # Negate because income is negative

    # Query 4: Total expenses
    total_expenses_query = """
        SELECT
            sum(convert(position, 'AUD')) as total_expenses_aud
        FROM
            OPEN ON 2025-11-01 CLOSE ON 2025-12-01
        WHERE
            account ~ '^Expenses:'
    """

    result_types, result_rows = run_query(ledger_file, total_expenses_query)
    print("\nTOTAL EXPENSES")
    print("=" * 80)
    if result_rows:
        total_expenses = result_rows[0][0]
        print(f"Total Expenses (AUD): {total_expenses:,.2f}")

        # Calculate net
        net = -total_income - total_expenses
        print(f"\nNet Income/Savings (AUD): {net:,.2f}")
        if total_income != 0:
            savings_rate = (net / -total_income) * 100
            print(f"Savings Rate: {savings_rate:.1f}%")
    print()

    # Query 5: Top expenses (excluding transfers)
    top_expenses_query = """
        SELECT
            account,
            sum(convert(position, 'AUD')) as total_aud
        FROM
            OPEN ON 2025-11-01 CLOSE ON 2025-12-01
        WHERE
            account ~ '^Expenses:'
            AND NOT account ~ 'Transfer'
        GROUP BY account
        ORDER BY total_aud DESC
        LIMIT 10
    """

    result_types, result_rows = run_query(ledger_file, top_expenses_query)
    print_table(result_types, result_rows, "TOP 10 EXPENSE CATEGORIES (in AUD)")

    print("=" * 80)


if __name__ == "__main__":
    ledger_file = "/Users/nelson/.local/finance-vault/main.beancount"
    generate_reports(ledger_file)
