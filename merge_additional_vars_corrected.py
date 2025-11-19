import pandas as pd
import numpy as np

print("Merging additional SF1 variables into data2.parquet (CORRECTED METHOD)...")
print()

# Load existing data2 (but remove the incorrectly merged columns first)
print("Loading data2.parquet...")
df_data2 = pd.read_parquet('data2.parquet')

# Remove the incorrectly merged columns
cols_to_remove = ['dps', 'payoutratio', 'assetturnover', 'equity_multiplier',
                  'dps_5y_growth', 'payoutratio_5y_growth', 'assetturnover_5y_growth', 'equity_multiplier_5y_growth']
df_data2 = df_data2.drop(columns=[col for col in cols_to_remove if col in df_data2.columns])

print(f"  {len(df_data2):,} rows")
print(f"  Columns after removing old merge: {len(df_data2.columns)}")
print()

# Load new SF1 variables
print("Loading sf1_additional_vars.parquet...")
df_sf1_add = pd.read_parquet('sf1_additional_vars.parquet')
print(f"  {len(df_sf1_add):,} rows")
print()

# Convert datekey to end-of-month dates
print("Converting datekey to end-of-month dates...")
df_sf1_add['datekey'] = pd.to_datetime(df_sf1_add['datekey'])
df_sf1_add['month'] = df_sf1_add['datekey'].dt.to_period('M').dt.to_timestamp('M').dt.strftime('%Y-%m')

# Drop reportperiod and datekey - we only need month now
df_sf1_add = df_sf1_add.drop(columns=['reportperiod', 'datekey'])

print(f"  SF1 data now has month column")
print()

# Perform outer merge on ticker and month
print("Performing outer merge on ticker and month...")
df_merged = pd.merge(
    df_data2,
    df_sf1_add,
    on=['ticker', 'month'],
    how='left'  # Use left join to keep all rows from data2
)

print(f"  Merged {len(df_merged):,} rows")
print()

# Forward-fill SF1 variables by ticker
print("Forward-filling SF1 variables by ticker...")
sf1_vars = ['dps', 'payoutratio', 'assetturnover', 'equity_multiplier',
            'dps_5y_growth', 'payoutratio_5y_growth', 'assetturnover_5y_growth', 'equity_multiplier_5y_growth']

# Sort by ticker and month to ensure proper forward-fill
df_merged = df_merged.sort_values(['ticker', 'month']).reset_index(drop=True)

# Forward-fill by ticker
for var in sf1_vars:
    print(f"  Forward-filling {var}...")
    df_merged[var] = df_merged.groupby('ticker')[var].ffill()

print()

# Check coverage after forward-fill
print("Coverage of new variables after forward-fill:")
for var in ['dps', 'payoutratio', 'assetturnover', 'equity_multiplier']:
    non_null = df_merged[var].notna().sum()
    pct = (non_null / len(df_merged)) * 100
    print(f"  {var}: {non_null:,} ({pct:.1f}%)")
print()

# Save the updated data2
print("Saving updated data2.parquet...")
df_merged.to_parquet('data2.parquet', index=False)
print(f"  Saved {len(df_merged):,} rows with {len(df_merged.columns)} columns")
print()

print("="*80)
print("SUMMARY")
print("="*80)
print(f"\nCorrected merge method used:")
print(f"  1. Converted SF1 datekey to end-of-month dates")
print(f"  2. Performed outer merge on ticker and month")
print(f"  3. Forward-filled SF1 variables by ticker")
print(f"\nThis ensures fundamentals are available in all subsequent months")
print(f"after they are filed, matching the pattern used for other SF1 variables.")

print(f"\nSample data for AAPL in recent months:")
sample = df_merged[df_merged['ticker'] == 'AAPL'].tail(10)
if not sample.empty:
    cols_to_show = ['ticker', 'month', 'dps', 'payoutratio', 'assetturnover', 'equity_multiplier']
    print(sample[cols_to_show].to_string())
