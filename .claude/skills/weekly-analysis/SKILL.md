---
name: weekly-analysis
description: "Complete weekly stock analysis workflow: fetch end-of-week prices, calculate returns/momentum, and merge with fundamentals from Rice Data Portal. Self-contained for all weekly analysis tasks."
---

# Weekly Stock Analysis Expert

You are an expert in weekly stock analysis, fetching data from the Rice Data Portal and providing complete analysis-ready datasets.

## OVERVIEW

This skill provides a **complete, self-contained workflow** for weekly stock analysis:
1. **Fetch** end-of-week prices and valuation metrics from Rice Data Portal
2. **Calculate** weekly returns and momentum
3. **Fetch** fundamental data from 10K/10Q filings
4. **Merge** all data into analysis-ready weekly dataset

---

## 🚨 MANDATORY FIRST STEP: READ TABLE SCHEMAS 🚨

**BEFORE fetching or calculating ANY variable, you MUST:**

### Step 1: Identify What Variables the User Needs

Make a list of all variables requested (e.g., pb, roe, leverage, marketcap, etc.)

### Step 2: Read the Relevant Table Schema Sections

**Jump to these sections in this document and READ them:**
- **DAILY Table** → Search for "## DATABASE SCHEMA" then "### DAILY Table"
- **SF1 Table** → Search for "## DATABASE SCHEMA" then "### SF1 Table"

### Step 3: Check Each Variable

For EACH variable the user wants:
- ✅ **In DAILY table?** → Fetch from DAILY (then shift by 1 week)
- ✅ **In SF1 table?** → Fetch from SF1 (then shift by 1 week)
- ✅ **In neither?** → OK to calculate manually
- ❌ **NEVER calculate a variable that exists in DAILY or SF1**

### Step 4: Common Variables (Quick Reference)

**Price/valuation ratios (in DAILY and SF1):**
- `pb` = price-to-book ratio
- `pe` = price-to-earnings ratio
- `ps` = price-to-sales ratio

**Debt/equity (in SF1 only):**
- `de` = debt-to-equity ratio (this is "leverage")

**Profitability ratios (in SF1 only):**
- `roe`, `roa`, `roic`
- `grossmargin`, `netmargin`, `ebitdamargin`
- `assetturnover`

**If you want leverage:** Fetch `de` from SF1 table. Do NOT calculate as debt/equity.
**If you want price-to-book:** Fetch `pb` from DAILY table. Do NOT calculate as marketcap/equity.

### Step 5: Shifting Rule

**ALL variables from DAILY and SF1 MUST be shifted by 1 week** (grouped by ticker):
```python
# After fetching variables from DAILY or SF1:
df['pb'] = df.groupby('ticker')['pb'].shift(1)
df['roe'] = df.groupby('ticker')['roe'].shift(1)
df['marketcap'] = df.groupby('ticker')['marketcap'].shift(1)
```

This avoids look-ahead bias - variables represent prior week's values.

---

## UTILITY SCRIPTS

**Located in `.claude/skills/weekly-analysis/`:**

### 1. Fetch Weekly Returns (with Marketcap)

```bash
python .claude/skills/weekly-analysis/fetch_weekly_data.py START_DATE OUTPUT_FILE
# For all stocks: python .claude/skills/weekly-analysis/fetch_weekly_data.py 2020-01-01 weekly.parquet
# For specific tickers: python .claude/skills/weekly-analysis/fetch_weekly_data.py AAPL,MSFT 2020-01-01 weekly.parquet
```

**Automatically includes:**
- `ticker`, `week`, `date`
- `close`, `return`, `momentum`, `lag_week`
- `marketcap` (from DAILY table, already shifted by 1 week)
- `sector`, `industry`, `size`

### 2. Merge with Fundamentals

```bash
python .claude/skills/weekly-analysis/merge_weekly_fundamentals.py WEEKLY_FILE FUNDAMENTALS_FILE OUTPUT_FILE
```

**Automatically handles:**
- First week AFTER filing date
- Forward fills fundamental data
- Shifts close prices

**⚠️ WARNING:** The merge script currently calculates `pb` - this is WRONG. You must fetch `pb` from DAILY instead.

---

## COMPLETE WORKFLOW

### Step 1: Fetch Weekly Returns

```bash
python .claude/skills/weekly-analysis/fetch_weekly_data.py 2010-01-01 weekly_returns.parquet
```

This gets: ticker, week, date, close, return, momentum, lag_week, marketcap (shifted), sector, industry, size

### Step 2: Fetch Additional DAILY Variables (if needed)

**Example: If you need pb from DAILY table:**

