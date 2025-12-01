"""
Create comprehensive monthly dataset with returns, fundamentals, and derived variables
Uses Rice Data Portal API to fetch data from SEP, DAILY, SF1, and TICKERS tables
"""

import requests
import pandas as pd
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Get access token from environment
ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')

if not ACCESS_TOKEN:
    raise ValueError(
        "RICE_ACCESS_TOKEN not found in .env file. "
        "Please create a .env file with your access token from https://data-portal.rice-business.org:\n"
        "RICE_ACCESS_TOKEN=your_access_token_here"
    )

# Rice Data Portal API endpoint
API_URL = "https://data-portal.rice-business.org/api/query"

def execute_query(sql, description=""):
    """Execute SQL query and return DataFrame"""
    print(f"\n{description}")
    print(f"Executing query...")

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
        print(f"Retrieved {len(df)} rows")
        return df
    else:
        print("No data returned")
        return pd.DataFrame()

print("="*80)
print("CREATING COMPREHENSIVE MONTHLY DATASET")
print("="*80)

# Step 1: Get all tickers
print("\n" + "="*80)
print("STEP 1: Fetching all tickers")
print("="*80)

sql_tickers = """
SELECT DISTINCT ticker
FROM sep
WHERE date::DATE >= '2010-01-01'
ORDER BY ticker
"""

df_tickers = execute_query(sql_tickers, "Getting list of all tickers with data since 2010")
all_tickers = df_tickers['ticker'].tolist()
print(f"\nFound {len(all_tickers)} tickers")

# Step 2: Fetch monthly returns and momentum (year by year to avoid timeout)
print("\n" + "="*80)
print("STEP 2: Fetching monthly end-of-month prices, returns, and momentum")
print("="*80)

start_year = 2010
current_year = datetime.now().year
monthly_data_list = []

for year in range(start_year, current_year + 1):
    print(f"\nProcessing year {year}...")

    # Create ticker list string for SQL IN clause
    ticker_list = "', '".join(all_tickers)

    sql_monthly = f"""
    WITH month_ends AS (
      SELECT a.ticker, a.date::DATE as date, a.close, a.closeadj,
             ROW_NUMBER() OVER (
               PARTITION BY a.ticker, DATE_TRUNC('month', a.date::DATE)
               ORDER BY a.date::DATE DESC
             ) as rn
      FROM sep a
      WHERE a.ticker IN ('{ticker_list}')
        AND a.date::DATE >= '{year}-01-01'
        AND a.date::DATE < '{year+1}-01-01'
    )
    SELECT ticker, date, close, closeadj
    FROM month_ends
    WHERE rn = 1
    ORDER BY ticker, date
    """

    df_year = execute_query(sql_monthly, f"Fetching end-of-month prices for {year}")
    if not df_year.empty:
        monthly_data_list.append(df_year)

# Combine all years
print("\nCombining all years...")
df_monthly = pd.concat(monthly_data_list, ignore_index=True)

# Convert date column to datetime FIRST
df_monthly['date'] = pd.to_datetime(df_monthly['date'], errors='coerce')

# Remove any rows with invalid dates
initial_rows = len(df_monthly)
df_monthly = df_monthly.dropna(subset=['date'])
if len(df_monthly) < initial_rows:
    print(f"Warning: Removed {initial_rows - len(df_monthly)} rows with invalid dates")

# Sort by ticker and date
df_monthly = df_monthly.sort_values(['ticker', 'date']).reset_index(drop=True)

print(f"Total monthly observations: {len(df_monthly)}")
print(f"Date range: {df_monthly['date'].min()} to {df_monthly['date'].max()}")

# Calculate returns and momentum
print("\nCalculating monthly returns and momentum...")

# Monthly returns (by ticker) - as decimals
df_monthly['return'] = (
    df_monthly.groupby('ticker')['closeadj']
    .pct_change()
).round(4)

# Momentum: 12-month return from 13 months ago to 2 months ago (by ticker)
df_monthly['momentum'] = (
    df_monthly.groupby('ticker')['closeadj'].shift(2) /
    df_monthly.groupby('ticker')['closeadj'].shift(13) - 1
).round(4)

# Lagged return (return from previous month)
df_monthly['lagged_return'] = (
    df_monthly.groupby('ticker')['return'].shift(1)
).round(4)

# Add month column AFTER date conversion
df_monthly['month'] = df_monthly['date'].dt.to_period('M').astype(str)

# Keep only needed columns for now
df_monthly = df_monthly[['ticker', 'month', 'date', 'close', 'return', 'momentum', 'lagged_return']]

print("Monthly returns and momentum calculated")
print(f"Sample data:\n{df_monthly.head(20)}")

