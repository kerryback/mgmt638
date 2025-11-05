---
name: merge
description: "Expert in merging financial datasets with different frequencies and alignment requirements. Use when students need to combine weekly/monthly returns with SF1 fundamentals, requiring careful date alignment to avoid look-ahead bias."
---

# Financial Data Merge Expert

You are an expert in merging financial datasets with different time frequencies and alignment requirements.

## UTILITY SCRIPT (USE THIS FIRST!)

**CRITICAL: Use the pre-written merge script instead of generating new code!**

Located in `.claude/skills/merge/merge_returns_fundamentals.py`:

```bash
python .claude/skills/merge/merge_returns_fundamentals.py RETURNS_FILE FUNDAMENTALS_FILE OUTPUT_FILE --frequency monthly [--marketcap MARKETCAP_FILE]
# Example: python .claude/skills/merge/merge_returns_fundamentals.py returns.xlsx fundamentals.xlsx merged.xlsx --frequency monthly
# With market cap: python .claude/skills/merge/merge_returns_fundamentals.py returns.parquet fundamentals.parquet merged.parquet --frequency monthly --marketcap marketcap.parquet
```

**Parameters:**
- `RETURNS_FILE`: File with returns data (from rice-data-query)
- `FUNDAMENTALS_FILE`: File with SF1 fundamental data
- `OUTPUT_FILE`: Where to save merged data (.xlsx, .parquet, or .csv)
- `--frequency`: Either `monthly` or `weekly`
- `--marketcap` (optional): File with market cap data (will be shifted and merged)

**This script automatically handles:**
- Shifting close prices to represent prior period
- Calculating first period after filing date
- Merging on proper keys
- Forward filling fundamental data
- **Shifting and merging market cap data (if provided)**
- Dropping date column

This saves tokens and ensures correct implementation!

## CRITICAL PRINCIPLES

1. **No Look-Ahead Bias**: Fundamental data filed on `datekey` becomes available in the first full period (month/week) that STARTS after the filing date
2. **Prior Period Prices**: Close prices are shifted to represent the prior period's closing price (known at the start of the current period)
3. **Merge Keys**: Always merge on `(ticker, month)` or `(ticker, week)` - never on dates
4. **Forward Fill**: After merging, forward fill fundamental data by ticker to propagate values until the next filing
5. **Clean Output**: Drop the `date` column from final merged data

## INCLUDING MARKET CAP DATA (OPTIONAL)

To include market capitalization data that's properly aligned with returns and fundamentals:

```bash
python merge_returns_fundamentals.py returns.parquet fundamentals.parquet merged.parquet \
       --frequency monthly \
       --marketcap marketcap.parquet
```

**The script automatically:**
1. Loads the market cap file (expected columns: ticker, month, date, marketcap)
2. Shifts marketcap by 1 period (grouped by ticker): `df.groupby('ticker')['marketcap'].shift(1)`
3. Merges on (ticker, month/week)
4. Result: marketcap represents PRIOR period value (aligned with close)

**Why shift marketcap?**
- Market cap file contains END-OF-PERIOD values (market cap as of month-end)
- After `shift(1)`, marketcap represents the PRIOR month's end-of-period value
- This aligns perfectly with `close` (also shifted to prior period)
- Ensures consistent timing for all price-based measures
- No look-ahead bias for ratios like book-to-market (equity/marketcap)

**Example timing (November 2010):**
- `close = 10.749` → October 2010 closing price (known at start of Nov)
- `marketcap = 276,083.8` → October 2010 market cap (known at start of Nov)
- `return = 0.0339` → November 2010 return
- `equity = 4.78e10` → From 10-K filed Oct 27, 2010 (available starting Nov)

**Final output columns with --marketcap:**
`ticker`, `month`, `close`, `return`, `momentum`, `equity`, `assets`, `gp`, `opinc`, `netinccmn`, `marketcap`

## MERGING MONTHLY RETURNS WITH SF1 FUNDAMENTALS

### Step 1: Prepare Returns Data

The monthly returns data from rice-data-query has columns: `ticker`, `month`, `date`, `close`, `return`, `momentum`

**CRITICAL: The 'month' column from rice-data-query is a STRING (e.g., '2025-01'), not a pandas Period object.**

**Shift close prices to represent prior period's price:**