Write a Python script to fetch pb from DAILY table (year-by-year), then shift by 1 week.

**SQL Pattern:**
```sql
WITH week_ends AS (
  SELECT d.ticker, d.date::DATE as date, d.pb,
         ROW_NUMBER() OVER (
           PARTITION BY d.ticker, DATE_TRUNC('week', d.date::DATE)
           ORDER BY d.date::DATE DESC
         ) as rn
  FROM daily d
  WHERE d.date::DATE >= '{year}-01-01'
    AND d.date::DATE < '{year+1}-01-01'
)
SELECT ticker, CAST(date AS VARCHAR) as date, pb
FROM week_ends
WHERE rn = 1
ORDER BY ticker, date
```

Then shift: `df['pb'] = df.groupby('ticker')['pb'].shift(1)`

### Step 3: Fetch SF1 Fundamental Data

**Example: equity, assets, debt, roe, grossmargin, assetturnover, de (leverage)**

Write Python script to fetch from SF1 table (year-by-year), dimension='ARY' for annual data.

**SQL Pattern:**
```sql
SELECT ticker, reportperiod, datekey, equity, assets, debt, roe, grossmargin, assetturnover, de
FROM sf1
WHERE dimension = 'ARY'
  AND reportperiod::DATE >= '{year}-01-01'
  AND reportperiod::DATE < '{year+1}-01-01'
ORDER BY ticker, datekey
```

**CRITICAL:** Calculate any growth rates (e.g., asset_growth) BEFORE merging:
```python
df_fund['asset_growth'] = df_fund.groupby('ticker')['assets'].pct_change().round(4)
```

### Step 4: Merge Everything

```bash
python .claude/skills/weekly-analysis/merge_weekly_fundamentals.py weekly_returns.parquet fundamentals.parquet merged.parquet
```

### Step 5: Shift SF1 Variables

After merging, shift all SF1 variables by 1 week:
```python
df['roe'] = df.groupby('ticker')['roe'].shift(1)
df['grossmargin'] = df.groupby('ticker')['grossmargin'].shift(1)
df['de'] = df.groupby('ticker')['de'].shift(1)
# etc.
```

---

## DATABASE SCHEMA

### Rice Data Portal Connection

**API Endpoint:** `https://data-portal.rice-business.org/api/query`
**Authentication:** Bearer token from environment variable `RICE_ACCESS_TOKEN`

**Setup code:**
```python
import requests
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()
ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')
API_URL = "https://data-portal.rice-business.org/api/query"

response = requests.post(
    API_URL,
    headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"},
    json={"query": sql},
    timeout=120
)
```

### TICKERS Table

**One row per stock - permanent information**

Core columns:
- `ticker`: Stock symbol
- `name`: Company name
- `sector`, `industry`: Classifications
- `exchange`: NYSE, NASDAQ, NYSEMKT (case-sensitive)
- `scalemarketcap`: '1 - Nano', '2 - Micro', '3 - Small', '4 - Mid', '5 - Large', '6 - Mega'
- `isdelisted`: Y or N

### SEP Table (Stock End-of-Day Prices)

**Daily price data**

Core columns:
- `ticker`, `date` (VARCHAR - must cast to DATE)
- `open`, `high`, `low`, `close` (split-adjusted)
- `volume`
- `closeadj`: Close price adjusted for splits, dividends, spinoffs
- **CRITICAL:** `close` is SQL reserved keyword, use alias: `SELECT a.close FROM sep a`

### DAILY Table (Daily Valuation Metrics)

**Daily valuation metrics calculated from prices and fundamentals**

All columns:
- `ticker`, `date` (VARCHAR - must cast to DATE)
- `marketcap`: Market capitalization (**in thousands of USD**)
- `pb`: Price-to-book ratio
- `pe`: Price-to-earnings ratio
- `ps`: Price-to-sales ratio
- `ev`: Enterprise value (millions)
- `evebit`: EV / EBIT ratio
- `evebitda`: EV / EBITDA ratio

**⚠️ IMPORTANT:** `marketcap` values are in thousands. To convert to millions: `marketcap / 1000`

### SF1 Table (Fundamentals from 10-K/10-Q)

**Financial statement data from SEC filings**

**CRITICAL:** SF1 has NO 'date' column! Use `reportperiod`, `datekey`, or `calendardate`.

**Key columns:**
- `ticker`
- `dimension`: ARY (annual), ARQ (quarterly), ART (trailing 12 months) - **ALWAYS use AR dimensions**
- `reportperiod`: Fiscal period end date (e.g., "2024-12-31") - **primary date field**
- `datekey`: SEC filing date
- `fiscalperiod`: Fiscal period name (e.g., "2024-Q4")

