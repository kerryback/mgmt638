import pandas as pd
import numpy as np

print("Adding gross profit to assets ratio to data2.parquet...")
print()

# Load data2.parquet
print("Loading data2.parquet...")
df = pd.read_parquet('data2.parquet')
print(f"  {len(df):,} rows")
print(f"  Current columns: {len(df.columns)}")
print()

# Check if we have the necessary columns
print("Checking for required columns...")
has_gp = 'gp' in df.columns
has_revenue = 'revenue' in df.columns
has_grossmargin = 'grossmargin' in df.columns
has_assets = 'assets' in df.columns

if not has_gp:
    print("  'gp' (gross profit) column not found")
    if has_revenue and has_grossmargin:
        print("  Will calculate from revenue * grossmargin")
    else:
        print("  ERROR: Need revenue and grossmargin columns")
        import sys
        sys.exit(1)
else:
    print("  'gp' (gross profit) column found")

if not has_assets:
    print("  ERROR: 'assets' column not found in data2.parquet")
    import sys
    sys.exit(1)

print()

# Calculate gp if not present
if not has_gp:
    print("Calculating gross profit (gp = revenue * grossmargin)...")
    df['gp'] = df['revenue'] * df['grossmargin']
    df['gp'] = df['gp'].round(2)  # Round to 2 decimal places for dollar amounts
    print(f"  Calculated gp from revenue and grossmargin")
    print()

# Calculate gp_to_assets ratio
print("Calculating gp_to_assets ratio...")
df['gp_to_assets'] = df['gp'] / df['assets']

# Set to NaN if assets <= 0 or gp is negative
df.loc[df['assets'] <= 0, 'gp_to_assets'] = np.nan

# Round to 4 decimal places
df['gp_to_assets'] = df['gp_to_assets'].round(4)

print(f"  Calculated gp_to_assets")
print()

# Calculate 5-year growth rate by ticker
print("Calculating 5-year growth rate for gp_to_assets...")

# Sort by ticker and month
df = df.sort_values(['ticker', 'month']).reset_index(drop=True)

# Calculate 5-year growth (60 months lag)
df['gp_to_assets_5y_growth'] = (
    df.groupby('ticker')['gp_to_assets'].apply(
        lambda x: ((x - x.shift(60)) / x.shift(60)).round(4)
    ).reset_index(level=0, drop=True)
)

print(f"  Calculated gp_to_assets_5y_growth")
print()

# Show coverage
print("Coverage of new variables:")
non_null = df['gp_to_assets'].notna().sum()
pct = (non_null / len(df)) * 100
print(f"  gp_to_assets: {non_null:,} ({pct:.1f}%)")

non_null_growth = df['gp_to_assets_5y_growth'].notna().sum()
pct_growth = (non_null_growth / len(df)) * 100
print(f"  gp_to_assets_5y_growth: {non_null_growth:,} ({pct_growth:.1f}%)")
print()

# Save updated data2.parquet
print("Saving updated data2.parquet...")
df.to_parquet('data2.parquet', index=False)
print(f"  Saved {len(df):,} rows with {len(df.columns)} columns")
print()

print("="*80)
print("SUMMARY")
print("="*80)
print("\nAdded variables to data2.parquet:")
print("  - gp_to_assets: Gross Profit / Assets ratio")
print("  - gp_to_assets_5y_growth: 5-year growth rate")
print("\nThis ratio measures how efficiently a company generates gross profit")
print("relative to its total asset base.")

print("\nSample data for AAPL:")
sample = df[df['ticker'] == 'AAPL'].tail(10)
if not sample.empty:
    cols_to_show = ['ticker', 'month', 'gp', 'assets', 'gp_to_assets', 'gp_to_assets_5y_growth']
    print(sample[cols_to_show].to_string())
