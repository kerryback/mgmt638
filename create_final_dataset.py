import pandas as pd

print("Creating final merged dataset from scratch...")

# Load all the data files
print("\n1. Loading monthly returns and momentum...")
df_returns = pd.read_parquet('monthly_returns_momentum.parquet')
print(f"   Loaded {len(df_returns)} rows, {df_returns['ticker'].nunique()} tickers")

print("\n2. Loading monthly DAILY metrics...")
df_daily = pd.read_parquet('monthly_daily_metrics.parquet')
print(f"   Loaded {len(df_daily)} rows, {df_daily['ticker'].nunique()} tickers")

print("\n3. Loading SF1 fundamentals with growth rates...")
df_sf1 = pd.read_parquet('sf1_fundamentals_with_growth.parquet')
print(f"   Loaded {len(df_sf1)} rows, {df_sf1['ticker'].nunique()} tickers")

# Step 1: Merge returns with DAILY metrics
print("\n4. Merging returns with DAILY metrics on (ticker, month, date)...")
df_base = pd.merge(
    df_returns,
    df_daily[['ticker', 'month', 'date', 'ev', 'evebit', 'evebitda', 'marketcap', 'pb', 'pe', 'ps']],
    on=['ticker', 'month', 'date'],
    how='inner'
)
print(f"   After merge: {len(df_base)} rows")

# Step 2: Prepare returns data - shift close and valuation metrics to represent prior period
print("\n5. Shifting close and valuation metrics to represent prior period...")
df_base = df_base.sort_values(['ticker', 'date']).reset_index(drop=True)

shift_vars = ['close', 'marketcap', 'pe', 'pb', 'ps', 'ev', 'evebit', 'evebitda']
for var in shift_vars:
    df_base[var] = df_base.groupby('ticker')[var].shift(1)

print(f"   Shifted {len(shift_vars)} variables")

# Step 3: Prepare SF1 data - calculate first month AFTER filing date
print("\n6. Preparing SF1 data for merge...")
df_sf1['datekey'] = pd.to_datetime(df_sf1['datekey'])
df_sf1['available_month_start'] = df_sf1['datekey'] + pd.offsets.MonthBegin(1)
df_sf1['month'] = df_sf1['available_month_start'].dt.strftime('%Y-%m')

# Select SF1 columns to keep
sf1_cols = ['ticker', 'month', 'revenue', 'netinc', 'eps', 'ebitda', 'assets', 'equity', 'debt',
            'cashneq', 'ncfo', 'fcf', 'roe', 'roa', 'grossmargin', 'netmargin', 'shareswa',
            'revenue_5y_growth', 'netinc_5y_growth', 'eps_5y_growth', 'ebitda_5y_growth',
            'assets_5y_growth', 'equity_5y_growth', 'debt_5y_growth', 'cashneq_5y_growth',
            'ncfo_5y_growth', 'fcf_5y_growth']

print(f"   SF1 data prepared: {len(df_sf1)} rows")

# Step 4: Merge with SF1 data
print("\n7. Merging with SF1 fundamentals on (ticker, month)...")
df_final = pd.merge(
    df_base,
    df_sf1[sf1_cols],
    on=['ticker', 'month'],
    how='left'
)
print(f"   After merge: {len(df_final)} rows")

# Step 5: Sort and forward fill fundamentals
print("\n8. Forward filling fundamental data within each ticker...")
df_final = df_final.sort_values(['ticker', 'date']).reset_index(drop=True)

fundamental_vars = [col for col in sf1_cols if col not in ['ticker', 'month']]
df_final[fundamental_vars] = df_final.groupby('ticker')[fundamental_vars].ffill()

# Step 6: Drop date column
print("\n9. Dropping date column...")
df_final = df_final.drop(columns=['date'])

# Step 7: Save final dataset
print(f"\n10. Final dataset summary:")
print(f"   Total rows: {len(df_final)}")
print(f"   Unique tickers: {df_final['ticker'].nunique()}")
print(f"   Columns: {df_final.columns.tolist()}")

print(f"\nFirst 20 rows:")
print(df_final.head(20))

print(f"\nSample for ticker 'AAPL':")
print(df_final[df_final['ticker'] == 'AAPL'].head(20))

print(f"\nSummary statistics:")
print(df_final[['close', 'return', 'momentum', 'marketcap', 'pe', 'pb', 'revenue', 'equity']].describe())

# Save to parquet
output_file = 'complete_merged_data.parquet'
df_final.to_parquet(output_file, index=False)
print(f"\nComplete merged data saved to {output_file}")
