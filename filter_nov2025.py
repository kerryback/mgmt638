import pandas as pd

print("Filtering data2.parquet for November 2025...")

# Load data2.parquet
df = pd.read_parquet('data2.parquet')
print(f"Original data: {len(df)} rows")
print(f"Unique months: {df['month'].nunique()}")

# Filter to November 2025
df_nov2025 = df[df['month'] == '2025-11'].copy()

print(f"\nFiltered to November 2025: {len(df_nov2025)} rows")
print(f"Unique tickers: {df_nov2025['ticker'].nunique()}")

# Save to data2_nov2025.parquet
df_nov2025.to_parquet('data2_nov2025.parquet', index=False)
print(f"\nData saved to data2_nov2025.parquet")

print(f"\nFirst 20 rows:")
print(df_nov2025.head(20))

print(f"\nSummary statistics:")
print(df_nov2025[['close', 'return', 'momentum', 'marketcap', 'pe', 'pb', 'revenue', 'equity']].describe())
