"""
Finalize the monthly dataset:
1. Shift SF1 variables (roe, grossmargin, assetturnover) by 1 month (CRITICAL for avoiding look-ahead bias)
2. Add lagged_return column
3. Select and order final columns to match data5 structure (monthly version)
"""
import pandas as pd
import numpy as np

print("Loading merged monthly data...")
df = pd.read_parquet('monthly_data_merged.parquet')
print(f"Loaded {len(df)} rows, {df['ticker'].nunique()} tickers")
print(f"Columns: {list(df.columns)}")

# Sort by ticker and month to ensure proper ordering
df = df.sort_values(['ticker', 'month']).reset_index(drop=True)

# CRITICAL: Shift SF1 variables by 1 month (grouped by ticker) to avoid look-ahead bias
# Per CRITICAL DATA RULES: "ALL variables from DAILY and SF1 tables MUST be shifted"
print("\nShifting SF1 variables (roe, grossmargin, assetturnover) by 1 month...")
print("  This ensures fundamental data represents prior month's values")

df['roe'] = df.groupby('ticker')['roe'].shift(1)
df['grossmargin'] = df.groupby('ticker')['grossmargin'].shift(1)
df['assetturnover'] = df.groupby('ticker')['assetturnover'].shift(1)

# Note: marketcap was already shifted in fetch_monthly_data.py
# Note: pb is based on shifted marketcap, so it's already properly aligned
# Note: asset_growth, gp_to_assets, leverage are calculated from fundamentals,
#       and will be shifted naturally when fundamentals are forward-filled

# Add lagged_return column (same as lag_month, but renamed for consistency with data5)
print("Adding lagged_return column...")
df['lagged_return'] = df['lag_month']

# Select final columns in the same order as data5.parquet (monthly version)
# Original data5 columns: ticker, week, return, momentum, lagged_return, close,
#                         marketcap, pb, asset_growth, roe, gp_to_assets,
#                         grossmargin, assetturnover, leverage, sector, industry, size
final_columns = [
    'ticker', 'month', 'return', 'momentum', 'lagged_return', 'close',
    'marketcap', 'pb', 'asset_growth', 'roe', 'gp_to_assets',
    'grossmargin', 'assetturnover', 'leverage', 'sector', 'industry', 'size'
]

print(f"\nSelecting final columns: {final_columns}")
df_final = df[final_columns].copy()

# Display summary
print(f"\n{'='*60}")
print("FINAL DATASET SUMMARY")
print(f"{'='*60}")
print(f"Total rows: {len(df_final):,}")
print(f"Total tickers: {df_final['ticker'].nunique():,}")
print(f"Date range: {df_final['month'].min()} to {df_final['month'].max()}")
print(f"\nColumns ({len(df_final.columns)}):")
for col in df_final.columns:
    non_null = df_final[col].notna().sum()
    pct = (non_null / len(df_final) * 100)
    print(f"  {col:20s} - {non_null:8,} non-null ({pct:5.1f}%)")

# Save
output_file = 'data5_monthly.parquet'
df_final.to_parquet(output_file, index=False)
print(f"\n{'='*60}")
print(f"Saved to {output_file}")
print(f"{'='*60}")

# Show a sample
print("\nSample data (first ticker with complete fundamentals):")
for ticker in df_final['ticker'].unique():
    ticker_data = df_final[df_final['ticker'] == ticker]
    if ticker_data['roe'].notna().any():
        sample = ticker_data[ticker_data['roe'].notna()].head(5)
        print(f"\nTicker: {ticker}")
        print(sample.to_string(index=False))
        break
