"""
Clean the monthly dataset:
1. Drop all rows with any missing data
2. Drop all rows where close < 5.00
"""
import pandas as pd

print("Loading data5_monthly.parquet...")
df = pd.read_parquet('data5_monthly.parquet')
print(f"Initial rows: {len(df):,}")
print(f"Initial tickers: {df['ticker'].nunique():,}")

# Show initial missing data summary
print("\nMissing data by column (before cleaning):")
for col in df.columns:
    missing = df[col].isna().sum()
    pct = (missing / len(df) * 100)
    if missing > 0:
        print(f"  {col:20s} - {missing:8,} missing ({pct:5.1f}%)")

# Step 1: Drop rows with any missing data
print("\n" + "="*60)
print("STEP 1: Dropping rows with any missing data...")
print("="*60)
df_clean = df.dropna()
print(f"After dropping NaN: {len(df_clean):,} rows ({len(df) - len(df_clean):,} rows dropped)")
print(f"Tickers remaining: {df_clean['ticker'].nunique():,}")

# Step 2: Drop rows where close < 5.00
print("\n" + "="*60)
print("STEP 2: Dropping rows where close < $5.00...")
print("="*60)
before_price_filter = len(df_clean)
df_clean = df_clean[df_clean['close'] >= 5.00]
print(f"After price filter: {len(df_clean):,} rows ({before_price_filter - len(df_clean):,} rows dropped)")
print(f"Tickers remaining: {df_clean['ticker'].nunique():,}")

# Final summary
print("\n" + "="*60)
print("FINAL DATASET SUMMARY")
print("="*60)
print(f"Total rows: {len(df_clean):,}")
print(f"Total tickers: {df_clean['ticker'].nunique():,}")
print(f"Date range: {df_clean['month'].min()} to {df_clean['month'].max()}")
print(f"Rows dropped: {len(df) - len(df_clean):,} ({(len(df) - len(df_clean)) / len(df) * 100:.1f}%)")

# Verify no missing data
print(f"\nMissing data check:")
missing_count = df_clean.isna().sum().sum()
print(f"  Total missing values: {missing_count}")

# Price range
print(f"\nPrice statistics:")
print(f"  Min close: ${df_clean['close'].min():.2f}")
print(f"  Max close: ${df_clean['close'].max():.2f}")
print(f"  Mean close: ${df_clean['close'].mean():.2f}")
print(f"  Median close: ${df_clean['close'].median():.2f}")

# Save
output_file = 'data5_monthly.parquet'
df_clean.to_parquet(output_file, index=False)
print(f"\n{'='*60}")
print(f"Saved cleaned dataset to {output_file}")
print(f"{'='*60}")

# Show sample
print("\nSample data (first 5 rows):")
print(df_clean.head().to_string(index=False))
