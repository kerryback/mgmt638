"""
Fetch monthly returns and momentum from Rice Data Portal.
Usage: python rice_monthly_returns.py TICKER1,TICKER2,... START_DATE OUTPUT_FILE
Example: python rice_monthly_returns.py AAPL,MSFT 2020-01-01 returns.xlsx
"""
import sys
import requests
import pandas as pd
from dotenv import load_dotenv
import os
from datetime import datetime

def fetch_monthly_returns(tickers, start_date, output_file):
    """Fetch end-of-month prices and calculate returns and momentum."""
    # Load environment
    load_dotenv()
    ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')
    if not ACCESS_TOKEN:
        raise ValueError("RICE_ACCESS_TOKEN not found in .env file")
    
    API_URL = "https://data-portal.rice-business.org/api/query"
    
    # Parse inputs
    ticker_list = [t.strip() for t in tickers.split(',')]
    start_year = int(start_date[:4])
    current_year = datetime.now().year
    
    print(f"Fetching monthly returns for {len(ticker_list)} tickers from {start_date}...")
    
    all_data = []
    for year in range(start_year, current_year + 1):
        print(f"Fetching data for {year}...")
        
        ticker_str = "', '".join(ticker_list)
        sql = f"""
        WITH month_ends AS (
          SELECT a.ticker, a.date::DATE as date, a.close, a.closeadj,
                 ROW_NUMBER() OVER (
                   PARTITION BY a.ticker, DATE_TRUNC('month', a.date::DATE)
                   ORDER BY a.date::DATE DESC
                 ) as rn
          FROM sep a
          WHERE a.ticker IN ('{ticker_str}')
            AND a.date::DATE >= '{year}-01-01'
            AND a.date::DATE < '{year + 1}-01-01'
        )
        SELECT ticker, date, close, closeadj
        FROM month_ends
        WHERE rn = 1
        ORDER BY ticker, date
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
        
        if 'data' in data and 'columns' in data and data['data']:
            df_year = pd.DataFrame(data['data'])
            df_year = df_year[data['columns']]
            all_data.append(df_year)
            print(f"  Retrieved {len(df_year)} month-end prices")
    
    if not all_data:
        print("No data returned")
        return
    
    # Combine and process
    df = pd.concat(all_data, ignore_index=True)
    df['date'] = pd.to_datetime(df['date'], unit='s', utc=True).dt.tz_localize(None)
    df = df[df['date'] >= start_date].sort_values(['ticker', 'date']).reset_index(drop=True)
    
    # Calculate returns and momentum
    df['monthly_return'] = df.groupby('ticker')['closeadj'].pct_change().round(4)
    df['momentum'] = (df.groupby('ticker')['closeadj'].shift(2) / 
                      df.groupby('ticker')['closeadj'].shift(13) - 1).round(4)
    df['month'] = df['date'].dt.to_period('M').astype(str)
    df['return'] = df['monthly_return']
    df = df[['ticker', 'month', 'date', 'close', 'return', 'momentum']]
    
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
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    return df

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    fetch_monthly_returns(sys.argv[1], sys.argv[2], sys.argv[3])
