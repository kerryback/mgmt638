"""
Step 2: Fetch SF1 fundamental data for data4.parquet
Gets: 1-year percent asset growth, roe, gp/assets, grossmargin, assetturnover, leverage
Using 10K's (ARY dimension) for all stocks with datekey >= Jan 1, 2010
"""

import requests
import pandas as pd
import numpy as np
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

# Step 2: Fetch SF1 data - need assets, gp, roe, grossmargin, assetturnover, liabilities, equity
# We'll calculate:
# - asset_growth: (assets - LAG(assets)) / LAG(assets)
# - gp_to_assets: gp / assets
# - leverage: liabilities / equity (or assets / equity)

print("\nFetching SF1 annual data (ARY dimension)...")

# Process in ticker batches
batch_size = 500
ticker_batches = [all_tickers[i:i + batch_size] for i in range(0, len(all_tickers), batch_size)]

all_sf1_data = []

for batch_num, ticker_batch in enumerate(ticker_batches):
    ticker_list = "'" + "','".join(ticker_batch) + "'"
    print(f"Batch {batch_num + 1}/{len(ticker_batches)} ({len(ticker_batch)} tickers)")

    # Get all needed variables from SF1 with ARY dimension
    sql = f"""
    SELECT ticker, reportperiod, datekey,
           assets, gp, roe, grossmargin, assetturnover, liabilities, equity
    FROM sf1
    WHERE ticker IN ({ticker_list})
      AND dimension = 'ARY'
      AND datekey::DATE >= '2009-01-01'
    ORDER BY ticker, datekey
    """

    try:
        df_batch = execute_query(sql)
        if not df_batch.empty:
            all_sf1_data.append(df_batch)
            print(f"  Retrieved {len(df_batch)} rows")
    except Exception as e:
        print(f"  Error: {e}")

# Combine all SF1 data
print("\nCombining SF1 data...")
df_sf1 = pd.concat(all_sf1_data, ignore_index=True)

# Convert dates (SF1 returns dates as strings)
df_sf1['datekey'] = pd.to_datetime(df_sf1['datekey'])
df_sf1['reportperiod'] = pd.to_datetime(df_sf1['reportperiod'])

# Sort by ticker and datekey
df_sf1 = df_sf1.sort_values(['ticker', 'datekey']).reset_index(drop=True)
print(f"Total SF1 records: {len(df_sf1):,}")

# Step 3: Calculate derived variables
print("\nCalculating derived variables...")

# 1-year percent asset growth (by ticker)
df_sf1['asset_growth'] = (
    df_sf1.groupby('ticker')['assets'].pct_change()
).round(4)

# Gross profit to assets
df_sf1['gp_to_assets'] = (df_sf1['gp'] / df_sf1['assets']).round(4)
df_sf1.loc[df_sf1['assets'] <= 0, 'gp_to_assets'] = np.nan

# Leverage (assets / equity)
df_sf1['leverage'] = (df_sf1['assets'] / df_sf1['equity']).round(4)
df_sf1.loc[df_sf1['equity'] <= 0, 'leverage'] = np.nan

# Filter to datekey >= 2010-01-01
df_sf1 = df_sf1[df_sf1['datekey'] >= '2010-01-01'].copy()

# Select final columns
df_final = df_sf1[['ticker', 'datekey', 'asset_growth', 'roe', 'gp_to_assets', 'grossmargin', 'assetturnover', 'leverage']].copy()

# Save to parquet
output_file = 'data4_sf1.parquet'
df_final.to_parquet(output_file, index=False)
print(f"\nSaved to {output_file}")
print(f"Total rows: {len(df_final):,}")
print(f"Columns: {list(df_final.columns)}")
print(f"\nDate range: {df_final['datekey'].min()} to {df_final['datekey'].max()}")
print(f"Unique tickers: {df_final['ticker'].nunique():,}")

# Show sample
print("\nSample data (AAPL):")
sample = df_final[df_final['ticker'] == 'AAPL'].head(5)
print(sample.to_string(index=False))
