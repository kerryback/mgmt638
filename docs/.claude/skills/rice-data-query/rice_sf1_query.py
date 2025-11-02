"""
Fetch SF1 fundamental data from Rice Data Portal.
Usage: python rice_sf1_query.py TICKER1,TICKER2,... VARIABLES DIMENSION START_DATE OUTPUT_FILE
Example: python rice_sf1_query.py AAPL,MSFT equity,revenue,netinc ARY 2020-01-01 fundamentals.xlsx
"""
import sys
import requests
import pandas as pd
from dotenv import load_dotenv
import os

def fetch_sf1_data(tickers, variables, dimension, start_date, output_file):
    """Fetch SF1 fundamental data."""
    # Load environment
    load_dotenv()
    ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')
    if not ACCESS_TOKEN:
        raise ValueError("RICE_ACCESS_TOKEN not found in .env file")
    
    API_URL = "https://data-portal.rice-business.org/api/query"
    
    # Parse inputs
    ticker_list = [t.strip() for t in tickers.split(',')]
    var_list = [v.strip() for v in variables.split(',')]
    
    print(f"Fetching SF1 data for {len(ticker_list)} tickers, dimension={dimension}...")
    
    ticker_str = "', '".join(ticker_list)
    var_str = ', '.join(var_list)
    
    sql = f"""
    SELECT ticker, reportperiod, datekey, {var_str}
    FROM sf1
    WHERE ticker IN ('{ticker_str}')
      AND dimension = '{dimension}'
      AND reportperiod::DATE >= '{start_date}'
    ORDER BY ticker, datekey
    """
    
    response = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"},
        json={"query": sql},
        timeout=30
    )
    
    if response.status_code != 200:
        raise RuntimeError(f"API request failed with status {response.status_code}")
    
    data = response.json()
    if 'error' in data:
        raise RuntimeError(f"Query failed: {data['error']}")
    
    if 'data' in data and 'columns' in data:
        df = pd.DataFrame(data['data'])
        if not df.empty:
            df = df[data['columns']]
            df['reportperiod'] = pd.to_datetime(df['reportperiod'])
            df['datekey'] = pd.to_datetime(df['datekey'])
            
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
    
    print("No data returned")
    return None

if __name__ == '__main__':
    if len(sys.argv) != 6:
        print(__doc__)
        sys.exit(1)
    fetch_sf1_data(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