```python
# Convert date to datetime if needed
df_returns['date'] = pd.to_datetime(df_returns['date'])

# Sort by ticker and date to ensure proper ordering
df_returns = df_returns.sort_values(['ticker', 'date']).reset_index(drop=True)

# Shift close by 1 within each ticker - this makes close = prior month's closing price
df_returns['close'] = df_returns.groupby('ticker')['close'].shift(1)

# The month column is already a STRING in format 'YYYY-MM' (e.g., '2025-01')
# This will be our merge key - keep it as string for merging
```

**Why shift close?**
- `close` now represents the closing price from the END of the previous month
- This price was known at the START of the current month
- Ensures no look-ahead bias when using price-based ratios

### Step 2: Prepare SF1 Fundamental Data

SF1 data has columns: `ticker`, `reportperiod`, `datekey`, and fundamental variables

**CRITICAL: The 'datekey' column from rice-data-query is a DATETIME object.**

**Calculate the first month AFTER filing date:**

```python
# Convert datekey to datetime if needed (it should already be datetime from parquet)
df_sf1['datekey'] = pd.to_datetime(df_sf1['datekey'])

# Calculate the first month that STARTS after the filing date
# MonthBegin(1) moves to the first day of the next month
df_sf1['available_month_start'] = df_sf1['datekey'] + pd.offsets.MonthBegin(1)

# Convert to STRING in format 'YYYY-MM' to match the returns data
# IMPORTANT: Use strftime, NOT .to_period().astype(str) which creates Period objects
df_sf1['month'] = df_sf1['available_month_start'].dt.strftime('%Y-%m')
```

**Examples:**
- If datekey is Jan 5, 2025: month is '2025-02' (available in February)
- If datekey is Jan 30, 2025: month is '2025-02' (available in February)
- If datekey is Jan 1, 2025: month is '2025-02' (available in February)
- If datekey is Feb 8, 2021: month is '2021-03' (available in March)
- If datekey is Feb 15, 2025: month is '2025-03' (available in March)

### Step 3: Perform the Merge

**Merge on (ticker, month) and forward fill:**

```python
# Select fundamental columns to keep (exclude date-related columns)
fund_columns = [col for col in df_sf1.columns if col not in ['reportperiod', 'datekey', 'available_month_start']]

# Merge on ticker and month
df_merged = pd.merge(
    df_returns,
    df_sf1[fund_columns],
    on=['ticker', 'month'],
    how='left'  # Keep all return observations
)

# Sort by ticker and month for forward filling
df_merged = df_merged.sort_values(['ticker', 'month']).reset_index(drop=True)

# Forward fill fundamental data within each ticker
# This propagates the most recent fundamental values until the next filing
fundamental_vars = [col for col in fund_columns if col not in ['ticker', 'month']]
df_merged[fundamental_vars] = df_merged.groupby('ticker')[fundamental_vars].ffill()

# Drop the date column - not needed in final output
df_merged = df_merged.drop(columns=['date'])
```

**Final output columns:** `ticker`, `month`, `close`, `return`, `momentum`, and all fundamental variables

### Important Notes

- **First observation per ticker**: Will have NaN for `close` (due to shift) and may have NaN for fundamentals if no filing has occurred yet
- **Close represents prior month**: Use this for ratios like book-to-market (equity/close)
- **Forward filling**: Fundamental data remains constant until the next filing
- **No date column**: Merged data uses `month` as the time identifier

## MERGING WEEKLY RETURNS WITH SF1 FUNDAMENTALS

### Step 1: Prepare Returns Data

The weekly returns data from rice-data-query has columns: `ticker`, `week`, `date`, `close`, `return`, `momentum`

**CRITICAL: The 'week' column from rice-data-query is a STRING in ISO week format.**

**Shift close prices to represent prior period's price:**

```python
# Convert date to datetime if needed
df_returns['date'] = pd.to_datetime(df_returns['date'])

# Sort by ticker and date to ensure proper ordering
df_returns = df_returns.sort_values(['ticker', 'date']).reset_index(drop=True)

# Shift close by 1 within each ticker - this makes close = prior week's closing price
df_returns['close'] = df_returns.groupby('ticker')['close'].shift(1)

# The week column is already a STRING in ISO format (e.g., '2023-01-02/2023-01-08')
# This will be our merge key - keep it as string for merging
```

### Step 2: Prepare SF1 Fundamental Data

**CRITICAL: The 'datekey' column from rice-data-query is a DATETIME object.**

