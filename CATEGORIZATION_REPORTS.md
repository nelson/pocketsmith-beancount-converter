# Beancount Categorization Reports - Overview and Solutions

## Existing Beancount Reporting Solutions

### 1. **Fava** (Most Popular)
Web-based interface for Beancount with rich visualization and reporting features.

**Features:**
- Income statements with treemap and sunburst chart visualizations
- Balance sheets and net worth tracking over time
- Interactive filtering and drill-down capabilities
- Custom dashboards via extensions (fava-dashboards, fava-investor)
- Budget tracking and portfolio analysis

**Installation:**
```bash
pip install fava
```

**Usage:**
```bash
fava ~/.local/finance-vault/main.beancount
# Opens web interface at http://localhost:5000
```

**Pros:**
- Best for visual, interactive exploration
- No coding required
- Real-time updates as you edit ledger files
- Beautiful charts and graphs

**Cons:**
- Requires running a web server
- Limited customization without extensions

---

### 2. **bean-query** (Command-Line SQL Interface)
SQL-like query tool for beancount ledgers (replaces deprecated bean-report in v3).

**Features:**
- SQL-like BQL (Beancount Query Language) syntax
- Export to various formats (text, CSV)
- Scriptable and automatable
- Fast filtering and aggregation

**Installation:**
```bash
pip install beanquery
```

**Usage:**
```bash
# Interactive mode
bean-query ~/.local/finance-vault/main.beancount

# Or in Python
from beanquery import query
result_types, result_rows = query.run_query(entries, options, bql_query)
```

**Example BQL Queries:**

```sql
-- Total expenses by category for November 2025
SELECT
    account,
    sum(convert(position, 'AUD')) as total
FROM
    OPEN ON 2025-11-01 CLOSE ON 2025-12-01
WHERE
    account ~ '^Expenses:'
GROUP BY account
ORDER BY total DESC
```

**Pros:**
- Powerful query capabilities
- Great for automation and scripting
- Fast and efficient
- Can export to CSV for use in Excel/Sheets

**Cons:**
- Requires learning BQL syntax
- Text-based output (no visualizations)
- Limited presentation features

---

### 3. **beancount-multiperiod-reports**
Jupyter notebook-based tool for advanced time-series analysis.

**Features:**
- Monthly/quarterly/yearly pivot reports
- Time-series charts of income and expenses
- Treemap visualizations of expense categories
- Pandas-based data processing

**Installation:**
```bash
git clone https://github.com/isabekov/beancount-multiperiod-reports
cd beancount-multiperiod-reports
pip install -r requirements.txt
jupyter lab
```

**Usage:**
- Open Jupyter notebooks
- Load your ledger file
- Run analysis cells
- Generate charts and pivot tables

**Pros:**
- Great for data analysis and exploration
- Beautiful visualizations
- Flexible with Pandas/Python
- Can export charts as images

**Cons:**
- Requires Jupyter setup
- Steeper learning curve
- Not real-time (requires re-running cells)

---

## Custom Scripts for Your Ledger

I've created three reporting scripts for your ledger:

### 1. `query_report.py` - Basic BQL Report
Simple categorization report using bean-query.

**Run:**
```bash
uv run python query_report.py
```

**Output:**
- Income by category
- Expenses by category
- Summary totals
- Top 10 expense categories

### 2. `detailed_report.py` - Enhanced Visual Report
Detailed report with bar charts and insights.

**Run:**
```bash
uv run python detailed_report.py
```

**Output:**
- Expense breakdown with percentages and transaction counts
- Visual bar charts
- Income breakdown
- Financial summary (income, expenses, savings rate)
- Key insights and warnings

### 3. `transaction_report.py` - Transaction-Level Analysis
Shows individual transactions and daily patterns.

**Run:**
```bash
uv run python transaction_report.py
```

**Output:**
- Top 25 expense transactions
- All income transactions
- Expense distribution by date
- Highest spending days

---

## November 2025 Summary from Your Ledger

Based on the reports generated:

```
Total Income:        $93,751.00 (40 transactions)
Total Expenses:     $105,017.80 (275 transactions)
Net Income/Savings: -$11,266.80
Savings Rate:           -12.0%

Expense Breakdown:
  - Uncategorized:    $104,271.60 (99.3%)  - 255 transactions
  - Eating Out:           $746.20 (0.7%)   - 20 transactions

Top Expense Days:
  - Nov 12: $42,200.20 (14 transactions)
  - Nov 18: $11,626.70 (18 transactions)
  - Nov 14: $11,514.50 (12 transactions)
```

**Key Observation:** Most of your transactions (99.3%) are currently uncategorized, which suggests that implementing automatic categorization rules or manually categorizing transactions would provide much more valuable insights.

---

## Recommendations

1. **For Quick Visual Exploration:** Use **Fava**
   - Best for getting started
   - Easy to filter and explore data
   - No coding required

2. **For Automated Reports:** Use **bean-query** or the custom scripts
   - Run on schedule (daily/weekly/monthly)
   - Export to CSV for sharing
   - Integrate with other tools

3. **For Deep Analysis:** Use **beancount-multiperiod-reports**
   - Compare month-over-month trends
   - Identify spending patterns over time
   - Create presentation-ready charts

4. **Improve Categorization:**
   - Most transactions are in "Uncategorized"
   - Consider using `beancount-categorizer` for automatic categorization
   - Or use your existing pocketsmith-beancount-converter rules to map transactions to proper categories

---

## Next Steps

To add categorization functionality to your project, you could:

1. **Integrate with your existing converter:**
   - Add category mapping rules to your PocketSmith import process
   - Use the existing account categories from PocketSmith

2. **Use beancount-categorizer:**
   - Set up regex patterns to automatically categorize transactions
   - Apply during import or as a post-processing step

3. **Build custom reporting:**
   - Extend the scripts I created
   - Add more visualizations (matplotlib/plotly)
   - Create HTML reports
   - Set up automated email reports

Would you like me to help implement any of these enhancements to your converter project?
