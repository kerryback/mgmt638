"""
================================================================================
CREATE DATA4.PARQUET - Complete Pipeline Script
================================================================================

PURPOSE:
    Creates a merged dataset combining monthly stock price data with annual
    fundamentals from 10-K filings, plus sector/industry classification and
    size categories based on market cap percentiles.

OUTPUT FILE: data4.parquet

OUTPUT COLUMNS:
    - ticker: Stock ticker symbol
    - month: Month in 'YYYY-MM' format
    - return: Monthly return (decimal, e.g., 0.05 = 5%)
    - momentum: 12-month momentum skipping most recent month (Jegadeesh & Titman)
    - lagged_return: Prior month's return
    - close: End-of-prior-month closing price (for calculating ratios)
    - marketcap: End-of-prior-month market cap (millions USD)
    - pb: End-of-prior-month price-to-book ratio
    - asset_growth: 1-year percent change in total assets
    - roe: Return on equity (from SF1)
    - gp_to_assets: Gross profit / Total assets
    - grossmargin: Gross margin (from SF1)
    - assetturnover: Asset turnover (from SF1)
    - leverage: Assets / Equity
    - sector: Company sector classification
    - industry: Company industry classification
    - size: Market cap category (Mega/Large/Mid/Small/Micro/Nano-Cap)

DATA SOURCES:
    - SEP table: End-of-month prices (close, closeadj)
    - DAILY table: End-of-month valuation metrics (marketcap, pb)
    - SF1 table: Annual fundamentals from 10-K filings (ARY dimension)
    - TICKERS table: Sector and industry classification

KEY METHODOLOGY:
    1. Monthly prices are filtered to end-of-month using window functions
    2. Returns and momentum calculated from adjusted close prices
    3. Close, marketcap, pb are LAGGED by 1 month (end-of-prior-month values)
    4. SF1 data merged using first full month AFTER filing date (no look-ahead bias)
    5. Fundamentals forward-filled until next filing
    6. Size categories based on percentile cutoffs within each month
    7. Penny stocks (close < $5) filtered out

FILTERS APPLIED:
    - All tickers (including delisted) to avoid look-ahead bias
    - Date range: January 2010 to present
    - Close price >= $5.00 (penny stock filter)

DEPENDENCIES:
    - pandas, numpy, requests
    - python-dotenv (for API authentication)
    - RICE_ACCESS_TOKEN in .env file

USAGE:
    python create_data4.py

MODIFICATION NOTES FOR AI:
    - To add new SF1 variables: Add to SQL query in Step 2 and fund_columns list
    - To change date range: Modify start_year variable
    - To change size percentiles: Modify NANO_CUTOFF through LARGE_CUTOFF constants
    - To change price filter: Modify MINIMUM_PRICE constant
    - To add new daily metrics: Add to SQL query in Step 1b and merge logic

================================================================================
"""

import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

# Date range
START_YEAR = 2010

# Minimum price filter (drop stocks with close < this value)
MINIMUM_PRICE = 5.00

# Size category percentile cutoffs (cumulative from bottom)
# These create the following distribution:
# - Nano-Cap: bottom 3.34%
# - Micro-Cap: 3.34% to 18.83% (15.49%)
# - Small-Cap: 18.83% to 51.46% (32.63%)
# - Mid-Cap: 51.46% to 78.6% (27.14%)
# - Large-Cap: 78.6% to 98.53% (19.93%)
# - Mega-Cap: top 1.47%
NANO_CUTOFF = 3.34
MICRO_CUTOFF = 18.83
SMALL_CUTOFF = 51.46
MID_CUTOFF = 78.60
LARGE_CUTOFF = 98.53

# API Configuration
API_URL = "https://data-portal.rice-business.org/api/query"
BATCH_SIZE = 500  # Number of tickers per API query

# ============================================================================
# SETUP
# ============================================================================

# Load environment variables
load_dotenv()

ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')
if not ACCESS_TOKEN:
    raise ValueError(
        "RICE_ACCESS_TOKEN not found in .env file. "
        "Please create a .env file with your access token from https://data-portal.rice-business.org"
    )

