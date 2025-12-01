"""
Compare data5_monthly.parquet with data4.parquet
"""
import pandas as pd
import numpy as np

print("Loading datasets...")
df4 = pd.read_parquet('data4.parquet')
df5 = pd.read_parquet('data5_monthly.parquet')

print("\n" + "="*80)
print("DATASET COMPARISON: data4.parquet vs data5_monthly.parquet")
print("="*80)

# Basic structure comparison
print("\n1. BASIC STRUCTURE:")
print(f"  data4.parquet:         {len(df4):,} rows, {len(df4.columns)} columns")
print(f"  data5_monthly.parquet: {len(df5):,} rows, {len(df5.columns)} columns")
print(f"  Difference:            {len(df5) - len(df4):,} rows, {len(df5.columns) - len(df4.columns)} columns")

# Column comparison
print("\n2. COLUMNS:")
cols4 = set(df4.columns)
cols5 = set(df5.columns)

print(f"\n  Columns in data4: {sorted(df4.columns)}")
print(f"\n  Columns in data5_monthly: {sorted(df5.columns)}")

only_in_4 = cols4 - cols5
only_in_5 = cols5 - cols4
common_cols = cols4 & cols5

if only_in_4:
    print(f"\n  Columns ONLY in data4: {sorted(only_in_4)}")
if only_in_5:
    print(f"\n  Columns ONLY in data5_monthly: {sorted(only_in_5)}")
print(f"\n  Common columns: {len(common_cols)}")

# Time period comparison
print("\n3. TIME PERIOD:")
if 'week' in df4.columns:
    print(f"  data4:         {df4['week'].min()} to {df4['week'].max()} ({df4['week'].nunique()} weeks)")
if 'month' in df5.columns:
    print(f"  data5_monthly: {df5['month'].min()} to {df5['month'].max()} ({df5['month'].nunique()} months)")

# Ticker comparison
print("\n4. TICKERS:")
print(f"  data4:         {df4['ticker'].nunique():,} unique tickers")
print(f"  data5_monthly: {df5['ticker'].nunique():,} unique tickers")

tickers4 = set(df4['ticker'].unique())
tickers5 = set(df5['ticker'].unique())
print(f"  Tickers in both: {len(tickers4 & tickers5):,}")
print(f"  Only in data4: {len(tickers4 - tickers5):,}")
print(f"  Only in data5_monthly: {len(tickers5 - tickers4):,}")

# Variable statistics for common columns
print("\n5. VARIABLE STATISTICS (for common numerical columns):")
numerical_common = [col for col in common_cols
                   if col in ['return', 'momentum', 'lagged_return', 'close', 'marketcap',
                             'pb', 'asset_growth', 'roe', 'gp_to_assets', 'grossmargin',
                             'assetturnover', 'leverage']]

for col in sorted(numerical_common):
    if col in df4.columns and col in df5.columns:
        print(f"\n  {col}:")
        print(f"    data4:         mean={df4[col].mean():.4f}, std={df4[col].std():.4f}, "
              f"min={df4[col].min():.4f}, max={df4[col].max():.4f}")
        print(f"    data5_monthly: mean={df5[col].mean():.4f}, std={df5[col].std():.4f}, "
              f"min={df5[col].min():.4f}, max={df5[col].max():.4f}")

# Categorical comparison
print("\n6. CATEGORICAL VARIABLES:")
categorical_cols = ['sector', 'industry', 'size']

for col in categorical_cols:
    if col in df4.columns and col in df5.columns:
        print(f"\n  {col}:")
        print(f"    data4 unique values:         {df4[col].nunique()}")
        print(f"    data5_monthly unique values: {df5[col].nunique()}")

# Missing data comparison
print("\n7. MISSING DATA:")
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

# Data type comparison
print("\n8. DATA TYPES:")
print("\n  data4.parquet:")
print(df4.dtypes.to_string())
print("\n  data5_monthly.parquet:")
print(df5.dtypes.to_string())

print("\n" + "="*80)
print("COMPARISON COMPLETE")
print("="*80)
