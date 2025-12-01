"""
Merge weekly returns with annual fundamentals.
Fundamentals become available the week after the filing date.
"""
import pandas as pd
import numpy as np

print("Loading weekly returns (original without fundamentals)...")
# Load the original weekly data before fundamentals were added
df_weekly = pd.read_parquet('data5.parquet')
print(f"Weekly data: {len(df_weekly)} rows, {df_weekly['ticker'].nunique()} tickers")

# Drop any existing fundamental columns (they're all NaN from earlier failed merge)
cols_to_drop = ['pb', 'asset_growth', 'roe', 'gp_to_assets', 'grossmargin',
                'assetturnover', 'leverage', 'equity', 'assets', 'gp', 'debt']
cols_to_drop = [c for c in cols_to_drop if c in df_weekly.columns]
if cols_to_drop:
    print(f"Dropping existing (empty) fundamental columns: {cols_to_drop}")
    df_weekly = df_weekly.drop(columns=cols_to_drop)

# Rename lag_month to lagged_return if it exists
if 'lag_month' in df_weekly.columns:
    print("Renaming lag_month to lagged_return...")
    df_weekly = df_weekly.rename(columns={'lag_month': 'lagged_return'})

print("\nLoading fundamentals with ratios...")
df_fund = pd.read_parquet('fundamentals_weekly_with_ratios.parquet')
print(f"Fundamentals: {len(df_fund)} rows, {df_fund['ticker'].nunique()} tickers")

# Convert datekey to datetime
df_fund['datekey'] = pd.to_datetime(df_fund['datekey'])

# Calculate first week AFTER filing date using ISO week format
# Add 7 days to ensure we're in the next week, then get that week's ISO identifier
df_fund['filing_plus_week'] = df_fund['datekey'] + pd.Timedelta(days=7)
df_fund['iso_year'] = df_fund['filing_plus_week'].dt.isocalendar().year
df_fund['iso_week'] = df_fund['filing_plus_week'].dt.isocalendar().week
df_fund['available_week'] = df_fund['iso_year'].astype(str) + '-' + df_fund['iso_week'].astype(str).str.zfill(2)

print(f"\nSample fundamental availability dates:")
print(df_fund[['ticker', 'datekey', 'available_week']].head(10).to_string(index=False))

# Select fundamental columns for merge (drop helper columns)
fund_cols = ['ticker', 'available_week', 'equity', 'assets', 'roe', 'gp',
             'grossmargin', 'assetturnover', 'debt', 'asset_growth',
             'gp_to_assets', 'leverage']
df_fund_merge = df_fund[fund_cols].copy()
df_fund_merge = df_fund_merge.rename(columns={'available_week': 'week'})

print(f"\nFundamental data for merge:")
print(f"  Columns: {list(df_fund_merge.columns)}")
print(f"  Rows: {len(df_fund_merge)}")
print(f"  Sample weeks: {df_fund_merge['week'].head(10).tolist()}")

print(f"\nWeekly data sample weeks: {df_weekly['week'].head(10).tolist()}")

print(f"\nMerging...")
df_merged = pd.merge(
    df_weekly,
    df_fund_merge,
    on=['ticker', 'week'],
    how='left'
)

print(f"Initial merge: {len(df_merged)} rows")
print(f"Columns after merge: {list(df_merged.columns)}")
if 'roe' in df_merged.columns:
    print(f"Rows with fundamentals: {df_merged['roe'].notna().sum()}")
else:
    print("ERROR: roe column not in merged data!")

# Forward fill fundamental data within each ticker
print("\nForward filling fundamental data...")
fundamental_vars = ['equity', 'assets', 'roe', 'gp', 'grossmargin',
                   'assetturnover', 'debt', 'asset_growth', 'gp_to_assets', 'leverage']
df_merged[fundamental_vars] = df_merged.groupby('ticker')[fundamental_vars].ffill()

print(f"After forward fill - Rows with fundamentals: {df_merged['roe'].notna().sum()}")

# Calculate pb (price-to-book ratio) = marketcap / (equity/1000)
print("\nCalculating pb (price-to-book)...")
df_merged['pb'] = (df_merged['marketcap'] / (df_merged['equity'] / 1000)).round(4)
df_merged.loc[df_merged['equity'] <= 0, 'pb'] = np.nan

# Select final columns
final_cols = ['ticker', 'week', 'return', 'momentum', 'lagged_return', 'close',
              'marketcap', 'pb', 'asset_growth', 'roe', 'gp_to_assets',
              'grossmargin', 'assetturnover', 'leverage', 'sector', 'industry', 'size']
df_final = df_merged[final_cols]

# Save
df_final.to_parquet('data5.parquet', index=False)
print(f"\nSaved {len(df_final)} rows to data5.parquet")
print(f"Columns: {list(df_final.columns)}")
print(f"Rows with fundamentals: {df_final['roe'].notna().sum()}")

# Show sample
print("\nSample data with fundamentals:")
print(df_final[df_final['roe'].notna()].head(10).to_string(index=False))