def execute_query(sql):
    """Execute SQL query against Rice Data Portal API.

    Args:
        sql: DuckDB SQL query string

    Returns:
        pandas DataFrame with query results

    Raises:
        RuntimeError: If API request fails or query returns error
    """
    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        },
        json={"query": sql},
        timeout=120
    )

    if response.status_code != 200:
        raise RuntimeError(f"API request failed with status {response.status_code}")

    data = response.json()

    if 'error' in data:
        raise RuntimeError(f"Query failed: {data['error']}")

    if 'data' in data and 'columns' in data:
        df = pd.DataFrame(data['data'])
        if not df.empty:
            df = df[data['columns']]
        return df
    return pd.DataFrame()


def categorize_by_percentile(group):
    """Assign size categories based on market cap percentiles within a month.

    Args:
        group: DataFrame group for a single month

    Returns:
        Series with size category labels
    """
    mcap = group['marketcap']

    # Calculate percentile cutoffs for this month
    nano_thresh = mcap.quantile(NANO_CUTOFF / 100)
    micro_thresh = mcap.quantile(MICRO_CUTOFF / 100)
    small_thresh = mcap.quantile(SMALL_CUTOFF / 100)
    mid_thresh = mcap.quantile(MID_CUTOFF / 100)
    large_thresh = mcap.quantile(LARGE_CUTOFF / 100)

    # Assign categories
    result = pd.Series(index=group.index, dtype='object')
    result[mcap.isna()] = np.nan
    result[mcap <= nano_thresh] = 'Nano-Cap'
    result[(mcap > nano_thresh) & (mcap <= micro_thresh)] = 'Micro-Cap'
    result[(mcap > micro_thresh) & (mcap <= small_thresh)] = 'Small-Cap'
    result[(mcap > small_thresh) & (mcap <= mid_thresh)] = 'Mid-Cap'
    result[(mcap > mid_thresh) & (mcap <= large_thresh)] = 'Large-Cap'
    result[mcap > large_thresh] = 'Mega-Cap'

    return result


# ============================================================================
# STEP 0: GET TICKER LIST
# ============================================================================

print("=" * 80)
print("STEP 0: Fetching ticker list")
print("=" * 80)

ticker_sql = "SELECT ticker FROM tickers"
tickers_df = execute_query(ticker_sql)
all_tickers = tickers_df['ticker'].tolist()
print(f"Found {len(all_tickers)} tickers")

# Create ticker batches for API queries
ticker_batches = [all_tickers[i:i + BATCH_SIZE] for i in range(0, len(all_tickers), BATCH_SIZE)]
current_year = datetime.now().year


# ============================================================================
# STEP 1a: FETCH MONTHLY PRICES FROM SEP TABLE
# ============================================================================

print("\n" + "=" * 80)
print("STEP 1a: Fetching end-of-month prices from SEP table")
print("=" * 80)

all_monthly_data = []

for batch_num, ticker_batch in enumerate(ticker_batches):
    ticker_list = "'" + "','".join(ticker_batch) + "'"
    print(f"\nBatch {batch_num + 1}/{len(ticker_batches)} ({len(ticker_batch)} tickers)")

    for year in range(START_YEAR, current_year + 1):
        # Use window function to get last trading day of each month
        sql = f"""
        WITH month_ends AS (
            SELECT a.ticker, a.date::DATE as date, a.close, a.closeadj,
                   ROW_NUMBER() OVER (
                       PARTITION BY a.ticker, DATE_TRUNC('month', a.date::DATE)
                       ORDER BY a.date::DATE DESC
                   ) as rn
            FROM sep a
            WHERE a.ticker IN ({ticker_list})
              AND a.date::DATE >= '{year}-01-01'
              AND a.date::DATE < '{year + 1}-01-01'
        )
        SELECT ticker, date, close, closeadj
        FROM month_ends
        WHERE rn = 1
        ORDER BY ticker, date
        """

        try:
            df_year = execute_query(sql)
            if not df_year.empty:
                all_monthly_data.append(df_year)
                print(f"  {year}: {len(df_year)} rows", end="")
        except Exception as e:
            print(f"  {year}: Error - {e}")
        print("", flush=True)

