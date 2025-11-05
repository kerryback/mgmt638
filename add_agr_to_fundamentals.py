import pandas as pd

print("Loading fundamentals data...")
df_fund = pd.read_parquet('data1_fundamentals.parquet')

print(f"Fundamentals: {len(df_fund):,} rows")

# Sort by ticker and datekey to ensure proper ordering
df_fund = df_fund.sort_values(['ticker', 'datekey']).reset_index(drop=True)

# Calculate asset growth rate (agr) as percent change in assets, grouped by ticker
print("Calculating asset growth rate (agr)...")
df_fund['agr'] = df_fund.groupby('ticker')['assets'].pct_change().round(4)

print(f"\nColumns: {list(df_fund.columns)}")
print(f"\nSample data (first 10 rows):")
print(df_fund[['ticker', 'datekey', 'assets', 'agr']].head(10))

# Save
filename = 'data1_fundamentals.parquet'
df_fund.to_parquet(filename, index=False)
print(f"\nData saved to {filename}")
print(f"AGR non-null count: {df_fund['agr'].notna().sum():,}")
print(f"AGR null count: {df_fund['agr'].isna().sum():,} (first observation per ticker)")
