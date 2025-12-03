---
name: weekly-analysis
description: "Complete weekly stock analysis workflow: fetch end-of-week prices, calculate returns/momentum, and merge with fundamentals from Rice Data Portal. Self-contained for all weekly analysis tasks."
---

# Weekly Stock Analysis

Provide complete, self-contained workflows for weekly stock analysis including price data, returns, momentum, and fundamental data from SEC filings.

## When to Use This Skill

Use this skill when the user requests:
- Weekly stock returns or prices
- End-of-week data analysis
- Financial data at weekly frequency
- Combining price and fundamental data weekly
- Weekly portfolio analysis or backtesting
- Higher frequency analysis than monthly

## Core Workflow

### Step 1: Check for Precomputed Ratios

**CRITICAL:** Before calculating any financial ratio, check if it already exists in the database.

Use the precomputed check script (shared across both skills):
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

### Step 2: Fetch Weekly Returns

Use the fetch script to get end-of-week prices and calculate returns:

```bash
python .claude/skills/weekly-analysis/scripts/fetch_weekly_data.py START_DATE OUTPUT_FILE
# Example: python .claude/skills/weekly-analysis/scripts/fetch_weekly_data.py 2020-01-01 weekly.parquet
```

**Automatically includes:**
- `ticker`, `week` (ISO week format: YYYY-WW), `date`
- `close` (split-adjusted price)
- `return` (weekly return, decimal format)
- `momentum` (48-week momentum: week t-53 to t-5)
- `lag_month` (4-week return: week t-5 to t-1)
- `lag_week` (prior week's return)
- `marketcap` (from DAILY table, already shifted by 1 week)
- `sector`, `industry`, `size` (market cap category)

**ISO Week Format:**
- Weeks labeled as '2025-W01', '2025-W02', etc.
- Week 1 = first week with at least 4 days in new year
- Some years have 53 weeks (e.g., 2020, 2026, 2032)

### Step 3: Fetch Additional Variables

#### From DAILY Table (for precomputed ratios)

Fetch end-of-week values for ratios like pb, pe, ps:

```python
# Pattern: Get end-of-week values, then shift by 1 week
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
python .claude/skills/weekly-analysis/scripts/merge_weekly_fundamentals.py WEEKLY_FILE FUNDAMENTALS_FILE OUTPUT_FILE
```

The merge script automatically:
- Converts filing date to ISO week format
- Shifts data one week forward (filed in week N → available week N+1)
- Forward fills fundamental data until next filing
- Shifts close prices to represent prior week's closing price

### Step 5: Shift SF1 Variables

After merging, shift all SF1 variables by 1 week to avoid look-ahead bias:

```python
# Shift each SF1 variable by 1 week (grouped by ticker)
df['roe'] = df.groupby('ticker')['roe'].shift(1)
df['grossmargin'] = df.groupby('ticker')['grossmargin'].shift(1)
df['de'] = df.groupby('ticker')['de'].shift(1)
# Repeat for all SF1 variables
```

## Important Rules

### Avoiding Look-Ahead Bias

**ALL variables from DAILY and SF1 tables must be shifted:**
- DAILY variables: Shift by 1 week after fetching
- SF1 variables: Shift by 1 week after merging
- This ensures variables represent information known at the start of the week

### Return Calculations

**ALWAYS group by ticker when calculating returns:**
```python
df['return'] = df.groupby('ticker')['closeadj'].pct_change().round(4)
df['momentum'] = (
    df.groupby('ticker')['closeadj'].shift(5) /
    df.groupby('ticker')['closeadj'].shift(53) - 1
).round(4)
```

Returns are expressed as decimals (0.02 = 2% return), rounded to 4 decimal places.

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

### ISO Week Edge Cases

- Early January dates may belong to prior year's Week 52/53
- Late December dates may belong to next year's Week 01
- This is normal ISO 8601 week numbering behavior

## Output Format

Final dataset columns:
- `ticker`: Stock symbol
- `week`: ISO week label (YYYY-WW format, e.g., '2025-W01')
- `return`: Weekly return (decimal)
- `momentum`: 48-week momentum (decimal)
- `lag_month`: 4-week return (decimal)
- `lag_week`: Prior week return (decimal)
- `close`: Prior week's closing price (shifted)
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

Scripts in `.claude/skills/weekly-analysis/scripts/`:
1. **fetch_weekly_data.py** - Get end-of-week prices and returns
2. **merge_weekly_fundamentals.py** - Merge returns with fundamental data

Shared scripts in `.claude/skills/references/scripts/`:
1. **check_precomputed.py** - Verify which ratios exist in database
2. **precomputed_variables.py** - List of all precomputed variables

## Key Reminders

- ✅ Check for precomputed ratios BEFORE calculating
- ✅ Fetch from DAILY/SF1 tables when variables exist
- ✅ Shift ALL DAILY variables by 1 week after fetching
- ✅ Calculate growth rates BEFORE merging
- ✅ Shift ALL SF1 variables by 1 week after merging
- ✅ Always group by ticker for returns and growth rates
- ✅ Query year-by-year to avoid timeouts
- ✅ Use decimal format for returns (not percentages)
- ✅ Understand ISO week format (weeks may span year boundaries)
