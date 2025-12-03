"""
Merge weekly returns data with fundamental data.
Usage: python merge_weekly_fundamentals.py WEEKLY_FILE FUNDAMENTALS_FILE OUTPUT_FILE
Example: python merge_weekly_fundamentals.py weekly.parquet fundamentals.parquet merged.parquet
"""
import sys
import pandas as pd

def merge_weekly_fundamentals(weekly_file, fundamentals_file, output_file):
    """Merge weekly returns with fundamentals, handling date alignment properly."""

    print(f"Loading weekly returns data from {weekly_file}...")
    df_weekly = pd.read_excel(weekly_file) if weekly_file.endswith('.xlsx') else \
                pd.read_parquet(weekly_file) if weekly_file.endswith('.parquet') else \
                pd.read_csv(weekly_file)

    print(f"Loading fundamentals data from {fundamentals_file}...")
    df_fund = pd.read_excel(fundamentals_file) if fundamentals_file.endswith('.xlsx') else \
              pd.read_parquet(fundamentals_file) if fundamentals_file.endswith('.parquet') else \
              pd.read_csv(fundamentals_file)

    print(f"\nWeekly returns: {len(df_weekly)} rows")
    print(f"Fundamentals: {len(df_fund)} rows")

    # STEP 1: Prepare Weekly Returns Data
    df_weekly['date'] = pd.to_datetime(df_weekly['date'])
    df_weekly = df_weekly.sort_values(['ticker', 'date']).reset_index(drop=True)

    # Shift close to represent prior period's closing price
    df_weekly['close'] = df_weekly.groupby('ticker')['close'].shift(1)

    # STEP 2: Prepare Fundamental Data
    df_fund['datekey'] = pd.to_datetime(df_fund['datekey'])

    # Define the isocalendar week of the datekey
    df_fund['filing_iso_year'] = df_fund['datekey'].dt.isocalendar().year
    df_fund['filing_iso_week'] = df_fund['datekey'].dt.isocalendar().week
    df_fund['filing_week'] = df_fund['filing_iso_year'].astype(str) + '-' + df_fund['filing_iso_week'].astype(str).str.zfill(2)

    print("\nFundamental data filing weeks:")
    print(df_fund[['ticker', 'datekey', 'filing_week']].to_string(index=False))

    # Shift the data one week forward
    # Data filed in week 2025-01 becomes available in week 2025-02
    df_fund['filing_date'] = df_fund['datekey']
    df_fund['available_date'] = df_fund['filing_date'] + pd.Timedelta(days=7)

    # Calculate the week when data becomes available (one week after filing)
    df_fund['available_iso_year'] = df_fund['available_date'].dt.isocalendar().year
    df_fund['available_iso_week'] = df_fund['available_date'].dt.isocalendar().week
    df_fund['week'] = df_fund['available_iso_year'].astype(str) + '-' + df_fund['available_iso_week'].astype(str).str.zfill(2)

    print("\nFundamental data availability (shifted one week forward):")
    print(df_fund[['ticker', 'datekey', 'filing_week', 'week']].to_string(index=False))

    # STEP 3: Perform the Merge
    fund_columns = [col for col in df_fund.columns
                    if col not in ['reportperiod', 'datekey', 'filing_iso_year', 'filing_iso_week',
                                   'filing_week', 'filing_date', 'available_date', 'available_iso_year', 'available_iso_week']]

    print(f"\nMerging on (ticker, week)...")
    print(f"Fundamental columns to merge: {[c for c in fund_columns if c not in ['ticker', 'week']]}")

    df_merged = pd.merge(
        df_weekly,
        df_fund[fund_columns],
        on=['ticker', 'week'],
        how='left'
    )

    df_merged = df_merged.sort_values(['ticker', 'week']).reset_index(drop=True)

    # STEP 4: Forward fill fundamental data within each ticker
    fundamental_vars = [col for col in fund_columns if col not in ['ticker', 'week']]
    print(f"\nForward filling fundamental data by ticker...")
    df_merged[fundamental_vars] = df_merged.groupby('ticker')[fundamental_vars].ffill()

    # STEP 5: Shift all SF1 variables by 1 week (grouped by ticker) to avoid look-ahead bias
    # According to weekly-analysis skill: ALL SF1 variables must be shifted by 1 week after merging
    print(f"\nShifting SF1 variables by 1 week (grouped by ticker) to avoid look-ahead bias...")
    for var in fundamental_vars:
        df_merged[var] = df_merged.groupby('ticker')[var].shift(1)
        print(f"  Shifted {var}")

    # STEP 6: Apply data quality filters
    initial_rows = len(df_merged)

    # Filter 1: Drop rows with close < 5.00
    print(f"\nApplying data quality filters...")
    print(f"  Initial rows: {initial_rows:,}")
    df_merged = df_merged[df_merged['close'] >= 5.00]
    print(f"  After close >= $5.00 filter: {len(df_merged):,} rows ({initial_rows - len(df_merged):,} dropped)")

    # Filter 2: Drop rows with any missing data
    rows_before_dropna = len(df_merged)
    df_merged = df_merged.dropna()
    print(f"  After dropping missing data: {len(df_merged):,} rows ({rows_before_dropna - len(df_merged):,} dropped)")
    print(f"  Total rows dropped: {initial_rows - len(df_merged):,}")

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

    # Show sample
    print(f"\nSample merged data (first ticker, rows 50-65 to see fundamental data):")
    sample = df_merged[df_merged['ticker'] == df_merged['ticker'].iloc[0]].iloc[50:65]
    print(sample.to_string(index=False))

    return df_merged

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    merge_weekly_fundamentals(sys.argv[1], sys.argv[2], sys.argv[3])
