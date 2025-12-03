---
name: monthly-analysis
description: "Complete monthly stock analysis workflow: fetch end-of-month prices, calculate returns/momentum, and merge with fundamentals from Rice Data Portal. Self-contained for all monthly analysis tasks."
---

# Monthly Stock Analysis

Provide complete, self-contained workflows for monthly stock analysis including price data, returns, momentum, and fundamental data from SEC filings.

## When to Use This Skill

Use this skill when the user requests:
- Monthly stock returns or prices
- End-of-month data analysis
- Financial data at monthly frequency
- Combining price and fundamental data monthly
- Monthly portfolio analysis or backtesting

## Core Workflow

### Step 1: Check for Precomputed Ratios

**CRITICAL:** Before calculating any financial ratio, check if it already exists in the database.

Run the precomputed check script:
```bash
python .claude/skills/references/scripts/check_precomputed.py
```

This verifies which variables are available in:
- **DAILY table**: marketcap, pb, pe, ps, ev, evebit, evebitda
- **SF1 table**: All income statement, balance sheet, cash flow items, and financial ratios

**Common precomputed ratios:**
- `pb` (price-to-book), `pe` (price-to-earnings), `ps` (price-to-sales)
- `roe` (return on equity), `roa`, `roic`
- `grossmargin`, `netmargin`, `ebitdamargin`
- `de` (debt-to-equity ratio - this is "leverage")
- `assetturnover`, `currentratio`, `quickratio`

**Rule:** Fetch precomputed ratios from the database. Do NOT calculate manually if they exist.

### Step 2: Fetch Monthly Returns

Use the fetch script to get end-of-month prices and calculate returns:

```bash
python .claude/skills/monthly-analysis/scripts/fetch_monthly_data.py START_DATE OUTPUT_FILE
# Example: python .claude/skills/monthly-analysis/scripts/fetch_monthly_data.py 2020-01-01 monthly.parquet
```

**Automatically includes:**
- `ticker`, `month` (YYYY-MM format), `date`
- `close` (split-adjusted price)
- `return` (monthly return, decimal format)
- `momentum` (12-month momentum: month t-13 to t-2)
- `lagged_return` (prior month's return)
- `marketcap` (from DAILY table, already shifted by 1 month)
- `sector`, `industry`, `size` (market cap category)

### Step 3: Fetch Additional Variables

#### From DAILY Table (for precomputed ratios)

Fetch end-of-month values for ratios like pb, pe, ps:

```python
# Pattern: Get end-of-month values, then shift by 1 month
# Query year-by-year to avoid timeouts
# See .claude/skills/references/rice_database_schema.md for query patterns
```

Then shift: `df['pb'] = df.groupby('ticker')['pb'].shift(1)`

#### From SF1 Table (for fundamental data)

Fetch annual (ARY) or quarterly (ARQ) fundamental data:

```python
# Query SF1 table with dimension='ARY' for annual data
# Order by ticker, datekey
# See .claude/skills/references/rice_database_schema.md for schema details
```

**CRITICAL:** Calculate growth rates BEFORE merging:
```python
# Calculate year-over-year growth from fundamental data
df_fund['asset_growth'] = df_fund.groupby('ticker')['assets'].pct_change().round(4)
```

### Step 4: Merge with Fundamentals

```bash
python .claude/skills/monthly-analysis/scripts/merge_monthly_fundamentals.py MONTHLY_FILE FUNDAMENTALS_FILE OUTPUT_FILE
```

The merge script automatically:
- Aligns fundamental data to first month AFTER filing date
- Forward fills fundamental data until next filing
- Shifts close prices to represent prior month's closing price

### Step 5: Shift SF1 Variables

After merging, shift all SF1 variables by 1 month to avoid look-ahead bias:

```python
# Shift each SF1 variable by 1 month (grouped by ticker)
df['roe'] = df.groupby('ticker')['roe'].shift(1)
df['grossmargin'] = df.groupby('ticker')['grossmargin'].shift(1)
df['de'] = df.groupby('ticker')['de'].shift(1)
# Repeat for all SF1 variables
```

## Important Rules

### Avoiding Look-Ahead Bias

**ALL variables from DAILY and SF1 tables must be shifted:**
- DAILY variables: Shift by 1 month after fetching
- SF1 variables: Shift by 1 month after merging
- This ensures variables represent information known at the start of the month

### Return Calculations

**ALWAYS group by ticker when calculating returns:**
```python
df['return'] = df.groupby('ticker')['closeadj'].pct_change().round(4)
df['momentum'] = (
    df.groupby('ticker')['closeadj'].shift(2) /
    df.groupby('ticker')['closeadj'].shift(13) - 1
).round(4)
```

Returns are expressed as decimals (0.05 = 5% return), rounded to 4 decimal places.

### Growth Rate Calculations

Calculate growth rates from fundamental data BEFORE merging:
- Use year-over-year for annual data (ARY)
- Use quarter-over-quarter for quarterly data (ARQ)
- Do NOT calculate after merging (forward-fill creates zero growth)

### Query Performance

Query year-by-year to avoid API timeouts:
```python
for year in range(start_year, end_year + 1):
    sql = f"SELECT ... WHERE date::DATE >= '{year}-01-01' AND date::DATE < '{year+1}-01-01'"
    # Execute and append results
```

## Output Format

Final dataset columns:
- `ticker`: Stock symbol
- `month`: Month label (YYYY-MM format, e.g., '2025-01')
- `return`: Monthly return (decimal)
- `momentum`: 12-month momentum (decimal)
- `lagged_return`: Prior month return (decimal)
- `close`: Prior month's closing price (shifted)
- `marketcap`: Market cap in thousands (from DAILY, shifted)
- `sector`, `industry`: Classifications
- `size`: Market cap category (Nano, Micro, Small, Mid, Large, Mega)
- Additional variables from DAILY/SF1 as requested (all shifted)

## Database Schema Reference

For complete database schema, table structures, and query patterns, see:
**`.claude/skills/references/rice_database_schema.md`**

Search for:
- "DAILY Table" - precomputed valuation ratios
- "SF1 Table" - fundamental data from SEC filings
- "SEP Table" - price data
- "Common Query Patterns" - SQL templates

## Scripts Available

Scripts in `.claude/skills/monthly-analysis/scripts/`:
1. **fetch_monthly_data.py** - Get end-of-month prices and returns
2. **merge_monthly_fundamentals.py** - Merge returns with fundamental data

Shared scripts in `.claude/skills/references/scripts/`:
1. **check_precomputed.py** - Verify which ratios exist in database
2. **precomputed_variables.py** - List of all precomputed variables

## Key Reminders

- ✅ Check for precomputed ratios BEFORE calculating
- ✅ Fetch from DAILY/SF1 tables when variables exist
- ✅ Shift ALL DAILY variables by 1 month after fetching
- ✅ Calculate growth rates BEFORE merging
- ✅ Shift ALL SF1 variables by 1 month after merging
- ✅ Always group by ticker for returns and growth rates
- ✅ Query year-by-year to avoid timeouts
- ✅ Use decimal format for returns (not percentages)
