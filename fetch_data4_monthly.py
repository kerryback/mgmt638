"""
Step 1: Fetch monthly price data for data4.parquet
Gets: return, momentum, lagged return, ticker, month, close, marketcap, pb
For all stocks since Jan 1, 2010
"""

import requests
import pandas as pd
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables
load_dotenv()

ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')
if not ACCESS_TOKEN:
    raise ValueError("RICE_ACCESS_TOKEN not found in .env file")

API_URL = "https://data-portal.rice-business.org/api/query"

def execute_query(sql):
    """Execute SQL query against Rice Data Portal"""
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

# Step 1: Get list of all tickers
print("Fetching ticker list...")
ticker_sql = "SELECT ticker FROM tickers WHERE isdelisted = 'N'"
tickers_df = execute_query(ticker_sql)
all_tickers = tickers_df['ticker'].tolist()
print(f"Found {len(all_tickers)} active tickers")

# Step 2: Fetch monthly prices year by year
start_year = 2010
current_year = datetime.now().year

# Process in ticker batches to avoid query timeout
batch_size = 500
ticker_batches = [all_tickers[i:i + batch_size] for i in range(0, len(all_tickers), batch_size)]

all_monthly_data = []

print(f"\nFetching end-of-month prices from {start_year} to {current_year}...")
for batch_num, ticker_batch in enumerate(ticker_batches):
    ticker_list = "'" + "','".join(ticker_batch) + "'"
    print(f"\nBatch {batch_num + 1}/{len(ticker_batches)} ({len(ticker_batch)} tickers)")

    for year in range(start_year, current_year + 1):
        sql = f"""
        WITH month_ends AS (
            SELECT a.ticker, a.date::DATE as date, a.close, a.closeadj,
                   ROW_NUMBER() OVER (PARTITION BY a.ticker, DATE_TRUNC('month', a.date::DATE) ORDER BY a.date::DATE DESC) as rn
            FROM sep a
            WHERE a.ticker IN ({ticker_list})
              AND a.date::DATE >= '{year}-01-01'
              AND a.date::DATE < '{year + 1}-01-01'
        )
        SELECT ticker, date, close, closeadj FROM month_ends WHERE rn = 1 ORDER BY ticker, date
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

# Convert date from epoch seconds
df_prices['date'] = pd.to_datetime(df_prices['date'], unit='s')
df_prices = df_prices.sort_values(['ticker', 'date']).reset_index(drop=True)
print(f"Total price records: {len(df_prices):,}")

# Step 3: Calculate returns and momentum
print("\nCalculating returns and momentum...")
df_prices['return'] = df_prices.groupby('ticker')['closeadj'].pct_change().round(4)
df_prices['momentum'] = (
    df_prices.groupby('ticker')['closeadj'].shift(2) /
    df_prices.groupby('ticker')['closeadj'].shift(13) - 1
).round(4)

# Calculate lagged return (prior month return)
df_prices['lagged_return'] = df_prices.groupby('ticker')['return'].shift(1).round(4)

# Add month column
df_prices['month'] = df_prices['date'].dt.to_period('M').astype(str)

# Step 4: Fetch marketcap and pb from DAILY table (end-of-month)
print("\nFetching marketcap and pb from DAILY table...")
all_daily_data = []

for batch_num, ticker_batch in enumerate(ticker_batches):
    ticker_list = "'" + "','".join(ticker_batch) + "'"
    print(f"\nBatch {batch_num + 1}/{len(ticker_batches)} ({len(ticker_batch)} tickers)")

    for year in range(start_year, current_year + 1):
        sql = f"""
        WITH month_ends AS (
            SELECT ticker, date::DATE as date, marketcap, pb,
                   ROW_NUMBER() OVER (PARTITION BY ticker, DATE_TRUNC('month', date::DATE) ORDER BY date::DATE DESC) as rn
            FROM daily
            WHERE ticker IN ({ticker_list})
              AND date::DATE >= '{year}-01-01'
              AND date::DATE < '{year + 1}-01-01'
        )
        SELECT ticker, date, marketcap, pb FROM month_ends WHERE rn = 1 ORDER BY ticker, date
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

# Convert date from epoch seconds
df_daily['date'] = pd.to_datetime(df_daily['date'], unit='s')
df_daily = df_daily.sort_values(['ticker', 'date']).reset_index(drop=True)
print(f"Total daily records: {len(df_daily):,}")

# Step 5: Merge prices with daily metrics
print("\nMerging price data with daily metrics...")
df_merged = pd.merge(
    df_prices[['ticker', 'date', 'month', 'close', 'return', 'momentum', 'lagged_return']],
    df_daily[['ticker', 'date', 'marketcap', 'pb']],
    on=['ticker', 'date'],
    how='left'
)
print(f"Merged records: {len(df_merged):,}")

# Step 6: Shift close, marketcap, pb to get end-of-prior-month values
print("\nShifting to get end-of-prior-month values...")
df_merged = df_merged.sort_values(['ticker', 'date']).reset_index(drop=True)

# Create lagged versions (prior month values)
df_merged['close'] = df_merged.groupby('ticker')['close'].shift(1)
df_merged['marketcap'] = df_merged.groupby('ticker')['marketcap'].shift(1)
df_merged['pb'] = df_merged.groupby('ticker')['pb'].shift(1)

# Select final columns
df_final = df_merged[['ticker', 'month', 'return', 'momentum', 'lagged_return', 'close', 'marketcap', 'pb']]

# Save to parquet
output_file = 'data4_monthly.parquet'
df_final.to_parquet(output_file, index=False)
print(f"\nSaved to {output_file}")
print(f"Total rows: {len(df_final):,}")
print(f"Columns: {list(df_final.columns)}")
print(f"\nDate range: {df_merged['date'].min()} to {df_merged['date'].max()}")
print(f"Unique tickers: {df_final['ticker'].nunique():,}")

# Show sample
print("\nSample data (AAPL):")
sample = df_final[df_final['ticker'] == 'AAPL'].dropna().head(5)
print(sample.to_string(index=False))
