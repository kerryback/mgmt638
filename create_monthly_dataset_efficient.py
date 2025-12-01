"""
Create final monthly dataset using efficient merge_asof
"""
import pandas as pd
import numpy as np

print("Loading datasets...")
# Load monthly returns
df_returns = pd.read_parquet('monthly_returns.parquet')
print(f"Monthly returns: {len(df_returns)} rows")

# Load monthly pb
df_pb = pd.read_parquet('monthly_pb.parquet')
print(f"Monthly pb: {len(df_pb)} rows")

# Load fundamentals
df_fund = pd.read_parquet('monthly_fundamentals.parquet')
print(f"Fundamentals: {len(df_fund)} rows")

# Step 1: Convert dates first
df_returns['date'] = pd.to_datetime(df_returns['date'])
df_pb['date'] = pd.to_datetime(df_pb['date'])

# Merge returns with pb
print("\nMerging returns with pb...")
df = pd.merge(df_returns, df_pb[['ticker', 'date', 'pb']], on=['ticker', 'date'], how='left')
print(f"After pb merge: {len(df)} rows")

# Step 2: Prepare fundamentals for merge_asof
# Use datekey (filing date) as when the data becomes available
df_fund = df_fund.rename(columns={'datekey': 'filing_date'})
df_fund['filing_date'] = pd.to_datetime(df_fund['filing_date'])

# Sort both dataframes - critical for merge_asof
# Must be sorted by ticker first, then by date
df = df.sort_values(['ticker', 'date']).reset_index(drop=True)
df_fund = df_fund.sort_values(['ticker', 'filing_date']).reset_index(drop=True)

# Verify sorting
print(f"df sorted by ticker,date: {df[['ticker','date']].equals(df[['ticker','date']].sort_values(['ticker','date']))}")
print(f"df_fund sorted by ticker,filing_date: {df_fund[['ticker','filing_date']].equals(df_fund[['ticker','filing_date']].sort_values(['ticker','filing_date']))}")

# Select fundamental columns to merge
fund_cols = ['ticker', 'filing_date', 'equity', 'assets', 'gp',
             'roe', 'grossmargin', 'assetturnover', 'de',
             'asset_growth', 'gp_to_assets']
df_fund_merge = df_fund[fund_cols].copy()

# Use merge_asof to get the most recent fundamental data for each month
# direction='backward' means we take the most recent filing BEFORE each date
print("\nMerging with fundamentals using merge_asof...")
df = pd.merge_asof(
    df,
    df_fund_merge,
    left_on='date',
    right_on='filing_date',
    by='ticker',
    direction='backward'
)
print(f"After fundamentals merge: {len(df)} rows")

# Drop the filing_date column (not needed in final output)
df = df.drop(columns=['filing_date'], errors='ignore')

# Step 3: Shift SF1 variables by 1 month (grouped by ticker)
print("\nShifting SF1 variables by 1 month...")
sf1_vars = ['roe', 'grossmargin', 'assetturnover', 'de', 'asset_growth', 'gp_to_assets']
for var in sf1_vars:
    if var in df.columns:
        df[var] = df.groupby('ticker')[var].shift(1)
        print(f"  Shifted {var}")

# Step 4: Rename 'de' to 'leverage'
print("\nRenaming 'de' to 'leverage'...")
df = df.rename(columns={'de': 'leverage'})

# Step 5: Create 'lagged_return' (prior month's return)
print("Calculating lagged_return...")
df['lagged_return'] = df.groupby('ticker')['return'].shift(1)

# Step 6: Select final columns
final_columns = [
    'ticker', 'month', 'return', 'momentum', 'lagged_return', 'close',
    'marketcap', 'pb', 'asset_growth', 'roe', 'gp_to_assets',
    'grossmargin', 'assetturnover', 'leverage', 'sector', 'industry', 'size'
]

# Check which columns exist
available_cols = [col for col in final_columns if col in df.columns]
missing_cols = [col for col in final_columns if col not in df.columns]

if missing_cols:
    print(f"\nWarning: Missing columns: {missing_cols}")

df_final = df[available_cols].copy()

# Sort by ticker and month
df_final = df_final.sort_values(['ticker', 'month']).reset_index(drop=True)

# Save final dataset
output_file = 'data5_monthly.parquet'
df_final.to_parquet(output_file, index=False)
print(f"\n✓ Saved {len(df_final)} rows to {output_file}")

# Summary statistics
print(f"\n{'='*60}")
print("FINAL DATASET SUMMARY")
print(f"{'='*60}")
print(f"Columns: {df_final.columns.tolist()}")
print(f"\nMonth range: {df_final['month'].min()} to {df_final['month'].max()}")
print(f"Number of unique tickers: {df_final['ticker'].nunique()}")
print(f"Total rows: {len(df_final)}")

print("\n\nSample data (first 20 rows):")
print(df_final.head(20).to_string())

print("\n\nData types:")
print(df_final.dtypes)

print("\n\nNon-null counts:")
print(df_final.count())

print("\n\nNumeric summary:")
print(df_final.describe())