# Step 3: Fetch marketcap and pb from DAILY table (monthly)
print("\n" + "="*80)
print("STEP 3: Fetching marketcap and pb from DAILY table")
print("="*80)

daily_data_list = []

for year in range(start_year, current_year + 1):
    print(f"\nProcessing year {year}...")

    ticker_list = "', '".join(all_tickers)

    sql_daily = f"""
    WITH month_ends AS (
      SELECT ticker, date::DATE as date, marketcap, pb,
             ROW_NUMBER() OVER (
               PARTITION BY ticker, DATE_TRUNC('month', date::DATE)
               ORDER BY date::DATE DESC
             ) as rn
      FROM daily
      WHERE ticker IN ('{ticker_list}')
        AND date::DATE >= '{year}-01-01'
        AND date::DATE < '{year+1}-01-01'
    )
    SELECT ticker, date, marketcap, pb
    FROM month_ends
    WHERE rn = 1
    ORDER BY ticker, date
    """

    df_year = execute_query(sql_daily, f"Fetching DAILY metrics for {year}")
    if not df_year.empty:
        daily_data_list.append(df_year)

# Combine all years
print("\nCombining all years...")
df_daily = pd.concat(daily_data_list, ignore_index=True)

# Convert date column to datetime
df_daily['date'] = pd.to_datetime(df_daily['date'], errors='coerce')

# Remove any rows with invalid dates
initial_rows = len(df_daily)
df_daily = df_daily.dropna(subset=['date'])
if len(df_daily) < initial_rows:
    print(f"Warning: Removed {initial_rows - len(df_daily)} rows with invalid dates")

# Sort by ticker and date
df_daily = df_daily.sort_values(['ticker', 'date']).reset_index(drop=True)

# CRITICAL: Shift by 1 month to avoid look-ahead bias
print("\nShifting marketcap and pb by 1 month (to avoid look-ahead bias)...")
df_daily['marketcap'] = df_daily.groupby('ticker')['marketcap'].shift(1)
df_daily['pb'] = df_daily.groupby('ticker')['pb'].shift(1)

# Add month column for merging
df_daily['month'] = df_daily['date'].dt.to_period('M').astype(str)
df_daily = df_daily[['ticker', 'month', 'marketcap', 'pb']]

# Remove any duplicates (keep first occurrence)
df_daily = df_daily.drop_duplicates(subset=['ticker', 'month'], keep='first')

print(f"Total DAILY observations (after dedup): {len(df_daily)}")

# Step 4: Fetch fundamentals from SF1 table (quarterly)
print("\n" + "="*80)
print("STEP 4: Fetching fundamentals from SF1 table")
print("="*80)

ticker_list = "', '".join(all_tickers)

sql_sf1 = f"""
SELECT ticker, reportperiod, datekey,
       equity, assets, debt, gp, revenue,
       roe, grossmargin, assetturnover
FROM sf1
WHERE ticker IN ('{ticker_list}')
  AND dimension = 'ARQ'
  AND reportperiod::DATE >= '2009-01-01'
ORDER BY ticker, datekey
"""

df_sf1 = execute_query(sql_sf1, "Fetching quarterly fundamentals from SF1")

if not df_sf1.empty:
    df_sf1['reportperiod'] = pd.to_datetime(df_sf1['reportperiod'])
    df_sf1['datekey'] = pd.to_datetime(df_sf1['datekey'])

    # CRITICAL: Shift all SF1 variables by 1 period to avoid look-ahead bias
    print("\nShifting all SF1 variables by 1 period (to avoid look-ahead bias)...")
    sf1_vars = ['equity', 'assets', 'debt', 'gp', 'revenue', 'roe', 'grossmargin', 'assetturnover']
    for var in sf1_vars:
        df_sf1[var] = df_sf1.groupby('ticker')[var].shift(1)

    print(f"Total SF1 observations: {len(df_sf1)}")

# Step 5: Fetch sector and industry from TICKERS
print("\n" + "="*80)
print("STEP 5: Fetching sector and industry from TICKERS")
print("="*80)

ticker_list = "', '".join(all_tickers)

sql_tickers_info = f"""
SELECT ticker, sector, industry, scalemarketcap
FROM tickers
WHERE ticker IN ('{ticker_list}')
"""

df_tickers_info = execute_query(sql_tickers_info, "Fetching sector and industry")

print(f"Total tickers with info: {len(df_tickers_info)}")

# Step 6: Merge all datasets
print("\n" + "="*80)
print("STEP 6: Merging all datasets")
print("="*80)

