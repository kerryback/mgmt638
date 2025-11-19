"""
Fetch all monthly returns data from Rice Data Portal.
Gets all end-of-month prices from SEP table starting Jan 2010.
Returns: ticker, month, close (end of prior month), return (current month)
"""

import pandas as pd
import requests
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables
load_dotenv()
ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')

if not ACCESS_TOKEN:
    raise ValueError(
        "RICE_ACCESS_TOKEN not found in .env file. "
        "Please create a .env file with your access token from https://data-portal.rice-business.org"
    )

API_URL = "https://data-portal.rice-business.org/api/query"

# Fetch data year by year to avoid timeouts
start_year = 2010
current_year = datetime.now().year

all_data = []

for year in range(start_year, current_year + 1):
    print(f"Fetching data for {year}...")

    # SQL query to get end-of-month prices for ALL tickers
    sql = f"""
    WITH month_ends AS (
      SELECT a.ticker, a.date::DATE as date, a.close, a.closeadj,
             ROW_NUMBER() OVER (
               PARTITION BY a.ticker, DATE_TRUNC('month', a.date::DATE)
               ORDER BY a.date::DATE DESC
             ) as rn
      FROM sep a
      WHERE a.date::DATE >= '{year}-01-01'
        AND a.date::DATE < '{year + 1}-01-01'
    )
    SELECT ticker, date, close, closeadj
    FROM month_ends
    WHERE rn = 1
    ORDER BY ticker, date
    """

    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "Content-Type": "application/json"
            },
            json={"query": sql},
            timeout=180
        )

        if response.status_code != 200:
            print(f"  Error: API request failed with status {response.status_code}")
            continue

        data = response.json()

        if 'error' in data:
            print(f"  Error: {data['error']}")
            continue

        if 'data' in data and 'columns' in data and len(data['data']) > 0:
            df_year = pd.DataFrame(data['data'], columns=data['columns'])
            all_data.append(df_year)
            print(f"  Fetched {len(df_year):,} rows")
        else:
            print(f"  No data returned")

    except Exception as e:
        print(f"  Exception: {e}")
        continue

# Combine all years
print("\nCombining all years...")
df_all = pd.concat(all_data, ignore_index=True)
print(f"Total rows: {len(df_all):,}")

# Convert date from Unix timestamp to datetime
df_all['date'] = pd.to_datetime(df_all['date'], unit='s')

# Sort by ticker and date
df_all = df_all.sort_values(['ticker', 'date']).reset_index(drop=True)

print(f"Unique tickers: {df_all['ticker'].nunique():,}")

# Calculate monthly returns using closeadj
print("\nCalculating monthly returns...")
df_all['return'] = (
    df_all.groupby('ticker')['closeadj']
    .pct_change()
).round(4)

# For each row, the 'close' should be the close at the end of the PRIOR month
# So we need to shift close by 1 within each ticker group
df_all['close_prior_month'] = df_all.groupby('ticker')['close'].shift(1)

# Remove first row for each ticker (no prior month close) BEFORE creating month column
df_all = df_all.dropna(subset=['close_prior_month'])

# Add month column (as YYYY-MM string) AFTER dropping NaN rows
df_all['month'] = df_all['date'].dt.to_period('M').astype(str)

# Create final dataset with proper column names
# month = current month, close = end of prior month, return = current month return
df_final = df_all[['ticker', 'month', 'close_prior_month', 'return']].copy()
df_final = df_final.rename(columns={'close_prior_month': 'close'})

print(f"\nFinal dataset: {len(df_final):,} rows")
print(f"Unique tickers: {df_final['ticker'].nunique():,}")
print(f"Date range: {df_final['month'].min()} to {df_final['month'].max()}")

# Save to parquet
output_file = 'data3_returns.parquet'
df_final.to_parquet(output_file, index=False)
print(f"\nData saved to: {output_file}")

# Show sample
print("\nSample data (first 20 rows):")
print(df_final.head(20))
