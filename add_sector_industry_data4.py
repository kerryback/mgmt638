"""
Step 4: Get sector/industry from tickers table and merge into data4.parquet
"""

import requests
import pandas as pd
from dotenv import load_dotenv
import os

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

# Step 1: Fetch ticker, sector, industry from tickers table
print("Fetching sector/industry from tickers table...")
sql = "SELECT ticker, sector, industry FROM tickers"
df_tickers = execute_query(sql)
print(f"Retrieved {len(df_tickers):,} ticker records")

# Step 2: Load data4.parquet
print("\nLoading data4.parquet...")
df = pd.read_parquet('data4.parquet')
print(f"  {len(df):,} rows")
print(f"  Columns: {list(df.columns)}")

# Step 3: Merge sector/industry by ticker
print("\nMerging sector/industry by ticker...")
df_merged = pd.merge(
    df,
    df_tickers,
    on='ticker',
    how='left'
)
print(f"  Merged: {len(df_merged):,} rows")

# Check for missing sector/industry
missing_sector = df_merged['sector'].isna().sum()
missing_industry = df_merged['industry'].isna().sum()
print(f"  Missing sector: {missing_sector:,} rows")
print(f"  Missing industry: {missing_industry:,} rows")

# Save to data4.parquet
output_file = 'data4.parquet'
df_merged.to_parquet(output_file, index=False)
print(f"\nSaved to {output_file}")
print(f"Total rows: {len(df_merged):,}")
print(f"Columns: {list(df_merged.columns)}")

# Show sector distribution
print("\nSector distribution:")
sector_counts = df_merged['sector'].value_counts()
for sector, count in sector_counts.items():
    print(f"  {sector}: {count:,}")

# Show sample
print("\nSample data (AAPL):")
sample = df_merged[df_merged['ticker'] == 'AAPL'].dropna().head(3)
print(sample.to_string(index=False))