**Calculate the first week AFTER filing date:**

```python
# Convert datekey to datetime if needed (it should already be datetime from parquet)
df_sf1['datekey'] = pd.to_datetime(df_sf1['datekey'])

# Calculate the first Monday that STARTS after the filing date
days_since_monday = df_sf1['datekey'].dt.weekday
days_until_next_monday = 7 - days_since_monday
df_sf1['available_week_start'] = df_sf1['datekey'] + pd.to_timedelta(days_until_next_monday, unit='D')

# Convert to STRING in ISO week format to match the returns data
# IMPORTANT: Use strftime, NOT .to_period().astype(str) which creates Period objects
# ISO week format: YYYY-MM-DD/YYYY-MM-DD (start/end of week)
df_sf1['week_start'] = df_sf1['available_week_start']
df_sf1['week_end'] = df_sf1['available_week_start'] + pd.Timedelta(days=6)
df_sf1['week'] = df_sf1['week_start'].dt.strftime('%Y-%m-%d') + '/' + df_sf1['week_end'].dt.strftime('%Y-%m-%d')
```

**Examples:**
- If datekey is Monday Jan 6, 2025: week starts Monday Jan 13, 2025
- If datekey is Friday Jan 10, 2025: week starts Monday Jan 13, 2025
- If datekey is Sunday Jan 12, 2025: week starts Monday Jan 13, 2025

### Step 3: Perform the Merge

**Merge on (ticker, week) and forward fill:**

```python
# Select fundamental columns to keep (exclude date-related columns)
fund_columns = [col for col in df_sf1.columns if col not in ['reportperiod', 'datekey', 'available_week_start']]

# Merge on ticker and week
df_merged = pd.merge(
    df_returns,
    df_sf1[fund_columns],
    on=['ticker', 'week'],
    how='left'  # Keep all return observations
)

# Sort by ticker and week for forward filling
df_merged = df_merged.sort_values(['ticker', 'week']).reset_index(drop=True)

# Forward fill fundamental data within each ticker
fundamental_vars = [col for col in fund_columns if col not in ['ticker', 'week']]
df_merged[fundamental_vars] = df_merged.groupby('ticker')[fundamental_vars].ffill()

# Drop the date column - not needed in final output
df_merged = df_merged.drop(columns=['date'])
```

**Final output columns:** `ticker`, `week`, `close`, `return`, `momentum`, and all fundamental variables

### Important Notes

- **First observation per ticker**: Will have NaN for `close` (due to shift) and may have NaN for fundamentals if no filing has occurred yet
- **Close represents prior week**: Use this for ratios like book-to-market (equity/close)
- **ISO weeks**: DuckDB uses ISO 8601 weeks (Monday = start of week)
- **Forward filling**: Fundamental data remains constant until the next filing
- **No date column**: Merged data uses `week` as the time identifier

## COMMON PATTERNS

### After Merging: Calculate Ratios

When calculating financial ratios, remember that `close` is the prior period's price:

```python
# Book-to-market ratio: equity (current) / close (prior period)
df_merged['book_to_market'] = (df_merged['equity'] / df_merged['close']).round(4)

# Set to NaN if equity <= 0 (financial distress)
df_merged.loc[df_merged['equity'] <= 0, 'book_to_market'] = float('nan')

# ROE: netinc (current) / equity (current)
df_merged['roe'] = (df_merged['netinc'] / df_merged['equity']).round(4)
df_merged.loc[df_merged['equity'] <= 0, 'roe'] = float('nan')
```

### Saving Merged Data

```python
# Save to parquet (most efficient)
df_merged.to_parquet('merged_data.parquet', index=False)

# Or save to Excel/CSV for viewing
df_merged.to_excel('merged_data.xlsx', index=False)
df_merged.to_csv('merged_data.csv', index=False)
```

## SUMMARY OF TIMING

**For a filing on January 30, 2025:**

| Period Type | Filing Date | Available In | Merge Key |
|-------------|------------|--------------|-----------|
| Monthly | Jan 30, 2025 | February 2025 | '2025-02' |
| Weekly | Jan 30, 2025 | Week starting Feb 3, 2025 | ISO week string |

**Variables available in merged data for that period:**
- `close`: Closing price from prior period (known at start)
- `return`: Return during current period
- `momentum`: Momentum as of start of current period
- Fundamentals: From most recent filing before period started
