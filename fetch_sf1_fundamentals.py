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

print("Fetching SF1 fundamental data (ARY dimension)...")
print("Variables: revenue, netinc, eps, ebitda, assets, equity, debt, cashneq, ncfo, fcf, roe, roa, grossmargin, netmargin")

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
# For annual data, we'll query in batches to avoid timeout
start_year = 2010
current_year = datetime.now().year

# Split tickers into batches (500 tickers at a time)
batch_size = 500
ticker_batches = [all_tickers[i:i + batch_size] for i in range(0, len(all_tickers), batch_size)]

all_data = []

print(f"\nStep 2: Fetching SF1 fundamental data from {start_year} to {current_year}...")
print(f"Processing {len(ticker_batches)} batches of tickers...")

for batch_idx, ticker_batch in enumerate(ticker_batches):
    print(f"\nProcessing batch {batch_idx + 1}/{len(ticker_batches)} ({len(ticker_batch)} tickers)...")

    # Create ticker list for SQL IN clause
    ticker_list = "', '".join(ticker_batch)

    # SQL query to get SF1 annual data
    sql = f"""
    SELECT ticker, reportperiod, datekey,
           revenue, netinc, eps, ebitda,
           assets, equity, debt, cashneq,
           ncfo, fcf,
           roe, roa, grossmargin, netmargin,
           shareswa
    FROM sf1
    WHERE ticker IN ('{ticker_list}')
      AND dimension = 'ARY'
      AND reportperiod::DATE >= '{start_year}-01-01'
    ORDER BY ticker, datekey
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
        print(f"Warning: Failed to fetch data for batch {batch_idx + 1}")
        continue

    data = response.json()

    if 'error' in data:
        print(f"Warning: Query failed for batch {batch_idx + 1}: {data['error']}")
        continue

    if 'data' in data and 'columns' in data and len(data['data']) > 0:
        df_batch = pd.DataFrame(data['data'], columns=data['columns'])
        all_data.append(df_batch)
        print(f"  Retrieved {len(df_batch)} rows")
    else:
        print(f"  No data for batch {batch_idx + 1}")

# Combine all batches
if not all_data:
    raise RuntimeError("No data retrieved for any batch")

print("\nStep 3: Combining all batches and calculating 5-year growth rates...")
df_final = pd.concat(all_data, ignore_index=True)

# Convert date columns to datetime
df_final['reportperiod'] = pd.to_datetime(df_final['reportperiod'])
df_final['datekey'] = pd.to_datetime(df_final['datekey'])

# Sort by ticker and datekey
df_final = df_final.sort_values(['ticker', 'datekey']).reset_index(drop=True)

print(f"\nTotal rows retrieved: {len(df_final)}")
print(f"Date range: {df_final['reportperiod'].min()} to {df_final['reportperiod'].max()}")
print(f"Number of unique tickers: {df_final['ticker'].nunique()}")

# Calculate 5-year growth rates for each variable (grouped by ticker)
# For annual data, 5-year lag means lag(5)
print("\nCalculating 5-year growth rates (grouped by ticker)...")

growth_vars = ['revenue', 'netinc', 'eps', 'ebitda', 'assets', 'equity', 'debt', 'cashneq', 'ncfo', 'fcf']

for var in growth_vars:
    # Calculate 5-year growth rate
    df_final[f'{var}_5y_growth'] = (
        df_final.groupby('ticker')[var].apply(
            lambda x: ((x - x.shift(5)) / x.shift(5)).round(4)
        ).reset_index(level=0, drop=True)
    )
    print(f"  Calculated {var}_5y_growth")

# Add year column for easier reading
df_final['year'] = df_final['reportperiod'].dt.year

print(f"\nFirst few rows with growth rates:")
print(df_final[['ticker', 'year', 'revenue', 'revenue_5y_growth', 'netinc', 'netinc_5y_growth']].head(20))

# Save to parquet
output_file = 'sf1_fundamentals_with_growth.parquet'
df_final.to_parquet(output_file, index=False)
print(f"\nData saved to {output_file}")

print("\nSummary statistics for growth rates:")
growth_cols = [col for col in df_final.columns if '_5y_growth' in col]
print(df_final[growth_cols].describe())
