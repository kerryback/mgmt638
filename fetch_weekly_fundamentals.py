"""
Fetch SF1 fundamental data for weekly analysis.
Fetches: assets, gp, equity, roe, grossmargin, assetturnover, de (leverage)
Then calculates: asset_growth, gp_to_assets BEFORE merging (as per skill instructions)
"""
import requests
import pandas as pd
from dotenv import load_dotenv
import os
from datetime import datetime

def fetch_sf1_fundamentals(start_date, output_file):
    """Fetch SF1 fundamental data.

    Args:
        start_date: Start date in YYYY-MM-DD format
        output_file: Output filename (.parquet)
    """
    # Load environment
    load_dotenv()
    ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')
    if not ACCESS_TOKEN:
        raise ValueError(
            "RICE_ACCESS_TOKEN not found in .env file. "
            "Please create a .env file with your access token from https://data-portal.rice-business.org:\n"
            "RICE_ACCESS_TOKEN=your_access_token_here"
        )

    API_URL = "https://data-portal.rice-business.org/api/query"

    start_year = int(start_date[:4])
    current_year = datetime.now().year

    print(f"Fetching SF1 fundamental data (ARY dimension) from {start_date}...")
    print(f"Variables: assets, gp, equity, roe, grossmargin, assetturnover, de")

    # Fetch SF1 data year-by-year
    all_data = []
    for year in range(start_year, current_year + 1):
        print(f"\nFetching fundamentals for {year}...")

        # Fetch from SF1 table - ARY dimension for annual data
        sql_sf1 = f"""
        SELECT ticker, reportperiod, datekey,
               assets, gp, equity, roe, grossmargin, assetturnover, de
        FROM sf1
        WHERE dimension = 'ARY'
          AND reportperiod::DATE >= '{year}-01-01'
          AND reportperiod::DATE < '{year + 1}-01-01'
        ORDER BY ticker, datekey
        """

        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"},
            json={"query": sql_sf1},
            timeout=120
        )

        if response.status_code != 200:
            raise RuntimeError(f"SF1 query failed for {year}: {response.status_code}")

        data = response.json()
        if 'error' in data:
            raise RuntimeError(f"SF1 query failed for {year}: {data['error']}")

        if not data.get('data'):
            print(f"  No data for {year}")
            continue

        df_year = pd.DataFrame(data['data'])
        df_year = df_year[data['columns']]
        print(f"  Retrieved {len(df_year)} fundamental records")

        all_data.append(df_year)

    if not all_data:
        print("No data returned")
        return

    # Combine all years
    print("\nCombining data from all years...")
    df = pd.concat(all_data, ignore_index=True)

    # Convert date columns
    df['reportperiod'] = pd.to_datetime(df['reportperiod'])
    df['datekey'] = pd.to_datetime(df['datekey'])

    # Filter to start date based on reportperiod
    df = df[df['reportperiod'] >= start_date].sort_values(['ticker', 'datekey']).reset_index(drop=True)

    print(f"\nTotal records: {len(df)}")
    print(f"Date range (reportperiod): {df['reportperiod'].min()} to {df['reportperiod'].max()}")
    print(f"Date range (datekey): {df['datekey'].min()} to {df['datekey'].max()}")

    # CRITICAL: Calculate growth rates BEFORE merging (as per skill instructions)
    print("\nCalculating derived variables BEFORE merging:")

    # asset_growth: percent change in assets (grouped by ticker)
    print("  Calculating asset_growth...")
    df['asset_growth'] = df.groupby('ticker')['assets'].pct_change().round(4)

    # gp_to_assets: gross profit / assets
    print("  Calculating gp_to_assets...")
    df['gp_to_assets'] = (df['gp'] / df['assets']).round(4)

    # Apply financial ratio rule: set gp_to_assets to NaN if assets <= 0
    # (Following CLAUDE.md instructions for ratios with assets in denominator)
    invalid_assets = df['assets'] <= 0
    if invalid_assets.any():
        print(f"  Setting gp_to_assets to NaN for {invalid_assets.sum()} records with assets <= 0")
        df.loc[invalid_assets, 'gp_to_assets'] = float('nan')

    # Show statistics
    print("\nVariable statistics:")
    print(df[['assets', 'asset_growth', 'gp', 'gp_to_assets', 'equity', 'roe', 'grossmargin', 'assetturnover', 'de']].describe())

    # Save
    df.to_parquet(output_file, index=False)

    print(f"\nSaved {len(df)} rows to {output_file}")

    # Show sample
    print("\nSample data:")
    print(df[['ticker', 'reportperiod', 'datekey', 'assets', 'asset_growth', 'gp_to_assets', 'roe', 'grossmargin', 'assetturnover', 'de']].head(20).to_string(index=False))

    return df

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: python fetch_weekly_fundamentals.py START_DATE OUTPUT_FILE")
        print("Example: python fetch_weekly_fundamentals.py 2010-01-01 fundamentals.parquet")
        sys.exit(1)
    fetch_sf1_fundamentals(sys.argv[1], sys.argv[2])
