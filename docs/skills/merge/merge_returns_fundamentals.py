"""
Merge returns data with SF1 fundamental data, avoiding look-ahead bias.
Usage: python merge_returns_fundamentals.py RETURNS_FILE FUNDAMENTALS_FILE OUTPUT_FILE [--frequency monthly|weekly] [--marketcap MARKETCAP_FILE]
Example: python merge_returns_fundamentals.py returns.xlsx fundamentals.xlsx merged.xlsx --frequency monthly --marketcap marketcap.parquet
"""
import sys
import pandas as pd

def merge_returns_fundamentals(returns_file, fundamentals_file, output_file, frequency='monthly', marketcap_file=None):
    """Merge returns with fundamentals, handling date alignment properly."""
    
    print(f"Loading returns data from {returns_file}...")
    df_returns = pd.read_excel(returns_file) if returns_file.endswith('.xlsx') else \
                 pd.read_parquet(returns_file) if returns_file.endswith('.parquet') else \
                 pd.read_csv(returns_file)
    
    print(f"Loading fundamentals data from {fundamentals_file}...")
    df_sf1 = pd.read_excel(fundamentals_file) if fundamentals_file.endswith('.xlsx') else \
             pd.read_parquet(fundamentals_file) if fundamentals_file.endswith('.parquet') else \
             pd.read_csv(fundamentals_file)
    
    print(f"\nReturns: {len(df_returns)} rows")
    print(f"Fundamentals: {len(df_sf1)} rows")
    
    # STEP 1: Prepare Returns Data
    df_returns['date'] = pd.to_datetime(df_returns['date'])
    df_returns = df_returns.sort_values(['ticker', 'date']).reset_index(drop=True)
    
    # Shift close to represent prior period's closing price
    df_returns['close'] = df_returns.groupby('ticker')['close'].shift(1)
    
    # STEP 2: Prepare SF1 Fundamental Data
    df_sf1['datekey'] = pd.to_datetime(df_sf1['datekey'])
    
    if frequency == 'monthly':
        # Calculate first month AFTER filing date
        df_sf1['available_month_start'] = df_sf1['datekey'] + pd.offsets.MonthBegin(1)
        # IMPORTANT: Use strftime to create STRING, not Period objects
        df_sf1['month'] = df_sf1['available_month_start'].dt.strftime('%Y-%m')
        merge_key = 'month'
        time_col = 'month'
    elif frequency == 'weekly':
        # Calculate first Monday AFTER filing date
        days_since_monday = df_sf1['datekey'].dt.weekday
        days_until_next_monday = 7 - days_since_monday
        df_sf1['available_week_start'] = df_sf1['datekey'] + pd.to_timedelta(days_until_next_monday, unit='D')
        # IMPORTANT: Use strftime to create STRING in ISO format, not Period objects
        df_sf1['week_start'] = df_sf1['available_week_start']
        df_sf1['week_end'] = df_sf1['available_week_start'] + pd.Timedelta(days=6)
        df_sf1['week'] = df_sf1['week_start'].dt.strftime('%Y-%m-%d') + '/' + df_sf1['week_end'].dt.strftime('%Y-%m-%d')
        merge_key = 'week'
        time_col = 'week'
    else:
        raise ValueError("Frequency must be 'monthly' or 'weekly'")
    
    # STEP 3: Perform the Merge
    fund_columns = [col for col in df_sf1.columns
                    if col not in ['reportperiod', 'datekey', 'available_month_start', 'available_week_start', 'week_start', 'week_end']]
    
    df_merged = pd.merge(
        df_returns,
        df_sf1[fund_columns],
        on=['ticker', merge_key],
        how='left'
    )
    
    df_merged = df_merged.sort_values(['ticker', time_col]).reset_index(drop=True)
    
    # Forward fill fundamental data
    fundamental_vars = [col for col in fund_columns if col not in ['ticker', 'month', 'week']]
    df_merged[fundamental_vars] = df_merged.groupby('ticker')[fundamental_vars].ffill()
    
    # Drop date column
    df_merged = df_merged.drop(columns=['date'])

    # STEP 4: Merge market cap if provided
    if marketcap_file:
        print(f"\nLoading market cap data from {marketcap_file}...")
        df_mktcap = pd.read_excel(marketcap_file) if marketcap_file.endswith('.xlsx') else \
                    pd.read_parquet(marketcap_file) if marketcap_file.endswith('.parquet') else \
                    pd.read_csv(marketcap_file)

        # Ensure date column exists and convert to datetime
        if 'date' in df_mktcap.columns:
            df_mktcap['date'] = pd.to_datetime(df_mktcap['date'])
            df_mktcap = df_mktcap.sort_values(['ticker', 'date']).reset_index(drop=True)

            # Shift marketcap by 1 within each ticker (to represent prior period)
            print("Shifting marketcap to represent prior period...")
            df_mktcap['marketcap'] = df_mktcap.groupby('ticker')['marketcap'].shift(1)

            # Select columns for merge
            df_mktcap_merge = df_mktcap[['ticker', time_col, 'marketcap']].copy()

            # Merge with main data
            df_merged = pd.merge(
                df_merged,
                df_mktcap_merge,
                on=['ticker', time_col],
                how='left'
            )
            print(f"Market cap merged (shifted to represent prior period)")
        else:
            print("Warning: Market cap file missing 'date' column. Skipping shift.")
            df_mktcap_merge = df_mktcap[['ticker', time_col, 'marketcap']].copy()
            df_merged = pd.merge(
                df_merged,
                df_mktcap_merge,
                on=['ticker', time_col],
                how='left'
            )
            print(f"Market cap merged (not shifted - no date column)")

    # Save
    if output_file.endswith('.parquet'):
        df_merged.to_parquet(output_file, index=False)
    elif output_file.endswith('.xlsx'):
        df_merged.to_excel(output_file, index=False)
    elif output_file.endswith('.csv'):
        df_merged.to_csv(output_file, index=False)
    else:
        raise ValueError("Output file must end with .parquet, .xlsx, or .csv")
    
    print(f"\nMerged data saved to {output_file}")
    print(f"Total rows: {len(df_merged)}")
    print(f"Columns: {list(df_merged.columns)}")
    return df_merged

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    frequency = 'monthly'
    marketcap_file = None

    # Parse arguments
    i = 4
    while i < len(sys.argv):
        if sys.argv[i] == '--frequency' and i + 1 < len(sys.argv):
            frequency = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--marketcap' and i + 1 < len(sys.argv):
            marketcap_file = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    merge_returns_fundamentals(sys.argv[1], sys.argv[2], sys.argv[3], frequency, marketcap_file)
