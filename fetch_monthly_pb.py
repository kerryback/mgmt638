"""
Fetch monthly end-of-month pb (price-to-book) from DAILY table
"""
import requests
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()
ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')
API_URL = "https://data-portal.rice-business.org/api/query"

def fetch_pb_for_year(year):
    """Fetch end-of-month pb values for a given year"""
    sql = f"""
    WITH month_ends AS (
      SELECT d.ticker, d.date::DATE as date, d.pb,
             ROW_NUMBER() OVER (
               PARTITION BY d.ticker, DATE_TRUNC('month', d.date::DATE)
               ORDER BY d.date::DATE DESC
             ) as rn
      FROM daily d
      WHERE d.date::DATE >= '{year}-01-01'
        AND d.date::DATE < '{year+1}-01-01'
    )
    SELECT ticker, CAST(date AS VARCHAR) as date, pb
    FROM month_ends
    WHERE rn = 1
    ORDER BY ticker, date
    """

    response = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"},
        json={"query": sql},
        timeout=120
    )

    if response.status_code == 200:
        data = response.json()
        if 'data' in data:
            return pd.DataFrame(data['data'])
    return pd.DataFrame()

# Fetch data year by year from 2010 to 2025
print("Fetching monthly pb from DAILY table (2010-2025)...")
all_data = []

for year in range(2010, 2026):
    print(f"  Fetching {year}...")
    df_year = fetch_pb_for_year(year)
    if not df_year.empty:
        all_data.append(df_year)
        print(f"    Retrieved {len(df_year)} records")

# Combine all years
df = pd.concat(all_data, ignore_index=True)
print(f"\nTotal records: {len(df)}")

# Convert date to datetime
df['date'] = pd.to_datetime(df['date'])

# Sort by ticker and date
df = df.sort_values(['ticker', 'date']).reset_index(drop=True)

# Shift pb by 1 month (grouped by ticker) to avoid look-ahead bias
print("Shifting pb by 1 month (grouped by ticker)...")
df['pb'] = df.groupby('ticker')['pb'].shift(1)

# Save to parquet
output_file = 'monthly_pb.parquet'
df.to_parquet(output_file, index=False)
print(f"Saved to {output_file}")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")
