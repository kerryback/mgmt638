"""
Merge returns data with SF1 fundamental data, avoiding look-ahead bias.
Usage: python merge_returns_fundamentals.py RETURNS_FILE FUNDAMENTALS_FILE OUTPUT_FILE [--frequency monthly|weekly]
Example: python merge_returns_fundamentals.py returns.xlsx fundamentals.xlsx merged.xlsx --frequency monthly
"""
import sys
import pandas as pd

def merge_returns_fundamentals(returns_file, fundamentals_file, output_file, frequency='monthly'):
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
        df_sf1['month'] = df_sf1['available_month_start'].dt.to_period('M').astype(str)
        merge_key = 'month'
        time_col = 'month'
    elif frequency == 'weekly':
        # Calculate first Monday AFTER filing date
        days_since_monday = df_sf1['datekey'].dt.weekday
        days_until_next_monday = 7 - days_since_monday
        df_sf1['available_week_start'] = df_sf1['datekey'] + pd.to_timedelta(days_until_next_monday, unit='D')
        df_sf1['week'] = df_sf1['available_week_start'].dt.to_period('W').astype(str)
        merge_key = 'week'
        time_col = 'week'
    else:
        raise ValueError("Frequency must be 'monthly' or 'weekly'")
    
    # STEP 3: Perform the Merge
    fund_columns = [col for col in df_sf1.columns 
                    if col not in ['reportperiod', 'datekey', 'available_month_start', 'available_week_start']]
    
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
    if len(sys.argv) == 6 and sys.argv[4] == '--frequency':
        frequency = sys.argv[5]
    
    merge_returns_fundamentals(sys.argv[1], sys.argv[2], sys.argv[3], frequency)
