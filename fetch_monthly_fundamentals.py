"""
Fetch fundamental data from SF1 table (annual data)
Variables: equity, assets, gp, roe, grossmargin, assetturnover, de (leverage)
"""
import requests
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()
ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')
API_URL = "https://data-portal.rice-business.org/api/query"

def fetch_fundamentals_for_year(year):
    """Fetch annual fundamental data for a given year"""
    sql = f"""
    SELECT ticker, reportperiod, datekey,
           equity, assets, gp,
           roe, grossmargin, assetturnover, de
    FROM sf1
    WHERE dimension = 'ARY'
      AND reportperiod::DATE >= '{year}-01-01'
      AND reportperiod::DATE < '{year+1}-01-01'
    ORDER BY ticker, datekey
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
print("Fetching annual fundamentals from SF1 table (2010-2025)...")
all_data = []

for year in range(2010, 2026):
    print(f"  Fetching {year}...")
    df_year = fetch_fundamentals_for_year(year)
    if not df_year.empty:
        all_data.append(df_year)
        print(f"    Retrieved {len(df_year)} records")

# Combine all years
df = pd.concat(all_data, ignore_index=True)
print(f"\nTotal records: {len(df)}")

# Convert dates to datetime
df['reportperiod'] = pd.to_datetime(df['reportperiod'])
df['datekey'] = pd.to_datetime(df['datekey'])

# Sort by ticker and datekey
df = df.sort_values(['ticker', 'datekey']).reset_index(drop=True)

# Calculate asset_growth BEFORE merging (critical!)
print("Calculating asset_growth (grouped by ticker)...")
df['asset_growth'] = df.groupby('ticker')['assets'].pct_change().round(4)

# Calculate gp_to_assets
print("Calculating gp_to_assets...")
df['gp_to_assets'] = (df['gp'] / df['assets']).round(4)

# Set gp_to_assets to NaN where assets <= 0
df.loc[df['assets'] <= 0, 'gp_to_assets'] = float('nan')

# Save to parquet
output_file = 'monthly_fundamentals.parquet'
df.to_parquet(output_file, index=False)
print(f"\nSaved to {output_file}")
print(f"Report period range: {df['reportperiod'].min()} to {df['reportperiod'].max()}")
print(f"Filing date range: {df['datekey'].min()} to {df['datekey'].max()}")

# Show summary
print("\nColumns:", df.columns.tolist())
print("\nSample data:")
print(df[['ticker', 'reportperiod', 'datekey', 'assets', 'asset_growth', 'gp_to_assets', 'roe', 'de']].head(10))
