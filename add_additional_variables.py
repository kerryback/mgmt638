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

print("Fetching additional SF1 fundamentals from Rice Data Portal...")
print("This will take several minutes...\n")

# We need to get dividends (dps), and calculate:
# - Payout ratio = dps / eps
# - Asset turnover = revenue / assets
# - Equity multiplier = assets / equity
# We already have these base variables, but let's get dps

# Get list of all tickers
print("Getting list of tickers...")
ticker_sql = "SELECT DISTINCT ticker FROM sep ORDER BY ticker"
ticker_response = requests.post(
    API_URL,
    headers={
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    },
    json={"query": ticker_sql},
    timeout=30
)

if ticker_response.status_code != 200:
    raise RuntimeError(f"API request failed with status {ticker_response.status_code}")

ticker_data = ticker_response.json()
if 'error' in ticker_data:
    raise RuntimeError(f"Query failed: {ticker_data['error']}")

if isinstance(ticker_data['data'][0], dict):
    all_tickers = [row['ticker'] for row in ticker_data['data']]
else:
    all_tickers = [row[0] for row in ticker_data['data']]

print(f"Found {len(all_tickers)} tickers\n")

# Fetch SF1 data with dividends (dps)
# We'll fetch year by year to avoid timeout
all_data = []

for year in range(2005, 2026):  # Start from 2005 to calculate 5-year growth rates
    print(f"Fetching {year}...")

    ticker_list = "','".join(all_tickers)

    sql = f"""
    SELECT ticker, reportperiod, datekey,
           revenue, assets, equity, eps, dps
    FROM sf1
    WHERE ticker IN ('{ticker_list}')
      AND dimension = 'ARY'
      AND reportperiod::DATE >= '{year}-01-01'
      AND reportperiod::DATE < '{year + 1}-01-01'
    ORDER BY ticker, datekey
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
        print(f"Failed for year {year}: status {response.status_code}")
        continue

    data = response.json()
    if 'error' in data:
        print(f"Error for year {year}: {data['error']}")
        continue

    if 'data' in data and 'columns' in data:
        df_year = pd.DataFrame(data['data'], columns=data['columns'])
        all_data.append(df_year)
        print(f"  Retrieved {len(df_year)} rows")

# Combine all years
print("\nCombining all years...")
df_sf1 = pd.concat(all_data, ignore_index=True)
print(f"Total SF1 rows: {len(df_sf1)}")

# Convert date columns
df_sf1['reportperiod'] = pd.to_datetime(df_sf1['reportperiod'])
df_sf1['datekey'] = pd.to_datetime(df_sf1['datekey'])

# Calculate ratios
print("\nCalculating ratios...")

# Payout ratio = dps / eps (only where eps > 0)
df_sf1['payout_ratio'] = df_sf1['dps'] / df_sf1['eps']
df_sf1.loc[df_sf1['eps'] <= 0, 'payout_ratio'] = float('nan')

# Asset turnover = revenue / assets
df_sf1['asset_turnover'] = df_sf1['revenue'] / df_sf1['assets']
df_sf1.loc[df_sf1['assets'] <= 0, 'asset_turnover'] = float('nan')

# Equity multiplier = assets / equity
df_sf1['equity_multiplier'] = df_sf1['assets'] / df_sf1['equity']
df_sf1.loc[df_sf1['equity'] <= 0, 'equity_multiplier'] = float('nan')

# Calculate 5-year growth rates (grouped by ticker)
print("\nCalculating 5-year growth rates...")

# Sort by ticker and datekey
df_sf1 = df_sf1.sort_values(['ticker', 'datekey'])

growth_vars = ['dps', 'payout_ratio', 'asset_turnover', 'equity_multiplier']

for var in growth_vars:
    print(f"  {var}...")
    df_sf1[f'{var}_5y_growth'] = (
        df_sf1.groupby('ticker')[var].apply(
            lambda x: ((x - x.shift(5)) / x.shift(5)).round(4)
        ).reset_index(level=0, drop=True)
    )

# Save the new SF1 data
print("\nSaving new SF1 data...")
df_sf1.to_parquet('sf1_additional_vars.parquet', index=False)
print(f"Saved to sf1_additional_vars.parquet")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\nNew variables added:")
print(f"  - dividends (dps)")
print(f"  - payout_ratio")
print(f"  - asset_turnover")
print(f"  - equity_multiplier")
print(f"  - dps_5y_growth")
print(f"  - payout_ratio_5y_growth")
print(f"  - asset_turnover_5y_growth")
print(f"  - equity_multiplier_5y_growth")

print(f"\nSample data:")
sample = df_sf1[df_sf1['ticker'] == 'AAPL'].tail(5)
print(sample[['ticker', 'reportperiod', 'dps', 'payout_ratio', 'asset_turnover', 'equity_multiplier']].to_string())
