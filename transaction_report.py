#!/usr/bin/env python3
"""Generate transaction-level categorization report."""

from beancount import loader
from beanquery import query


def run_query(ledger_file: str, bql_query: str):
    """Run a BQL query and return results."""
    entries, errors, options = loader.load_file(ledger_file)

    if errors:
        return None, None

    result_types, result_rows = query.run_query(
        entries, options, bql_query, numberify=True
    )

    return result_types, result_rows


def generate_transaction_report(ledger_file: str):
    """Generate a transaction-level report."""

    print("=" * 120)
    print(" " * 40 + "TOP EXPENSE TRANSACTIONS - NOVEMBER 2025")
    print("=" * 120)
    print()

    # Get largest expense transactions
    large_expenses_query = """
        SELECT
            date,
            narration,
            account,
            convert(position, 'AUD') as amount_aud
        FROM
            OPEN ON 2025-11-01 CLOSE ON 2025-12-01
        WHERE
            account ~ '^Expenses:'
        ORDER BY amount_aud DESC
        LIMIT 25
    """

    result_types, result_rows = run_query(ledger_file, large_expenses_query)

    if result_rows:
        print(f"{'Date':<12s} {'Category':<25s} {'Amount':>15s} {'Description':<60s}")
        print("-" * 120)

        for date_obj, description, account, amount in result_rows:
            category = account.replace('Expenses:', '').replace('-', ' ')
            desc_short = (description[:57] + '...') if len(description) > 60 else description
            print(f"{str(date_obj):<12s} {category:<25s} ${amount:>13,.2f} {desc_short:<60s}")

        print()

    # Get income transactions
    print("=" * 120)
    print(" " * 40 + "INCOME TRANSACTIONS - NOVEMBER 2025")
    print("=" * 120)
    print()

    income_query = """
        SELECT
            date,
            narration,
            account,
            convert(position, 'AUD') as amount_aud
        FROM
            OPEN ON 2025-11-01 CLOSE ON 2025-12-01
        WHERE
            account ~ '^Income:'
        ORDER BY amount_aud
        LIMIT 25
    """

    result_types, result_rows = run_query(ledger_file, income_query)

    if result_rows:
        print(f"{'Date':<12s} {'Category':<25s} {'Amount':>15s} {'Description':<60s}")
        print("-" * 120)

        for date_obj, description, account, amount in result_rows:
            category = account.replace('Income:', '').replace('-', ' ')
            desc_short = (description[:57] + '...') if len(description) > 60 else description
            # Income amounts are negative, so negate them for display
            print(f"{str(date_obj):<12s} {category:<25s} ${-amount:>13,.2f} {desc_short:<60s}")

        print()

    # Get transactions by category
    print("=" * 120)
    print(" " * 40 + "EXPENSE DISTRIBUTION BY DATE")
    print("=" * 120)
    print()

    daily_expenses_query = """
        SELECT
            date,
            count(*) as num_transactions,
            sum(convert(position, 'AUD')) as total_aud
        FROM
            OPEN ON 2025-11-01 CLOSE ON 2025-12-01
        WHERE
            account ~ '^Expenses:'
        GROUP BY date
        ORDER BY total_aud DESC
        LIMIT 20
    """

    result_types, result_rows = run_query(ledger_file, daily_expenses_query)

    if result_rows:
        print(f"{'Date':<12s} {'Transactions':>15s} {'Total Amount':>20s}")
        print("-" * 120)

        for date_obj, num_tx, amount in result_rows:
            print(f"{str(date_obj):<12s} {num_tx:>15,d} ${amount:>18,.2f}")

        print()

    print("=" * 120)


if __name__ == "__main__":
    ledger_file = "/Users/nelson/.local/finance-vault/main.beancount"
    generate_transaction_report(ledger_file)
