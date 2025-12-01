"""
Fetch SF1 fundamental data for ALL stocks from Rice Data Portal.
Fetches year-by-year to avoid timeouts.
"""
import sys
import requests
import pandas as pd
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment
load_dotenv()
ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')
if not ACCESS_TOKEN:
    raise ValueError("RICE_ACCESS_TOKEN not found in .env file")

API_URL = "https://data-portal.rice-business.org/api/query"

start_date = "2010-01-01"
output_file = "fundamentals.parquet"

print(f"Fetching annual (10K) fundamentals for ALL stocks from {start_date}...")
print("Variables: equity, assets, roe, gp, grossmargin, assetturnover, debt")

start_year = int(start_date[:4])
current_year = datetime.now().year

all_data = []
for year in range(start_year, current_year + 1):
    print(f"\nFetching data for {year}...")

    sql = f"""
    SELECT ticker, reportperiod, datekey, equity, assets, roe, gp, grossmargin, assetturnover, debt
    FROM sf1
    WHERE dimension = 'ARY'
      AND reportperiod::DATE >= '{year}-01-01'
      AND reportperiod::DATE < '{year + 1}-01-01'
    ORDER BY ticker, datekey
    """

    response = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"},
        json={"query": sql},
        timeout=120
    )

    if response.status_code != 200:
        raise RuntimeError(f"Query failed for {year}: {response.status_code}")

    data = response.json()
    if 'error' in data:
        raise RuntimeError(f"Query failed for {year}: {data['error']}")

    if not data.get('data'):
        print(f"  No data for {year}")
        continue

    df_year = pd.DataFrame(data['data'])
    df_year = df_year[data['columns']]
    print(f"  Retrieved {len(df_year)} records")

    all_data.append(df_year)

if not all_data:
    print("No data returned")
    sys.exit(1)

# Combine all years
df = pd.concat(all_data, ignore_index=True)

# Convert date columns (already strings, not Unix timestamps)
df['reportperiod'] = pd.to_datetime(df['reportperiod'])
df['datekey'] = pd.to_datetime(df['datekey'])

# Filter to start date and sort
df = df[df['reportperiod'] >= start_date].sort_values(['ticker', 'datekey']).reset_index(drop=True)

# Save
df.to_parquet(output_file, index=False)
print(f"\nSaved {len(df)} rows to {output_file}")
print(f"Date range: {df['reportperiod'].min()} to {df['reportperiod'].max()}")
print(f"Tickers: {df['ticker'].nunique()}")