# Combine all price data
print("\nCombining price data...")
df_prices = pd.concat(all_monthly_data, ignore_index=True)

# Convert date from epoch seconds (API returns timestamps)
df_prices['date'] = pd.to_datetime(df_prices['date'], unit='s')
df_prices = df_prices.sort_values(['ticker', 'date']).reset_index(drop=True)
print(f"Total price records: {len(df_prices):,}")


# ============================================================================
# STEP 1b: CALCULATE RETURNS AND MOMENTUM
# ============================================================================

print("\n" + "=" * 80)
print("STEP 1b: Calculating returns and momentum")
print("=" * 80)

# Monthly return: percent change in adjusted close
df_prices['return'] = df_prices.groupby('ticker')['closeadj'].pct_change().round(4)

# Momentum (Jegadeesh & Titman): 12-month return from t-13 to t-2
# This skips the most recent month to avoid short-term reversal
df_prices['momentum'] = (
    df_prices.groupby('ticker')['closeadj'].shift(2) /
    df_prices.groupby('ticker')['closeadj'].shift(13) - 1
).round(4)

# Lagged return: prior month's return
df_prices['lagged_return'] = df_prices.groupby('ticker')['return'].shift(1).round(4)

# Add month column
df_prices['month'] = df_prices['date'].dt.to_period('M').astype(str)

print(f"Returns calculated for {df_prices['ticker'].nunique():,} tickers")


# ============================================================================
# STEP 1c: FETCH MARKETCAP AND PB FROM DAILY TABLE
# ============================================================================

print("\n" + "=" * 80)
print("STEP 1c: Fetching marketcap and pb from DAILY table")
print("=" * 80)

all_daily_data = []

for batch_num, ticker_batch in enumerate(ticker_batches):
    ticker_list = "'" + "','".join(ticker_batch) + "'"
    print(f"\nBatch {batch_num + 1}/{len(ticker_batches)} ({len(ticker_batch)} tickers)")

    for year in range(START_YEAR, current_year + 1):
        sql = f"""
        WITH month_ends AS (
            SELECT ticker, date::DATE as date, marketcap, pb,
                   ROW_NUMBER() OVER (
                       PARTITION BY ticker, DATE_TRUNC('month', date::DATE)
                       ORDER BY date::DATE DESC
                   ) as rn
            FROM daily
            WHERE ticker IN ({ticker_list})
              AND date::DATE >= '{year}-01-01'
              AND date::DATE < '{year + 1}-01-01'
        )
        SELECT ticker, date, marketcap, pb
        FROM month_ends
        WHERE rn = 1
        ORDER BY ticker, date
        """

        try:
            df_year = execute_query(sql)
            if not df_year.empty:
                all_daily_data.append(df_year)
                print(f"  {year}: {len(df_year)} rows", end="")
        except Exception as e:
            print(f"  {year}: Error - {e}")
        print("", flush=True)

# Combine daily data
print("\nCombining daily data...")
df_daily = pd.concat(all_daily_data, ignore_index=True)
df_daily['date'] = pd.to_datetime(df_daily['date'], unit='s')
df_daily = df_daily.sort_values(['ticker', 'date']).reset_index(drop=True)
print(f"Total daily records: {len(df_daily):,}")


# ============================================================================
# STEP 1d: MERGE AND LAG PRICE DATA
# ============================================================================

print("\n" + "=" * 80)
print("STEP 1d: Merging price data and creating lagged values")
print("=" * 80)

# Merge prices with daily metrics
df_monthly = pd.merge(
    df_prices[['ticker', 'date', 'month', 'close', 'return', 'momentum', 'lagged_return']],
    df_daily[['ticker', 'date', 'marketcap', 'pb']],
    on=['ticker', 'date'],
    how='left'
)
print(f"Merged records: {len(df_monthly):,}")

# Shift close, marketcap, pb to get END-OF-PRIOR-MONTH values
# This ensures no look-ahead bias when calculating ratios
df_monthly = df_monthly.sort_values(['ticker', 'date']).reset_index(drop=True)
df_monthly['close'] = df_monthly.groupby('ticker')['close'].shift(1)
df_monthly['marketcap'] = df_monthly.groupby('ticker')['marketcap'].shift(1)
df_monthly['pb'] = df_monthly.groupby('ticker')['pb'].shift(1)

