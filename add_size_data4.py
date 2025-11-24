"""
Step 5: Create 'size' variable in data4.parquet based on percentile-based categories
Size categories are determined by market cap percentiles within each month
"""

import pandas as pd
import numpy as np

print("Adding size classification column to data4.parquet...")
print()

# Load data4.parquet
print("Loading data4.parquet...")
df = pd.read_parquet('data4.parquet')
print(f"  {len(df):,} rows")
print()

# Define percentile cutoffs for size categories
# Based on target distribution:
# Nano-Cap: bottom 3.34%
# Micro-Cap: 3.34% to 18.83% (15.49%)
# Small-Cap: 18.83% to 51.46% (32.63%)
# Mid-Cap: 51.46% to 78.6% (27.14%)
# Large-Cap: 78.6% to 98.53% (19.93%)
# Mega-Cap: top 1.47%

# Percentile breakpoints (cumulative from bottom)
NANO_CUTOFF = 3.34
MICRO_CUTOFF = 18.83  # 3.34 + 15.49
SMALL_CUTOFF = 51.46  # 18.83 + 32.63
MID_CUTOFF = 78.60    # 51.46 + 27.14
LARGE_CUTOFF = 98.53  # 78.60 + 19.93
# Mega-Cap is the top 1.47%

def categorize_by_percentile(group):
    """Assign size categories based on percentiles within a month"""
    mcap = group['marketcap']

    # Calculate percentile cutoffs for this month
    nano_thresh = mcap.quantile(NANO_CUTOFF / 100)
    micro_thresh = mcap.quantile(MICRO_CUTOFF / 100)
    small_thresh = mcap.quantile(SMALL_CUTOFF / 100)
    mid_thresh = mcap.quantile(MID_CUTOFF / 100)
    large_thresh = mcap.quantile(LARGE_CUTOFF / 100)

    # Assign categories using pd.cut with bins
    result = pd.Series(index=group.index, dtype='object')

    result[mcap.isna()] = np.nan
    result[mcap <= nano_thresh] = 'Nano-Cap'
    result[(mcap > nano_thresh) & (mcap <= micro_thresh)] = 'Micro-Cap'
    result[(mcap > micro_thresh) & (mcap <= small_thresh)] = 'Small-Cap'
    result[(mcap > small_thresh) & (mcap <= mid_thresh)] = 'Mid-Cap'
    result[(mcap > mid_thresh) & (mcap <= large_thresh)] = 'Large-Cap'
    result[mcap > large_thresh] = 'Mega-Cap'

    return result

# Apply categorization by month
print("Categorizing market cap by percentile within each month...")
df['size'] = df.groupby('month').apply(
    lambda x: categorize_by_percentile(x),
    include_groups=False
).reset_index(level=0, drop=True)

# Show distribution
print()
print("="*80)
print("SIZE DISTRIBUTION ACROSS ALL MONTHS")
print("="*80)
size_counts = df['size'].value_counts()
size_pcts = (size_counts / len(df[df['size'].notna()]) * 100).round(2)

summary = pd.DataFrame({
    'Count': size_counts,
    'Percentage': size_pcts
})

# Reorder by market cap size
order = ['Mega-Cap', 'Large-Cap', 'Mid-Cap', 'Small-Cap', 'Micro-Cap', 'Nano-Cap']
summary = summary.reindex([cat for cat in order if cat in summary.index])

print(summary)
print()

# Show distribution for November 2025
print("="*80)
print("SIZE DISTRIBUTION FOR NOVEMBER 2025")
print("="*80)
df_nov = df[df['month'] == '2025-11']
nov_counts = df_nov['size'].value_counts()
nov_pcts = (nov_counts / len(df_nov[df_nov['size'].notna()]) * 100).round(2)

nov_summary = pd.DataFrame({
    'Count': nov_counts,
    'Percentage': nov_pcts
})
nov_summary = nov_summary.reindex([cat for cat in order if cat in nov_summary.index])
print(nov_summary)
print()

# Save updated data4.parquet
print("Saving updated data4.parquet...")
df.to_parquet('data4.parquet', index=False)
print(f"  Saved {len(df):,} rows with {len(df.columns)} columns")
print()

print("="*80)
print("SUMMARY")
print("="*80)
print("\nAdded 'size' column to data4.parquet")
print("\nSize categories based on market cap percentiles within each month:")
print(f"  - Nano-Cap: bottom {NANO_CUTOFF}%")
print(f"  - Micro-Cap: {NANO_CUTOFF}% to {MICRO_CUTOFF}%")
print(f"  - Small-Cap: {MICRO_CUTOFF}% to {SMALL_CUTOFF}%")
print(f"  - Mid-Cap: {SMALL_CUTOFF}% to {MID_CUTOFF}%")
print(f"  - Large-Cap: {MID_CUTOFF}% to {LARGE_CUTOFF}%")
print(f"  - Mega-Cap: top {100 - LARGE_CUTOFF}%")

print("\nFinal columns:", list(df.columns))

print("\nSample data for AAPL:")
sample = df[df['ticker'] == 'AAPL'].dropna().tail(5)
if not sample.empty:
    print(sample[['ticker', 'month', 'marketcap', 'size']].to_string(index=False))
