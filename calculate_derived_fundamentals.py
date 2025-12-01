"""
Calculate derived fundamental variables:
- asset_growth: Year-over-year asset growth
- gp_to_assets: Gross profit to assets ratio
- leverage: Debt to equity ratio

IMPORTANT: Per course instructions:
- ALWAYS group by ticker when calculating changes/growth
- Set ratios with equity in denominator to NaN if equity <= 0
"""
import pandas as pd
import numpy as np

print("Loading SF1 fundamentals data...")
df = pd.read_parquet('sf1_fundamentals_all.parquet')
print(f"Loaded {len(df)} rows")
print(f"Columns: {list(df.columns)}")

# Sort by ticker and datekey to ensure proper ordering
df = df.sort_values(['ticker', 'datekey']).reset_index(drop=True)

print("\nCalculating derived metrics...")

# 1. Asset Growth (year-over-year) - MUST group by ticker
print("  Calculating asset_growth (YoY)...")
df['asset_growth'] = df.groupby('ticker')['assets'].pct_change().round(4)

# 2. Gross Profit to Assets - rounded to 4 decimals
print("  Calculating gp_to_assets...")
df['gp_to_assets'] = (df['gp'] / df['assets']).round(4)
# Handle cases where assets is zero or missing
df.loc[df['assets'].isna() | (df['assets'] == 0), 'gp_to_assets'] = float('nan')

# 3. Leverage (Debt to Equity) - MUST set to NaN if equity <= 0
print("  Calculating leverage (debt/equity)...")
df['leverage'] = (df['debt'] / df['equity']).round(4)
# CRITICAL: Set to NaN if equity <= 0 (per course instructions)
df.loc[(df['equity'].isna()) | (df['equity'] <= 0), 'leverage'] = float('nan')

# Display summary statistics
print("\nSummary of calculated metrics:")
print(f"  asset_growth - non-null: {df['asset_growth'].notna().sum()}, mean: {df['asset_growth'].mean():.4f}")
print(f"  gp_to_assets - non-null: {df['gp_to_assets'].notna().sum()}, mean: {df['gp_to_assets'].mean():.4f}")
print(f"  leverage - non-null: {df['leverage'].notna().sum()}, mean: {df['leverage'].mean():.4f}")

# Save the enhanced fundamentals
output_file = 'sf1_fundamentals_enhanced.parquet'
df.to_parquet(output_file, index=False)
print(f"\nSaved enhanced fundamentals to {output_file}")
print(f"Total rows: {len(df)}")
print(f"Columns: {list(df.columns)}")