**Income Statement:**
- `revenue`, `cor` (cost of revenue), `gp` (gross profit)
- `sgna`, `rnd`, `opex` (operating expenses)
- `opinc` (operating income), `ebit`, `ebitda`
- `intexp` (interest expense), `taxexp`
- `netinc`, `netinccmn` (to common shareholders)
- `eps`, `epsdil`, `shareswa`, `shareswadil`

**Balance Sheet:**
- `assets`, `assetsc` (current assets), `assetssc` (non-current)
- `cashneq`, `inventory`, `receivables`, `ppnenet`
- `liabilities`, `liabilitiesc`, `liabilitiesnc`
- `debt`, `debtc`, `debtnc`
- `equity`, `retearn`, `accoci`

**Cash Flow:**
- `ncfo`, `ncfi`, `ncff`, `ncf`
- `capex`, `fcf`, `depamor`, `sbcomp`

**Financial Ratios (pre-calculated):**
- `roe`, `roa`, `roic`, `ros`
- `grossmargin`, `netmargin`, `ebitdamargin`
- `currentratio`, `quickratio`
- `de` (debt-to-equity ratio)
- `assetturnover`
- `payoutratio`, `divyield`
- `pe`, `pb`, `ps`

**⚠️ All SF1 values are in absolute dollars** (not thousands or millions)

---

## SQL QUERY RULES

### Basic Rules

1. **Only SELECT statements** - no other SQL operations
2. **SF1 has NO 'date' column** - use `reportperiod`, `datekey`, or `calendardate`
3. **All date columns are VARCHAR** - must cast: `reportperiod::DATE`, `date::DATE`
4. **Only reference tables/columns that exist** in the schema above

### Date Handling

**All date comparisons require casting:**
```sql
WHERE date::DATE >= '2020-01-01'
WHERE reportperiod::DATE >= CURRENT_DATE - INTERVAL '5 years'
```

**DuckDB date intervals:**
```sql
INTERVAL '2 years'    -- correct
INTERVAL '6 months'   -- correct
```

### SF1 Dimensions

**ALWAYS use AR (As Reported) dimensions:**
- `ARY` = As Reported Annual (10-K filings)
- `ARQ` = As Reported Quarterly (10-Q filings)
- `ART` = As Reported Trailing 12 months

**NEVER use MR dimensions** (contain restatements)

**SF1 queries must include:**
```sql
SELECT ticker, reportperiod, datekey, [variables]
FROM sf1
WHERE dimension = 'ARY'
  AND reportperiod::DATE >= '2020-01-01'
ORDER BY ticker, datekey  -- CRITICAL: always order by ticker, datekey
```

### End-of-Week Filtering

**For weekly end-of-week prices (SEP table):**
```sql
WITH week_ends AS (
  SELECT a.ticker, a.date::DATE as date, a.close, a.closeadj,
         ROW_NUMBER() OVER (
           PARTITION BY a.ticker, DATE_TRUNC('week', a.date::DATE)
           ORDER BY a.date::DATE DESC
         ) as rn
  FROM sep a
  WHERE a.date::DATE >= '{year}-01-01'
    AND a.date::DATE < '{year+1}-01-01'
)
SELECT ticker, date, close, closeadj
FROM week_ends
WHERE rn = 1
ORDER BY ticker, date
```

**Always query year-by-year** (not all years at once) to avoid timeouts.

### Weekly Returns and Momentum

**After fetching end-of-week prices:**
```python
# CRITICAL: Always group by ticker
df['return'] = df.groupby('ticker')['closeadj'].pct_change().round(4)
df['momentum'] = (
    df.groupby('ticker')['closeadj'].shift(5) /
    df.groupby('ticker')['closeadj'].shift(53) - 1
).round(4)
```

**Returns and momentum:**
- Expressed as DECIMALS (0.02 = 2% return)
- Rounded to 4 decimal places
- First week has NaN return
- First 53 weeks have NaN momentum (48-week return from 53 weeks ago to 5 weeks ago)

---

## IMPORTANT NOTES

1. **Week labels are ISO week format**: '2025-W01', '2025-W02', etc.
2. **End-of-week = last trading day in ISO week**: Usually Friday, respects holidays
3. **Query year-by-year**: Avoid API timeouts
4. **Growth rates BEFORE merging**: Calculate from fundamental data before merge
5. **Forward filling**: Fundamental data propagates until next filing
6. **All DAILY/SF1 variables must be shifted**: By 1 week after fetching

For complete database documentation:
- https://portal-guide.rice-business.org