print("Lagged close, marketcap, and pb by 1 month")


# ============================================================================
# STEP 2: FETCH SF1 FUNDAMENTALS
# ============================================================================

print("\n" + "=" * 80)
print("STEP 2: Fetching SF1 annual fundamentals (10-K filings)")
print("=" * 80)

all_sf1_data = []

for batch_num, ticker_batch in enumerate(ticker_batches):
    ticker_list = "'" + "','".join(ticker_batch) + "'"
    print(f"Batch {batch_num + 1}/{len(ticker_batches)} ({len(ticker_batch)} tickers)")

    # Query SF1 with ARY dimension (As Reported Yearly = 10-K filings)
    # Include extra year for calculating asset growth
    sql = f"""
    SELECT ticker, reportperiod, datekey,
           assets, gp, roe, grossmargin, assetturnover, liabilities, equity
    FROM sf1
    WHERE ticker IN ({ticker_list})
      AND dimension = 'ARY'
      AND datekey::DATE >= '{START_YEAR - 1}-01-01'
    ORDER BY ticker, datekey
    """

    try:
        df_batch = execute_query(sql)
        if not df_batch.empty:
            all_sf1_data.append(df_batch)
            print(f"  Retrieved {len(df_batch)} rows")
    except Exception as e:
        print(f"  Error: {e}")

# Combine SF1 data
print("\nCombining SF1 data...")
df_sf1 = pd.concat(all_sf1_data, ignore_index=True)

# Convert dates (SF1 returns dates as strings, not epoch)
df_sf1['datekey'] = pd.to_datetime(df_sf1['datekey'])
df_sf1['reportperiod'] = pd.to_datetime(df_sf1['reportperiod'])
df_sf1 = df_sf1.sort_values(['ticker', 'datekey']).reset_index(drop=True)
print(f"Total SF1 records: {len(df_sf1):,}")


# ============================================================================
# STEP 2b: CALCULATE DERIVED FUNDAMENTALS
# ============================================================================

print("\n" + "=" * 80)
print("STEP 2b: Calculating derived fundamental variables")
print("=" * 80)

# 1-year percent asset growth (by ticker)
df_sf1['asset_growth'] = (
    df_sf1.groupby('ticker')['assets'].pct_change(fill_method=None)
).round(4)

# Gross profit to assets
df_sf1['gp_to_assets'] = (df_sf1['gp'] / df_sf1['assets']).round(4)
df_sf1.loc[df_sf1['assets'] <= 0, 'gp_to_assets'] = np.nan

# Leverage (assets / equity)
df_sf1['leverage'] = (df_sf1['assets'] / df_sf1['equity']).round(4)
df_sf1.loc[df_sf1['equity'] <= 0, 'leverage'] = np.nan

# Filter to datekey >= START_YEAR
df_sf1 = df_sf1[df_sf1['datekey'] >= f'{START_YEAR}-01-01'].copy()

print(f"Calculated: asset_growth, gp_to_assets, leverage")
print(f"SF1 records after date filter: {len(df_sf1):,}")


# ============================================================================
# STEP 3: MERGE MONTHLY DATA WITH SF1 FUNDAMENTALS
# ============================================================================

print("\n" + "=" * 80)
print("STEP 3: Merging monthly data with SF1 fundamentals")
print("=" * 80)

# Calculate the first month that STARTS after the filing date
# This ensures no look-ahead bias (data not available until month after filing)
df_sf1['available_month_start'] = df_sf1['datekey'] + pd.offsets.MonthBegin(1)
df_sf1['month'] = df_sf1['available_month_start'].dt.strftime('%Y-%m')

# Select fundamental columns to merge
fund_columns = ['ticker', 'month', 'asset_growth', 'roe', 'gp_to_assets',
                'grossmargin', 'assetturnover', 'leverage']
df_sf1_merge = df_sf1[fund_columns].copy()

# Merge on (ticker, month)
df_merged = pd.merge(
    df_monthly,
    df_sf1_merge,
    on=['ticker', 'month'],
    how='left'
)
print(f"Merged records: {len(df_merged):,}")

