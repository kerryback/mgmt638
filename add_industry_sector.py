import requests
import pandas as pd
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')

if not ACCESS_TOKEN:
    raise ValueError(
        "RICE_ACCESS_TOKEN not found in .env file. "
        "Please create a .env file with your access token from https://data-portal.rice-business.org:\n"
        "RICE_ACCESS_TOKEN=your_access_token_here"
    )

API_URL = "https://data-portal.rice-business.org/api/query"

print("Fetching ticker, industry, and sector from TICKERS table...")

# SQL query to get ticker, industry, and sector
sql = "SELECT ticker, industry, sector FROM tickers ORDER BY ticker"

response = requests.post(
    API_URL,
    headers={
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    },
    json={"query": sql},
    timeout=30
)

if response.status_code != 200:
    raise RuntimeError(f"API request failed with status {response.status_code}")

data = response.json()
if 'error' in data:
    raise RuntimeError(f"Query failed: {data['error']}")

# Create dataframe
if 'data' in data and 'columns' in data:
    df_tickers = pd.DataFrame(data['data'], columns=data['columns'])
    print(f"Retrieved {len(df_tickers)} tickers")
    print(f"\nFirst few rows:")
    print(df_tickers.head(20))
else:
    raise RuntimeError("No data returned")

# Load data2.parquet
print("\n\nMerging with data2.parquet...")
df_data2 = pd.read_parquet('data2.parquet')
print(f"Original data2.parquet: {len(df_data2)} rows, {df_data2['ticker'].nunique()} unique tickers")

# Inner merge
df_data2_merged = pd.merge(
    df_data2,
    df_tickers,
    on='ticker',
    how='inner'
)
print(f"After merge: {len(df_data2_merged)} rows")

# Save merged data2.parquet
df_data2_merged.to_parquet('data2.parquet', index=False)
print(f"Updated data2.parquet saved with industry and sector")

# Load data2_nov2025.xlsx
print("\n\nMerging with data2_nov2025.xlsx...")
df_nov2025 = pd.read_excel('data2_nov2025.xlsx')
print(f"Original data2_nov2025.xlsx: {len(df_nov2025)} rows")

# Inner merge
df_nov2025_merged = pd.merge(
    df_nov2025,
    df_tickers,
    on='ticker',
    how='inner'
)
print(f"After merge: {len(df_nov2025_merged)} rows")

# Save merged data2_nov2025.xlsx
df_nov2025_merged.to_excel('data2_nov2025.xlsx', index=False)
print(f"Updated data2_nov2025.xlsx saved with industry and sector")

print("\n\nSummary of data2.parquet:")
print(f"Columns: {df_data2_merged.columns.tolist()}")
print(f"\nSample rows:")
print(df_data2_merged[['ticker', 'month', 'close', 'industry', 'sector']].head(20))

print("\n\nIndustry distribution in November 2025:")
print(df_nov2025_merged['industry'].value_counts().head(20))

print("\n\nSector distribution in November 2025:")
print(df_nov2025_merged['sector'].value_counts())
