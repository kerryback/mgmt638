"""
Step 3: Merge monthly price data with SF1 fundamentals for data4.parquet
Following the merge skill guidance for proper alignment without look-ahead bias
"""

import pandas as pd
import numpy as np

# Load the monthly price data
print("Loading data4_monthly.parquet...")
df_monthly = pd.read_parquet('data4_monthly.parquet')
print(f"  {len(df_monthly):,} rows")
print(f"  Columns: {list(df_monthly.columns)}")

# Load the SF1 fundamentals
print("\nLoading data4_sf1.parquet...")
df_sf1 = pd.read_parquet('data4_sf1.parquet')
print(f"  {len(df_sf1):,} rows")
print(f"  Columns: {list(df_sf1.columns)}")

# Step 1: Prepare SF1 data - calculate the first month AFTER filing date
print("\nPreparing SF1 data for merge...")
df_sf1['datekey'] = pd.to_datetime(df_sf1['datekey'])

# Calculate the first month that STARTS after the filing date
# MonthBegin(1) moves to the first day of the next month
df_sf1['available_month_start'] = df_sf1['datekey'] + pd.offsets.MonthBegin(1)

# Convert to STRING in format 'YYYY-MM' to match the monthly data
df_sf1['month'] = df_sf1['available_month_start'].dt.strftime('%Y-%m')

# Select fundamental columns to keep
fund_columns = ['ticker', 'month', 'asset_growth', 'roe', 'gp_to_assets', 'grossmargin', 'assetturnover', 'leverage']
df_sf1_merge = df_sf1[fund_columns].copy()

print(f"  SF1 month range: {df_sf1_merge['month'].min()} to {df_sf1_merge['month'].max()}")

# Step 2: Merge on (ticker, month)
print("\nMerging on (ticker, month)...")
df_merged = pd.merge(
    df_monthly,
    df_sf1_merge,
    on=['ticker', 'month'],
    how='left'
)
print(f"  Merged: {len(df_merged):,} rows")

# Step 3: Sort and forward fill fundamentals by ticker
print("\nForward filling fundamental data by ticker...")
df_merged = df_merged.sort_values(['ticker', 'month']).reset_index(drop=True)

fundamental_vars = ['asset_growth', 'roe', 'gp_to_assets', 'grossmargin', 'assetturnover', 'leverage']
df_merged[fundamental_vars] = df_merged.groupby('ticker')[fundamental_vars].ffill()

# Save merged data
output_file = 'data4.parquet'
df_merged.to_parquet(output_file, index=False)
print(f"\nSaved to {output_file}")
print(f"Total rows: {len(df_merged):,}")
print(f"Columns: {list(df_merged.columns)}")
print(f"\nMonth range: {df_merged['month'].min()} to {df_merged['month'].max()}")
print(f"Unique tickers: {df_merged['ticker'].nunique():,}")

# Show sample
print("\nSample data (AAPL):")
sample = df_merged[df_merged['ticker'] == 'AAPL'].dropna().head(5)
print(sample.to_string(index=False))
