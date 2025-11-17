import pandas as pd

print("Adding DAILY metrics to final merged dataset...")

# Load the final merged data
df_final = pd.read_parquet('final_merged_data.parquet')
print(f"Final merged data: {len(df_final)} rows")

# Load the monthly DAILY metrics
df_daily = pd.read_parquet('monthly_daily_metrics.parquet')
print(f"DAILY metrics: {len(df_daily)} rows")

# Shift pe, pb, ps, ev, evebit, evebitda to represent prior period
# (aligning with close and marketcap which are already shifted)
df_daily = df_daily.sort_values(['ticker', 'date']).reset_index(drop=True)
valuation_vars = ['pe', 'pb', 'ps', 'ev', 'evebit', 'evebitda']
for var in valuation_vars:
    df_daily[var] = df_daily.groupby('ticker')[var].shift(1)

# Keep only ticker, month, and valuation metrics
df_daily = df_daily[['ticker', 'month'] + valuation_vars]

# Merge with final dataset
df_complete = pd.merge(
    df_final,
    df_daily,
    on=['ticker', 'month'],
    how='left'
)

print(f"\nComplete dataset: {len(df_complete)} rows")
print(f"\nColumns: {df_complete.columns.tolist()}")

print(f"\nFirst few rows:")
print(df_complete.head(20))

print(f"\nSummary statistics:")
print(df_complete.describe())

# Save complete dataset
df_complete.to_parquet('complete_merged_data.parquet', index=False)
print(f"\nComplete data saved to complete_merged_data.parquet")
