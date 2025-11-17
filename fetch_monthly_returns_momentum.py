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

print("Fetching end-of-month prices and calculating monthly returns and momentum...")
print("This will process data year by year to avoid timeouts...")

# Get all tickers first
print("\nStep 1: Fetching all active tickers...")
ticker_sql = "SELECT ticker FROM tickers WHERE isdelisted = 'N' ORDER BY ticker"

response = requests.post(
    API_URL,
    headers={
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    },
    json={"query": ticker_sql},
    timeout=30
)

if response.status_code != 200:
    raise RuntimeError(f"API request failed with status {response.status_code}")

ticker_data = response.json()
if 'error' in ticker_data:
    raise RuntimeError(f"Query failed: {ticker_data['error']}")

if 'data' in ticker_data and len(ticker_data['data']) > 0:
    # Handle both list and dict formats from API
    if isinstance(ticker_data['data'][0], dict):
        all_tickers = [row['ticker'] for row in ticker_data['data']]
    else:
        all_tickers = [row[0] for row in ticker_data['data']]
    print(f"Found {len(all_tickers)} active tickers")
else:
    raise RuntimeError("No ticker data retrieved")

# Process year by year from 2010 to current year
start_year = 2010
current_year = datetime.now().year

all_data = []

print(f"\nStep 2: Fetching end-of-month prices from {start_year} to {current_year}...")

for year in range(start_year, current_year + 1):
    print(f"Processing year {year}...")

    # Create ticker list for SQL IN clause
    ticker_list = "', '".join(all_tickers)

    # SQL query using window function to get end-of-month prices
    sql = f"""
    WITH month_ends AS (
      SELECT a.ticker, a.date::DATE as date, a.close, a.closeadj,
             ROW_NUMBER() OVER (
               PARTITION BY a.ticker, DATE_TRUNC('month', a.date::DATE)
               ORDER BY a.date::DATE DESC
             ) as rn
      FROM sep a
      WHERE a.ticker IN ('{ticker_list}')
        AND a.date::DATE >= '{year}-01-01'
        AND a.date::DATE < '{year + 1}-01-01'
    )
    SELECT ticker, date, close, closeadj
    FROM month_ends
    WHERE rn = 1
    ORDER BY ticker, date
    """

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        },
        json={"query": sql},
        timeout=60
    )

    if response.status_code != 200:
        print(f"Warning: Failed to fetch data for year {year}")
        continue

    data = response.json()

    if 'error' in data:
        print(f"Warning: Query failed for year {year}: {data['error']}")
        continue

    if 'data' in data and 'columns' in data and len(data['data']) > 0:
        df_year = pd.DataFrame(data['data'], columns=data['columns'])
        all_data.append(df_year)
        print(f"  Retrieved {len(df_year)} rows for {year}")
    else:
        print(f"  No data for {year}")

# Combine all years
if not all_data:
    raise RuntimeError("No data retrieved for any year")

print("\nStep 3: Combining all years and calculating returns and momentum...")
df_final = pd.concat(all_data, ignore_index=True)

# Convert date column to datetime
df_final['date'] = pd.to_datetime(df_final['date'])

# Sort by ticker and date
df_final = df_final.sort_values(['ticker', 'date']).reset_index(drop=True)

# CRITICAL: Use groupby('ticker') for all calculations
# Calculate monthly returns (by ticker) - as decimals
df_final['monthly_return'] = (
    df_final.groupby('ticker')['closeadj']
    .pct_change()
).round(4)

# Calculate momentum (by ticker) - as decimals
# Momentum = return from 13 months ago to 2 months ago
df_final['momentum'] = (
    df_final.groupby('ticker')['closeadj'].shift(2) /
    df_final.groupby('ticker')['closeadj'].shift(13) - 1
).round(4)

# Add month column for easier reading
df_final['month'] = df_final['date'].dt.to_period('M').astype(str)

# Rename monthly_return to return for final output
df_final['return'] = df_final['monthly_return']

# Select final columns - keep close, DO NOT include closeadj
df_final = df_final[['ticker', 'month', 'date', 'close', 'return', 'momentum']]

print(f"\nTotal rows retrieved: {len(df_final)}")
print(f"Date range: {df_final['date'].min()} to {df_final['date'].max()}")
print(f"Number of unique tickers: {df_final['ticker'].nunique()}")
print(f"\nFirst few rows:")
print(df_final.head(20))
print(f"\nSummary statistics:")
print(df_final[['close', 'return', 'momentum']].describe())

# Save to parquet
output_file = 'monthly_returns_momentum.parquet'
df_final.to_parquet(output_file, index=False)
print(f"\nData saved to {output_file}")
