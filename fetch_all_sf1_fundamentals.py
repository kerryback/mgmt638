"""
Fetch SF1 fundamental data for ALL stocks from Rice Data Portal.
Fetches: equity, assets, gp, debt, roe, grossmargin, assetturnover
Dimension: ARY (As Reported Annual)
"""
import requests
import pandas as pd
from dotenv import load_dotenv
import os
from datetime import datetime

def fetch_all_sf1_data(start_date, output_file):
    """Fetch SF1 fundamental data for ALL stocks."""
    # Load environment
    load_dotenv()
    ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')
    if not ACCESS_TOKEN:
        raise ValueError("RICE_ACCESS_TOKEN not found in .env file")

    API_URL = "https://data-portal.rice-business.org/api/query"

    print(f"Fetching SF1 data for ALL stocks from {start_date}...")
    print("Variables: equity, assets, gp, debt, roe, grossmargin, assetturnover")
    print("Dimension: ARY (As Reported Annual)")

    # Fetch data year-by-year to avoid timeouts
    start_year = int(start_date[:4])
    current_year = datetime.now().year

    all_data = []
    for year in range(start_year, current_year + 1):
        print(f"\nFetching SF1 data for {year}...")

        sql = f"""
        SELECT ticker, reportperiod, datekey,
               equity, assets, gp, debt,
               roe, grossmargin, assetturnover
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
            raise RuntimeError(f"API request failed for {year}: {response.status_code}")

        data = response.json()
        if 'error' in data:
            raise RuntimeError(f"Query failed for {year}: {data['error']}")

        if data.get('data'):
            df_year = pd.DataFrame(data['data'])
            df_year = df_year[data['columns']]
            all_data.append(df_year)
            print(f"  Retrieved {len(df_year)} records")
        else:
            print(f"  No data for {year}")

    if not all_data:
        print("No data returned")
        return None

    # Combine all years
    df = pd.concat(all_data, ignore_index=True)
    df['reportperiod'] = pd.to_datetime(df['reportperiod'])
    df['datekey'] = pd.to_datetime(df['datekey'])

    # Sort
    df = df.sort_values(['ticker', 'datekey']).reset_index(drop=True)

    # Save
    if output_file.endswith('.parquet'):
        df.to_parquet(output_file, index=False)
    elif output_file.endswith('.xlsx'):
        df.to_excel(output_file, index=False)
    elif output_file.endswith('.csv'):
        df.to_csv(output_file, index=False)
    else:
        raise ValueError("Output file must end with .parquet, .xlsx, or .csv")

    print(f"\nSaved {len(df)} rows to {output_file}")
    print(f"Report period range: {df['reportperiod'].min()} to {df['reportperiod'].max()}")
    return df

if __name__ == '__main__':
    fetch_all_sf1_data('2010-01-01', 'sf1_fundamentals_all.parquet')
