import pandas as pd

print("Merging monthly returns/momentum with DAILY metrics...")

# Load the two datasets
df_returns = pd.read_parquet('monthly_returns_momentum.parquet')
df_metrics = pd.read_parquet('monthly_daily_metrics.parquet')

print(f"\nReturns/momentum dataset: {len(df_returns)} rows")
print(f"DAILY metrics dataset: {len(df_metrics)} rows")

# Merge on ticker and date
df_merged = pd.merge(
    df_returns,
    df_metrics[['ticker', 'date', 'ev', 'evebit', 'evebitda', 'marketcap', 'pb', 'pe', 'ps']],
    on=['ticker', 'date'],
    how='inner'
)

print(f"\nMerged dataset: {len(df_merged)} rows")
print(f"Number of unique tickers: {df_merged['ticker'].nunique()}")

# Reorder columns
df_merged = df_merged[['ticker', 'month', 'date', 'close', 'return', 'momentum',
                       'ev', 'evebit', 'evebitda', 'marketcap', 'pb', 'pe', 'ps']]

print(f"\nFirst few rows:")
print(df_merged.head(20))

print(f"\nSummary statistics:")
print(df_merged.describe())

# Save merged dataset
output_file = 'monthly_data.parquet'
df_merged.to_parquet(output_file, index=False)
print(f"\nMerged data saved to {output_file}")