# Start with monthly returns data - remove any duplicates first
print("Deduplicating monthly data...")
df_monthly = df_monthly.drop_duplicates(subset=['ticker', 'month'], keep='first')
df_final = df_monthly.copy()
print(f"Starting with monthly returns: {len(df_final)} rows")

# Merge with DAILY metrics
df_final = df_final.merge(df_daily, on=['ticker', 'month'], how='left')
print(f"After merging DAILY: {len(df_final)} rows")

# For SF1 merge, we need to merge on the most recent quarterly data
# For each monthly date, find the most recent SF1 report
print("\nMerging with SF1 fundamentals...")

# Sort both dataframes properly for merge_asof
df_final = df_final.sort_values(['ticker', 'date']).reset_index(drop=True)
df_sf1_sorted = df_sf1.sort_values(['ticker', 'reportperiod']).reset_index(drop=True)

df_final = pd.merge_asof(
    df_final,
    df_sf1_sorted[['ticker', 'reportperiod', 'equity', 'assets', 'debt', 'gp', 'revenue', 'roe', 'grossmargin', 'assetturnover']],
    left_on='date',
    right_on='reportperiod',
    by='ticker',
    direction='backward'
)

print(f"After merging SF1: {len(df_final)} rows")

# Merge with TICKERS info
df_final = df_final.merge(df_tickers_info[['ticker', 'sector', 'industry']], on='ticker', how='left')
print(f"After merging TICKERS: {len(df_final)} rows")

# Step 7: Calculate derived variables
print("\n" + "="*80)
print("STEP 7: Calculating derived variables")
print("="*80)

# Asset growth (year-over-year, by ticker)
# Use 4 quarters lag for quarterly data
print("Calculating asset_growth...")
df_final = df_final.sort_values(['ticker', 'date']).reset_index(drop=True)
df_final['assets_lag4'] = df_final.groupby('ticker')['assets'].shift(4)
df_final['asset_growth'] = ((df_final['assets'] - df_final['assets_lag4']) / df_final['assets_lag4']).round(4)

# GP to assets
print("Calculating gp_to_assets...")
df_final['gp_to_assets'] = (df_final['gp'] / df_final['assets']).round(4)

# Leverage (debt to equity)
print("Calculating leverage...")
df_final['leverage'] = (df_final['debt'] / df_final['equity']).round(4)

# Size categories based on marketcap
print("Calculating size categories...")
# Note: marketcap in DAILY table is in thousands of dollars
# Define size buckets based on marketcap in thousands
def classify_size(mc_thousands):
    if pd.isna(mc_thousands):
        return None
    mc = mc_thousands * 1000  # Convert to actual dollars
    if mc < 50_000_000:  # < $50M
        return 'Nano-Cap'
    elif mc < 300_000_000:  # $50M - $300M
        return 'Micro-Cap'
    elif mc < 2_000_000_000:  # $300M - $2B
        return 'Small-Cap'
    elif mc < 10_000_000_000:  # $2B - $10B
        return 'Mid-Cap'
    elif mc < 200_000_000_000:  # $10B - $200B
        return 'Large-Cap'
    else:  # >= $200B
        return 'Mega-Cap'

df_final['size'] = df_final['marketcap'].apply(classify_size)

print("Derived variables calculated")

# Step 8: Clean up and finalize
print("\n" + "="*80)
print("STEP 8: Finalizing dataset")
print("="*80)

# Select final columns in the correct order
final_columns = [
    'ticker', 'month', 'return', 'momentum', 'lagged_return', 'close',
    'marketcap', 'pb', 'asset_growth', 'roe', 'gp_to_assets',
    'grossmargin', 'assetturnover', 'leverage', 'sector', 'industry', 'size'
]

df_final = df_final[final_columns]

# Sort by ticker and month
df_final = df_final.sort_values(['ticker', 'month']).reset_index(drop=True)

print(f"\nFinal dataset shape: {df_final.shape}")
print(f"\nColumn summary:")
for col in final_columns:
    non_null = df_final[col].notna().sum()
    print(f"  {col}: {non_null} non-null values ({non_null/len(df_final)*100:.1f}%)")

print(f"\nFirst 20 rows:")
print(df_final.head(20))

print(f"\nLast 20 rows:")
print(df_final.tail(20))

# Save to parquet
output_file = 'monthly_dataset_complete.parquet'
df_final.to_parquet(output_file, index=False)
print(f"\n{'='*80}")
print(f"SUCCESS! Data saved to {output_file}")
print(f"Total rows: {len(df_final):,}")
print(f"Date range: {df_final['month'].min()} to {df_final['month'].max()}")
print(f"Number of tickers: {df_final['ticker'].nunique():,}")
print(f"{'='*80}")
