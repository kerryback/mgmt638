import pandas as pd

print("Renaming and filtering data...")

# Load the complete merged data
df = pd.read_parquet('complete_merged_data.parquet')
print(f"Original data: {len(df)} rows")

# Drop rows where close < 5.00
# Note: This will also drop rows where close is NaN
df_filtered = df[df['close'] >= 5.00].copy()

print(f"After filtering (close >= 5.00): {len(df_filtered)} rows")
print(f"Rows dropped: {len(df) - len(df_filtered)}")

# Save to data2.parquet
df_filtered.to_parquet('data2.parquet', index=False)
print(f"\nFiltered data saved to data2.parquet")

print(f"\nSummary of filtered data:")
print(f"Unique tickers: {df_filtered['ticker'].nunique()}")
print(f"Date range: {df_filtered['month'].min()} to {df_filtered['month'].max()}")
print(f"\nFirst 20 rows:")
print(df_filtered.head(20))
