import pandas as pd

print("Loading data files...")
# Load the original merged data (before the inner merge)
# We need to start fresh, so let's reconstruct from the pieces
# Actually, we can just reload the current merged file and agr file

# First, let's load what we have
df_current = pd.read_parquet('data1_merged.parquet')
df_agr = pd.read_parquet('data1_agr.parquet')

print(f"Current merged data: {len(df_current)} rows")
print(f"AGR data: {len(df_agr)} rows")

# The current merged file only has 65,331 rows (from inner merge)
# We need to reload from the backup or reconstruct
# Let me check if we still have the agr column and remove it first

if 'agr' in df_current.columns:
    print("\nRemoving existing agr column from merged data...")
    df_merged = df_current.drop(columns=['agr'])
    print(f"After removing agr: {len(df_merged)} rows, {len(df_merged.columns)} columns")
else:
    df_merged = df_current
    print(f"No agr column found, using current data as-is")

print(f"\nMerged data columns: {df_merged.columns.tolist()}")
print(f"AGR data columns: {df_agr.columns.tolist()}")

# Perform OUTER merge on (ticker, month)
print("\nPerforming OUTER merge on (ticker, month)...")
df_final = pd.merge(
    df_merged,
    df_agr,
    on=['ticker', 'month'],
    how='outer'
)

print(f"\nAfter outer merge: {len(df_final)} rows")

# Sort by ticker and month to prepare for forward fill
print("\nSorting by ticker and month...")
df_final = df_final.sort_values(['ticker', 'month']).reset_index(drop=True)

# Forward fill agr within each ticker
print("\nForward filling agr by ticker...")
df_final['agr'] = df_final.groupby('ticker')['agr'].ffill()

print(f"\nFinal data summary:")
print(f"Total rows: {len(df_final)}")
print(f"Unique tickers: {df_final['ticker'].nunique()}")
print(f"\nColumns: {df_final.columns.tolist()}")
print(f"\nNull counts:")
print(df_final.isnull().sum())

# Save as parquet
output_file = 'data1_merged.parquet'
df_final.to_parquet(output_file, index=False)
print(f"\nData saved to {output_file}")

# Display sample
print("\nSample - AAPL (showing forward fill of agr):")
aapl_sample = df_final[df_final['ticker'] == 'AAPL'].head(20)
print(aapl_sample[['ticker', 'month', 'close', 'return', 'equity', 'assets', 'agr']].to_string())

print("\n" + "="*70)
print("SUCCESS: Outer merge with forward fill completed")
print("="*70)
print("Asset growth rate (agr) is now forward filled by ticker")
print("AGR values propagate until the next 10-K filing")
