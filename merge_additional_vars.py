import pandas as pd
import numpy as np

print("Merging additional SF1 variables into data2.parquet...")
print()

# Load existing data2
print("Loading data2.parquet...")
df_data2 = pd.read_parquet('data2.parquet')
print(f"  {len(df_data2):,} rows")
print(f"  Columns: {list(df_data2.columns)}")
print()

# Load new SF1 variables
print("Loading sf1_additional_vars.parquet...")
df_sf1_add = pd.read_parquet('sf1_additional_vars.parquet')
print(f"  {len(df_sf1_add):,} rows")
print(f"  Columns: {list(df_sf1_add.columns)}")
print()

# Convert month to datetime for merging
print("Preparing data for merge...")
df_data2['month_dt'] = pd.to_datetime(df_data2['month'])
df_sf1_add['datekey'] = pd.to_datetime(df_sf1_add['datekey'])

print("Merging using left join on ticker first...")
# First, prepare SF1 data by keeping only the most recent datekey for each ticker-reportperiod
df_sf1_sorted = df_sf1_add.sort_values(['ticker', 'reportperiod', 'datekey']).drop_duplicates(['ticker', 'reportperiod'], keep='last')
df_sf1_sorted = df_sf1_sorted.drop(columns=['reportperiod'])  # Don't need reportperiod after this

# Merge by iterating through each ticker to avoid sorting issues
print("Performing ticker-by-ticker merge...")
all_merged = []
tickers = df_data2['ticker'].unique()

for i, ticker in enumerate(tickers):
    if (i + 1) % 500 == 0:
        print(f"  Processing ticker {i+1}/{len(tickers)}")

    df_ticker = df_data2[df_data2['ticker'] == ticker].copy()
    df_sf1_ticker = df_sf1_sorted[df_sf1_sorted['ticker'] == ticker].copy()

    if len(df_sf1_ticker) == 0:
        # No SF1 data for this ticker, add NaN columns
        sf1_cols = ['dps', 'payoutratio', 'assetturnover', 'equity_multiplier',
                    'dps_5y_growth', 'payoutratio_5y_growth', 'assetturnover_5y_growth', 'equity_multiplier_5y_growth']
        for col in sf1_cols:
            df_ticker[col] = np.nan
    else:
        # Sort by date for merge_asof
        df_ticker = df_ticker.sort_values('month_dt').reset_index(drop=True)
        df_sf1_ticker = df_sf1_ticker.sort_values('datekey').reset_index(drop=True)

        # Perform merge_asof for this ticker
        df_ticker = pd.merge_asof(
            df_ticker,
            df_sf1_ticker.drop(columns=['ticker']),
            left_on='month_dt',
            right_on='datekey',
            direction='backward',
            tolerance=pd.Timedelta(days=180)
        )
        df_ticker = df_ticker.drop(columns=['datekey'])

    all_merged.append(df_ticker)

print("Combining all tickers...")
df_merged = pd.concat(all_merged, ignore_index=True)

# Drop temporary column
df_merged = df_merged.drop(columns=['month_dt'])

print(f"  Merged {len(df_merged):,} rows")
print()

# Check how many rows have the new variables
print("Coverage of new variables:")
for var in ['dps', 'payoutratio', 'assetturnover', 'equity_multiplier']:
    non_null = df_merged[var].notna().sum()
    pct = (non_null / len(df_merged)) * 100
    print(f"  {var}: {non_null:,} ({pct:.1f}%)")
print()

# Save the updated data2
print("Saving updated data2.parquet...")
df_merged.to_parquet('data2.parquet', index=False)
print(f"  Saved {len(df_merged):,} rows")
print()

print("="*80)
print("SUMMARY")
print("="*80)
print(f"\nAdded variables to data2.parquet:")
print(f"  - dps (dividends per share)")
print(f"  - payoutratio")
print(f"  - assetturnover")
print(f"  - equity_multiplier")
print(f"  - dps_5y_growth")
print(f"  - payoutratio_5y_growth")
print(f"  - assetturnover_5y_growth")
print(f"  - equity_multiplier_5y_growth")

print(f"\nSample data for AAPL in recent months:")
sample = df_merged[df_merged['ticker'] == 'AAPL'].tail(5)
if not sample.empty:
    cols_to_show = ['ticker', 'month', 'dps', 'payoutratio', 'assetturnover', 'equity_multiplier']
    print(sample[cols_to_show].to_string())
