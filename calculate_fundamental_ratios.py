"""
Calculate derived fundamental metrics BEFORE merging with monthly data.
"""
import pandas as pd
import numpy as np

print("Loading fundamentals...")
df = pd.read_parquet('fundamentals.parquet')
print(f"Loaded {len(df)} records for {df['ticker'].nunique()} tickers")

# Sort by ticker and datekey to ensure proper ordering
df = df.sort_values(['ticker', 'datekey']).reset_index(drop=True)

print("\nCalculating derived metrics...")

# 1. Asset growth: year-over-year asset growth as decimal
# For annual data (ARY), lag by 1 period to get prior year
df['asset_growth'] = (
    df.groupby('ticker')['assets']
    .pct_change()
).round(4)

# 2. GP to Assets ratio
df['gp_to_assets'] = (df['gp'] / df['assets']).round(4)

# 3. Leverage: debt to equity
df['leverage'] = (df['debt'] / df['equity']).round(4)

# Set ratios to NaN where denominators are invalid
df.loc[df['assets'] <= 0, 'gp_to_assets'] = np.nan
df.loc[df['equity'] <= 0, 'leverage'] = np.nan

print("\nDerived metrics calculated:")
print(f"- asset_growth: year-over-year growth in assets (decimal)")
print(f"- gp_to_assets: gross profit / assets")
print(f"- leverage: debt / equity")

# Save updated fundamentals
df.to_parquet('fundamentals_with_ratios.parquet', index=False)
print(f"\nSaved {len(df)} rows to fundamentals_with_ratios.parquet")

# Show sample
print("\nSample data:")
print(df[['ticker', 'reportperiod', 'assets', 'asset_growth', 'gp', 'gp_to_assets',
         'debt', 'equity', 'leverage']].head(10).to_string(index=False))
