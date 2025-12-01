"""
Create final monthly dataset combining returns, pb, and fundamentals
"""
import pandas as pd
import numpy as np

print("Loading datasets...")
# Load monthly returns
df_returns = pd.read_parquet('monthly_returns.parquet')
print(f"Monthly returns: {len(df_returns)} rows")
print(f"Columns: {df_returns.columns.tolist()}")

# Load monthly pb
df_pb = pd.read_parquet('monthly_pb.parquet')
print(f"\nMonthly pb: {len(df_pb)} rows")
print(f"Columns: {df_pb.columns.tolist()}")

# Load fundamentals
df_fund = pd.read_parquet('monthly_fundamentals.parquet')
print(f"\nFundamentals: {len(df_fund)} rows")
print(f"Columns: {df_fund.columns.tolist()}")

# Merge returns with pb on ticker and date
print("\nMerging returns with pb...")
df = pd.merge(df_returns, df_pb[['ticker', 'date', 'pb']], on=['ticker', 'date'], how='left')
print(f"After pb merge: {len(df)} rows")

# Prepare fundamentals for merging
# Use datekey as the filing date (when data becomes available)
df_fund = df_fund.rename(columns={'datekey': 'filing_date'})
df_fund = df_fund.sort_values(['ticker', 'filing_date'])

# For each month in df, we want the most recent filing that occurred BEFORE that month
print("\nMerging with fundamentals (using filing date logic)...")
df = df.sort_values(['ticker', 'date'])

# Convert to allow merging
df_fund['filing_date'] = pd.to_datetime(df_fund['filing_date'])
df['date'] = pd.to_datetime(df['date'])

# For each ticker-month, find the most recent fundamental data
# where filing_date is before the month start
merged_data = []

for ticker in df['ticker'].unique():
    df_ticker = df[df['ticker'] == ticker].copy()
    df_fund_ticker = df_fund[df_fund['ticker'] == ticker].copy()

    if len(df_fund_ticker) == 0:
        # No fundamental data for this ticker
        merged_data.append(df_ticker)
        continue

    # For each row in df_ticker, find the most recent fundamental filing
    for idx, row in df_ticker.iterrows():
        month_start = row['date'].replace(day=1)
        # Get the most recent filing BEFORE this month
        recent_fund = df_fund_ticker[df_fund_ticker['filing_date'] < month_start]

        if len(recent_fund) > 0:
            # Take the most recent
            recent_fund = recent_fund.iloc[-1]
            for col in ['equity', 'assets', 'gp', 'roe', 'grossmargin',
                       'assetturnover', 'de', 'asset_growth', 'gp_to_assets']:
                if col in recent_fund.index:
                    df_ticker.loc[idx, col] = recent_fund[col]

    merged_data.append(df_ticker)

df = pd.concat(merged_data, ignore_index=True)
print(f"After fundamentals merge: {len(df)} rows")

# Now shift all SF1 variables by 1 month (grouped by ticker)
print("\nShifting SF1 variables by 1 month...")
sf1_vars = ['roe', 'grossmargin', 'assetturnover', 'de', 'asset_growth', 'gp_to_assets']
for var in sf1_vars:
    if var in df.columns:
        df[var] = df.groupby('ticker')[var].shift(1)

# Rename 'de' to 'leverage'
print("\nRenaming 'de' to 'leverage'...")
df = df.rename(columns={'de': 'leverage'})

# Create 'lagged_return' which is the prior month's return
print("Calculating lagged_return...")
df['lagged_return'] = df.groupby('ticker')['return'].shift(1)

# Select final columns to match data5.parquet structure
# ticker, month, return, momentum, lagged_return, close, marketcap, pb,
# asset_growth, roe, gp_to_assets, grossmargin, assetturnover, leverage,
# sector, industry, size

final_columns = [
    'ticker', 'month', 'return', 'momentum', 'lagged_return', 'close',
    'marketcap', 'pb', 'asset_growth', 'roe', 'gp_to_assets',
    'grossmargin', 'assetturnover', 'leverage', 'sector', 'industry', 'size'
]

# Check which columns exist
missing_cols = [col for col in final_columns if col not in df.columns]
if missing_cols:
    print(f"\nWarning: Missing columns: {missing_cols}")

# Select only the columns that exist
available_cols = [col for col in final_columns if col in df.columns]
df_final = df[available_cols].copy()

# Sort by ticker and month
df_final = df_final.sort_values(['ticker', 'month']).reset_index(drop=True)

# Save final dataset
output_file = 'data5_monthly.parquet'
df_final.to_parquet(output_file, index=False)
print(f"\nSaved {len(df_final)} rows to {output_file}")

# Show summary
print(f"\nFinal columns: {df_final.columns.tolist()}")
print(f"\nMonth range: {df_final['month'].min()} to {df_final['month'].max()}")
print(f"Number of unique tickers: {df_final['ticker'].nunique()}")

print("\nSample data:")
print(df_final.head(20))

print("\nData types:")
print(df_final.dtypes)

print("\nSummary statistics:")
print(df_final.describe())
