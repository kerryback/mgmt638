"""
Drop November 2025 from both datasets and compare them
"""
import pandas as pd
import numpy as np

print("Loading datasets...")
df4 = pd.read_parquet('data4.parquet')
df5 = pd.read_parquet('data5_monthly.parquet')

print(f"Before filtering:")
print(f"  data4: {len(df4)} rows")
print(f"  data5_monthly: {len(df5)} rows")

# Drop November 2025 from both datasets
print("\nDropping November 2025...")
df4 = df4[df4['month'] != '2025-11']
df5 = df5[df5['month'] != '2025-11']

print(f"After dropping 2025-11:")
print(f"  data4: {len(df4)} rows")
print(f"  data5_monthly: {len(df5)} rows")

# Save filtered datasets
df4.to_parquet('data4.parquet', index=False)
df5.to_parquet('data5_monthly.parquet', index=False)
print("\nSaved filtered datasets (without 2025-11)")

print("\n" + "="*80)
print("DATASET COMPARISON: data4.parquet vs data5_monthly.parquet (without 2025-11)")
print("="*80)

# Basic structure comparison
print("\n1. BASIC STRUCTURE:")
print(f"  data4.parquet:         {len(df4):,} rows, {len(df4.columns)} columns")
print(f"  data5_monthly.parquet: {len(df5):,} rows, {len(df5.columns)} columns")
print(f"  Difference:            {len(df5) - len(df4):,} rows, {len(df5.columns) - len(df4.columns)} columns")

# Time period comparison
print("\n2. TIME PERIOD:")
print(f"  data4:         {df4['month'].min()} to {df4['month'].max()} ({df4['month'].nunique()} months)")
print(f"  data5_monthly: {df5['month'].min()} to {df5['month'].max()} ({df5['month'].nunique()} months)")

# Ticker comparison
print("\n3. TICKERS:")
print(f"  data4:         {df4['ticker'].nunique():,} unique tickers")
print(f"  data5_monthly: {df5['ticker'].nunique():,} unique tickers")

tickers4 = set(df4['ticker'].unique())
tickers5 = set(df5['ticker'].unique())
print(f"  Tickers in both: {len(tickers4 & tickers5):,}")
print(f"  Only in data4: {len(tickers4 - tickers5):,}")
print(f"  Only in data5_monthly: {len(tickers5 - tickers4):,}")

# Variable statistics for common columns
print("\n4. VARIABLE STATISTICS (for key numerical columns):")
numerical_cols = ['return', 'momentum', 'lagged_return', 'close', 'marketcap', 'pb',
                 'asset_growth', 'roe', 'leverage']

for col in numerical_cols:
    if col in df4.columns and col in df5.columns:
        print(f"\n  {col}:")
        print(f"    data4:         mean={df4[col].mean():.4f}, std={df4[col].std():.4f}, "
              f"min={df4[col].min():.4f}, max={df4[col].max():.4f}")
        print(f"    data5_monthly: mean={df5[col].mean():.4f}, std={df5[col].std():.4f}, "
              f"min={df5[col].min():.4f}, max={df5[col].max():.4f}")

# Missing data comparison
print("\n5. MISSING DATA:")
print("\n  data4.parquet:")
missing4 = df4.isnull().sum()
if missing4.sum() > 0:
    print(missing4[missing4 > 0].to_string())
else:
    print("    No missing data")

print("\n  data5_monthly.parquet:")
missing5 = df5.isnull().sum()
if missing5.sum() > 0:
    print(missing5[missing5 > 0].to_string())
else:
    print("    No missing data")

print("\n" + "="*80)
print("COMPARISON COMPLETE")
print("="*80)