# Forward fill fundamentals by ticker (values persist until next filing)
df_merged = df_merged.sort_values(['ticker', 'month']).reset_index(drop=True)
fundamental_vars = ['asset_growth', 'roe', 'gp_to_assets', 'grossmargin',
                    'assetturnover', 'leverage']
df_merged[fundamental_vars] = df_merged.groupby('ticker')[fundamental_vars].ffill()

print("Forward-filled fundamental data by ticker")


# ============================================================================
# STEP 4: ADD SECTOR AND INDUSTRY
# ============================================================================

print("\n" + "=" * 80)
print("STEP 4: Adding sector and industry classification")
print("=" * 80)

# Fetch sector/industry from tickers table
sql = "SELECT ticker, sector, industry FROM tickers"
df_tickers = execute_query(sql)
print(f"Retrieved {len(df_tickers):,} ticker classifications")

# Merge by ticker
df_merged = pd.merge(
    df_merged,
    df_tickers,
    on='ticker',
    how='left'
)

missing_sector = df_merged['sector'].isna().sum()
print(f"Missing sector/industry: {missing_sector:,} rows")


# ============================================================================
# STEP 5: ADD SIZE CATEGORIES
# ============================================================================

print("\n" + "=" * 80)
print("STEP 5: Adding size categories based on market cap percentiles")
print("=" * 80)

# Apply percentile-based categorization within each month
df_merged['size'] = df_merged.groupby('month').apply(
    lambda x: categorize_by_percentile(x),
    include_groups=False
).reset_index(level=0, drop=True)

# Show size distribution
size_counts = df_merged['size'].value_counts()
size_pcts = (size_counts / len(df_merged[df_merged['size'].notna()]) * 100).round(2)
print("\nSize distribution:")
for cat in ['Mega-Cap', 'Large-Cap', 'Mid-Cap', 'Small-Cap', 'Micro-Cap', 'Nano-Cap']:
    if cat in size_pcts.index:
        print(f"  {cat}: {size_pcts[cat]}%")


# ============================================================================
# STEP 6: APPLY FILTERS
# ============================================================================

print("\n" + "=" * 80)
print("STEP 6: Applying filters")
print("=" * 80)

print(f"Rows before filtering: {len(df_merged):,}")

# Drop rows with close < MINIMUM_PRICE (penny stock filter)
low_price_count = (df_merged['close'] < MINIMUM_PRICE).sum()
df_merged = df_merged[df_merged['close'] >= MINIMUM_PRICE]
print(f"Dropped {low_price_count:,} rows with close < ${MINIMUM_PRICE:.2f}")

print(f"Rows after filtering: {len(df_merged):,}")


# ============================================================================
# STEP 7: SELECT FINAL COLUMNS AND SAVE
# ============================================================================

print("\n" + "=" * 80)
print("STEP 7: Saving final dataset")
print("=" * 80)

# Select and order final columns
final_columns = [
    'ticker', 'month', 'return', 'momentum', 'lagged_return',
    'close', 'marketcap', 'pb',
    'asset_growth', 'roe', 'gp_to_assets', 'grossmargin', 'assetturnover', 'leverage',
    'sector', 'industry', 'size'
]
df_final = df_merged[final_columns].copy()

# Drop rows with any missing values
rows_before = len(df_final)
df_final = df_final.dropna()
rows_dropped = rows_before - len(df_final)
print(f"Dropped {rows_dropped:,} rows with missing values")

# Save to parquet
output_file = 'data4.parquet'
df_final.to_parquet(output_file, index=False)

print(f"\nSaved to {output_file}")
print(f"Total rows: {len(df_final):,}")
print(f"Total columns: {len(df_final.columns)}")
print(f"Unique tickers: {df_final['ticker'].nunique():,}")
print(f"Date range: {df_final['month'].min()} to {df_final['month'].max()}")

# Show sample
print("\n" + "=" * 80)
print("SAMPLE DATA (AAPL)")
print("=" * 80)
sample = df_final[df_final['ticker'] == 'AAPL'].dropna().tail(5)
print(sample.to_string(index=False))

print("\n" + "=" * 80)
print("COMPLETE")
print("=" * 80)
