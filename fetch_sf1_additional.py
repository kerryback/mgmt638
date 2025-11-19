import requests
import pandas as pd
import os

# Rice Data Portal API endpoint
API_URL = "https://data-portal.rice-business.org/api/query"

# Get access token from environment (set by Claude Code MCP)
ACCESS_TOKEN = os.environ.get('USER_ACCESS_TOKEN')

if not ACCESS_TOKEN:
    raise ValueError("USER_ACCESS_TOKEN not found in environment variables")

print("Fetching additional SF1 variables from Rice Data Portal...")
print("Variables: dps, payoutratio, assetturnover, assets, equity")
print("Note: equity_multiplier will be calculated from assets/equity")
print("This will take several minutes...\n")

# Get list of all tickers from data2.parquet
print("Loading tickers from data2.parquet...")
df_data2 = pd.read_parquet('data2.parquet')
all_tickers = df_data2['ticker'].unique().tolist()
print(f"Found {len(all_tickers)} tickers\n")

# Fetch SF1 data year by year to avoid timeout
all_data = []

for year in range(2005, 2026):  # Start from 2005 to calculate 5-year growth rates
    print(f"Fetching {year}...")

    ticker_list = "','".join(all_tickers)

    sql = f"""
    SELECT ticker, reportperiod, datekey,
           dps, payoutratio, assetturnover, assets, equity
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

# Calculate equity_multiplier = assets / equity
print("\nCalculating equity_multiplier...")
df_sf1['equity_multiplier'] = df_sf1['assets'] / df_sf1['equity']
df_sf1.loc[df_sf1['equity'] <= 0, 'equity_multiplier'] = float('nan')

# Calculate 5-year growth rates (grouped by ticker)
print("\nCalculating 5-year growth rates...")

# Sort by ticker and datekey
df_sf1 = df_sf1.sort_values(['ticker', 'datekey'])

growth_vars = ['dps', 'payoutratio', 'assetturnover', 'equity_multiplier']

for var in growth_vars:
    print(f"  {var}_5y_growth...")
    df_sf1[f'{var}_5y_growth'] = (
        df_sf1.groupby('ticker')[var].apply(
            lambda x: ((x - x.shift(5)) / x.shift(5)).round(4)
        ).reset_index(level=0, drop=True)
    )

# Drop assets and equity (only needed for calculation)
df_sf1 = df_sf1.drop(columns=['assets', 'equity'])

# Save the new SF1 data
print("\nSaving SF1 data with additional variables...")
df_sf1.to_parquet('sf1_additional_vars.parquet', index=False)
print(f"Saved to sf1_additional_vars.parquet ({len(df_sf1)} rows)")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\nVariables added:")
print(f"  - dps (dividends per share)")
print(f"  - payoutratio")
print(f"  - assetturnover")
print(f"  - equity_multiplier (calculated as assets/equity)")
print(f"  - dps_5y_growth")
print(f"  - payoutratio_5y_growth")
print(f"  - assetturnover_5y_growth")
print(f"  - equity_multiplier_5y_growth")

print(f"\nSample data for AAPL:")
sample = df_sf1[df_sf1['ticker'] == 'AAPL'].tail(5)
if not sample.empty:
    print(sample[['ticker', 'reportperiod', 'dps', 'payoutratio', 'assetturnover', 'equity_multiplier']].to_string())
