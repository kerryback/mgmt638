"""
Create final monthly dataset - SIMPLE VERSION
1. Load monthly returns
2. Load monthly pb and merge by (ticker, date)
3. Load fundamentals, expand to monthly, merge by (ticker, month)
4. Shift variables
"""
import pandas as pd
import numpy as np

print("Step 1: Load monthly returns...")
df = pd.read_parquet('monthly_returns.parquet')
print(f"  {len(df)} rows")
print(f"  Columns: {df.columns.tolist()}")

print("\nStep 2: Load and merge pb...")
df_pb = pd.read_parquet('monthly_pb.parquet')
df['date'] = pd.to_datetime(df['date'])
df_pb['date'] = pd.to_datetime(df_pb['date'])
df = df.merge(df_pb[['ticker', 'date', 'pb']], on=['ticker', 'date'], how='left')
print(f"  {len(df)} rows after merge")

print("\nStep 3: Load fundamentals and expand to monthly...")
df_fund = pd.read_parquet('monthly_fundamentals.parquet')

# Convert filing date to month format (YYYY-MM)
df_fund['datekey'] = pd.to_datetime(df_fund['datekey'])
df_fund['filing_month'] = df_fund['datekey'].dt.to_period('M').astype(str)

# For each ticker, create monthly rows from first filing to present
print("  Expanding fundamentals to monthly frequency...")
expanded_funds = []

for ticker in df_fund['ticker'].unique():
    ticker_fund = df_fund[df_fund['ticker'] == ticker].sort_values('datekey')

    if len(ticker_fund) == 0:
        continue

    # Get all months we need for this ticker from df
    ticker_months = df[df['ticker'] == ticker]['month'].unique()

    if len(ticker_months) == 0:
        continue

    # Create a monthly dataframe for this ticker
    monthly_df = pd.DataFrame({'month': ticker_months, 'ticker': ticker})
    monthly_df = monthly_df.sort_values('month')

    # For each fundamental variable, forward fill from filing dates
    for col in ['equity', 'assets', 'gp', 'roe', 'grossmargin',
                'assetturnover', 'de', 'asset_growth', 'gp_to_assets']:
        # Create a mapping from filing_month to value
        values = ticker_fund.set_index('filing_month')[col].to_dict()

        # For each month, find the most recent prior filing
        monthly_df[col] = None
        for idx, row in monthly_df.iterrows():
            month = row['month']
            # Find most recent filing before or at this month
            recent_value = None
            for filing_month, value in sorted(values.items()):
                if filing_month <= month:
                    recent_value = value
                else:
                    break
            monthly_df.at[idx, col] = recent_value

    expanded_funds.append(monthly_df)

df_fund_monthly = pd.concat(expanded_funds, ignore_index=True)
print(f"  Expanded to {len(df_fund_monthly)} monthly rows")

print("\nStep 4: Merge with fundamentals by (ticker, month)...")
df = df.merge(df_fund_monthly, on=['ticker', 'month'], how='left')
print(f"  {len(df)} rows after merge")

print("\nStep 5: Shift SF1 variables by 1 month...")
sf1_vars = ['roe', 'grossmargin', 'assetturnover', 'de', 'asset_growth', 'gp_to_assets']
for var in sf1_vars:
    df[var] = df.groupby('ticker')[var].shift(1)

# Rename de to leverage
df = df.rename(columns={'de': 'leverage'})

print("\nStep 6: Create lagged_return...")
df['lagged_return'] = df.groupby('ticker')['return'].shift(1)

print("\nStep 7: Select final columns...")
final_columns = [
    'ticker', 'month', 'return', 'momentum', 'lagged_return', 'close',
    'marketcap', 'pb', 'asset_growth', 'roe', 'gp_to_assets',
    'grossmargin', 'assetturnover', 'leverage', 'sector', 'industry', 'size'
]

df_final = df[final_columns].copy()
df_final = df_final.sort_values(['ticker', 'month']).reset_index(drop=True)

# Save
output_file = 'data5_monthly.parquet'
df_final.to_parquet(output_file, index=False)
print(f"\n✓ Saved {len(df_final)} rows to {output_file}")

print(f"\nMonth range: {df_final['month'].min()} to {df_final['month'].max()}")
print(f"Unique tickers: {df_final['ticker'].nunique()}")
print(f"\nSample:")
print(df_final.head(20))
