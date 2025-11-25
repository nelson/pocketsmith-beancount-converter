# bean-query Examples and Output

Here are various bean-query examples run on your ledger, showing the BQL syntax and actual output:

## 1. Expenses by Category (November 2025)

**Query:**
```sql
SELECT account, sum(position)
WHERE account ~ '^Expenses:' AND year = 2025 AND month = 11
GROUP BY account
ORDER BY sum(position) DESC;
```

**Output:**
```
account                  sum(position
----------------------  ------------
Expenses:Uncategorized  104271.6 AUD
Expenses:Eating-Out        746.2 AUD
```

---

## 2. Income by Category (November 2025)

**Query:**
```sql
SELECT account, sum(position)
WHERE account ~ '^Income:' AND year = 2025 AND month = 11
GROUP BY account;
```

**Output:**
```
      account         sum(position
--------------------  ------------
Income:Uncategorized  -93751.0 AUD
```

*Note: Income amounts are negative in double-entry accounting.*

---

## 3. Top 10 Expense Transactions

**Query:**
```sql
SELECT date, narration, account, position
WHERE account ~ '^Expenses:' AND year = 2025 AND month = 11
ORDER BY position DESC
LIMIT 10;
```

**Output:**
```
date         narration  account                  position
----------  -----------  ----------------------  -----------
2025-11-12              Expenses:Uncategorized  41307.0 AUD
2025-11-11              Expenses:Uncategorized   9971.8 AUD
2025-11-14              Expenses:Uncategorized   5500.0 AUD
2025-11-14              Expenses:Uncategorized   5500.0 AUD
2025-11-18              Expenses:Uncategorized   5500.0 AUD
2025-11-10              Expenses:Uncategorized   5368.0 AUD
2025-11-18              Expenses:Uncategorized   3377.0 AUD
2025-11-02              Expenses:Uncategorized   2358.0 AUD
2025-11-20              Expenses:Uncategorized   2100.0 AUD
2025-11-18              Expenses:Uncategorized   1497.9 AUD
```

---

## 4. Monthly Expenses Over Time

**Query:**
```sql
SELECT year, month, sum(convert(position, 'AUD')) as total
WHERE account ~ '^Expenses:' AND year >= 2024
GROUP BY year, month
ORDER BY year DESC, month DESC
LIMIT 12;
```

**Output:**
```
year  month          total
----  -----  ------------------------
2025     11   105017.8 AUD
2025     10   141535.0 AUD
2025      9   111631.7 AUD  86.17 USD
2025      8    72114.8 AUD
2025      7   113189.7 AUD
2025      6    59233.6 AUD
2025      5  1796074.6 AUD
2025      4    53359.9 AUD
2025      3    43419.4 AUD
2025      2    45722.8 AUD
2025      1    64928.1 AUD
2024     12   138560.3 AUD
```

*Note: May 2025 had unusually high expenses ($1.8M) - possibly a property purchase or large one-off expense.*

---

## 5. Account Balances (November 2025)

**Query:**
```sql
BALANCES FROM year = 2025 AND month = 11;
```

**Output:**
```
                       account                          SUM(position)
------------------------------------------------------  -------------
Assets:American-Express:American-Express-Platinum-Card    23597.8 AUD
Assets:Anz:Anz-One-Offset-Account                        -46448.1 AUD
Assets:Anz:Variable-Home-Loan                              4603.7 AUD
Assets:Commonwealth-Bank-Cba:Bills                          993.2 AUD
Assets:Commonwealth-Bank-Cba:Everyday                      1309.2 AUD
Assets:Macquarie:Offset-Account                            3725.9 AUD
Assets:Wise:Lok-Sun-Nelson-Tam                              951.4 AUD
Income:Uncategorized                                     -93751.0 AUD
Expenses:Eating-Out                                         746.2 AUD
Expenses:Uncategorized                                   104271.6 AUD
```

---

## 6. Eating Out Transactions with Count

**Query:**
```sql
SELECT account, count(*) as num_txns, sum(convert(position, 'AUD')) as total
WHERE account ~ '^Expenses:Eating' AND year = 2025 AND month = 11
GROUP BY account;
```

**Output:**
```
account              num_txns    total
-------------------  --------  ---------
Expenses:Eating-Out        20  746.2 AUD
```

---

## 7. All Eating Out Transactions by Date

**Query:**
```sql
SELECT date, account, convert(position, 'AUD') as amount
WHERE account ~ '^Expenses:Eating' AND year = 2025 AND month = 11
ORDER BY date;
```

**Output:**
```
   date           account          amount
----------  -------------------  ---------
2025-11-01  Expenses:Eating-Out   14.5 AUD
2025-11-04  Expenses:Eating-Out   18.1 AUD
2025-11-04  Expenses:Eating-Out   67.7 AUD
2025-11-05  Expenses:Eating-Out   25.4 AUD
2025-11-06  Expenses:Eating-Out   34.7 AUD
2025-11-06  Expenses:Eating-Out   49.7 AUD
2025-11-07  Expenses:Eating-Out   50.0 AUD
2025-11-08  Expenses:Eating-Out  138.4 AUD
2025-11-10  Expenses:Eating-Out   50.0 AUD
2025-11-11  Expenses:Eating-Out   17.0 AUD
2025-11-12  Expenses:Eating-Out   29.1 AUD
2025-11-12  Expenses:Eating-Out   50.0 AUD
2025-11-17  Expenses:Eating-Out   30.0 AUD
2025-11-18  Expenses:Eating-Out    9.7 AUD
2025-11-20  Expenses:Eating-Out   10.1 AUD
2025-11-21  Expenses:Eating-Out   30.5 AUD
2025-11-22  Expenses:Eating-Out   19.3 AUD
2025-11-22  Expenses:Eating-Out    9.7 AUD
2025-11-23  Expenses:Eating-Out   30.4 AUD
2025-11-24  Expenses:Eating-Out   61.7 AUD
```

**Summary:** 20 eating out transactions totaling $746.20, average of $37.31 per transaction.

---

## Key BQL Features Demonstrated

1. **Filtering:** Use `WHERE` with account patterns (`~`), dates (`year`, `month`), and currency
2. **Aggregation:** `sum()`, `count()`
3. **Grouping:** `GROUP BY` for category summaries
4. **Sorting:** `ORDER BY` with `ASC`/`DESC`
5. **Limiting:** `LIMIT` for top N results
6. **Currency Conversion:** `convert(position, 'AUD')` to normalize to single currency
7. **Date Ranges:** Filter by `year`, `month`, or use `OPEN ON ... CLOSE ON` syntax
8. **Pattern Matching:** Regex patterns with `~` operator
9. **Balance Queries:** `BALANCES FROM` for account balances

## Interactive Mode

To use bean-query interactively:

```bash
uv run bean-query ~/.local/finance-vault/main.beancount
```

This opens an interactive shell where you can type queries and explore your data. Use `.help` for commands.

## Limitations Found

- `DISTINCT` keyword is not supported
- `CASE` statements are not supported
- Some SQL features may not be available - BQL is a subset of SQL

## Tips

- Use regex patterns (`~`) for flexible account filtering
- Convert to single currency for meaningful totals across accounts
- The `year` and `month` attributes make date filtering easy
- Use `LIMIT` to avoid overwhelming output
- Column names can be aliased with `as`
