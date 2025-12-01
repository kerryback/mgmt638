"""
Fetch weekly end-of-week pb (price-to-book) from DAILY table.
According to weekly-analysis skill: fetch pb from DAILY, then shift by 1 week.
"""
import requests
import pandas as pd
from dotenv import load_dotenv
import os
from datetime import datetime

def fetch_weekly_pb(start_date, output_file):
    """Fetch end-of-week pb from DAILY table.

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

    print(f"Fetching weekly pb from DAILY table for all stocks from {start_date}...")

    # Fetch DAILY data year-by-year
    all_data = []
    for year in range(start_year, current_year + 1):
        print(f"\nFetching pb for {year}...")

        # Fetch end-of-week pb from DAILY
        sql_daily = f"""
        WITH week_ends AS (
          SELECT d.ticker, d.date::DATE as date, d.pb,
                 ROW_NUMBER() OVER (
                   PARTITION BY d.ticker, DATE_TRUNC('week', d.date::DATE)
                   ORDER BY d.date::DATE DESC
                 ) as rn
          FROM daily d
          WHERE d.date::DATE >= '{year}-01-01'
            AND d.date::DATE < '{year + 1}-01-01'
        )
        SELECT ticker, CAST(date AS VARCHAR) as date, pb
        FROM week_ends
        WHERE rn = 1
        ORDER BY ticker, date
        """

        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"},
            json={"query": sql_daily},
            timeout=120
        )

        if response.status_code != 200:
            raise RuntimeError(f"DAILY query failed for {year}: {response.status_code}")

        data = response.json()
        if 'error' in data:
            raise RuntimeError(f"DAILY query failed for {year}: {data['error']}")

        if not data.get('data'):
            print(f"  No data for {year}")
            continue

        df_year = pd.DataFrame(data['data'])
        df_year = df_year[data['columns']]
        print(f"  Retrieved {len(df_year)} week-end pb values")

        all_data.append(df_year)

    if not all_data:
        print("No data returned")
        return

    # Combine all years
    print("\nCombining data from all years...")
    df = pd.concat(all_data, ignore_index=True)

    # Convert date column
    df['date'] = pd.to_datetime(df['date'])

    # Filter to start date and sort
    df = df[df['date'] >= start_date].sort_values(['ticker', 'date']).reset_index(drop=True)

    # Add ISO calendar week label
    df['iso_year'] = df['date'].dt.isocalendar().year
    df['iso_week'] = df['date'].dt.isocalendar().week
    df['week'] = df['iso_year'].astype(str) + '-' + df['iso_week'].astype(str).str.zfill(2)

    # Drop helper columns and date
    df = df[['ticker', 'week', 'pb']]

    # CRITICAL: Shift pb by 1 week (by ticker) to avoid look-ahead bias
    print("Shifting pb by 1 week (by ticker) to avoid look-ahead bias...")
    df['pb'] = df.groupby('ticker')['pb'].shift(1)

    # Save
    df.to_parquet(output_file, index=False)

    print(f"\nSaved {len(df)} rows to {output_file}")
    print(f"Week range: {df['week'].min()} to {df['week'].max()}")

    # Show sample
    print("\nSample data:")
    print(df.head(20).to_string(index=False))

    return df

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: python fetch_weekly_pb.py START_DATE OUTPUT_FILE")
        print("Example: python fetch_weekly_pb.py 2010-01-01 pb.parquet")
        sys.exit(1)
    fetch_weekly_pb(sys.argv[1], sys.argv[2])
