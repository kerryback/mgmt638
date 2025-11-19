import pandas as pd
import numpy as np

print("Adding size classification column to data2.parquet...")
print()

# Load data2.parquet
print("Loading data2.parquet...")
df = pd.read_parquet('data2.parquet')
print(f"  {len(df):,} rows")
print()

# Define market cap categorization function
# Market cap is in MILLIONS of dollars
# Breakpoints in billions, converted to millions:
# Mega-Cap: >= $200B = 200,000 millions
# Large-Cap: $10B - $200B = 10,000 - 200,000 millions
# Mid-Cap: $2B - $10B = 2,000 - 10,000 millions
# Small-Cap: $300M - $2B = 300 - 2,000 millions
# Micro-Cap: $50M - $300M = 50 - 300 millions
# Nano-Cap: < $50M = < 50 millions

def categorize_market_cap(mcap_millions):
    if pd.isna(mcap_millions):
        return np.nan
    elif mcap_millions >= 200_000:
        return 'Mega-Cap'
    elif mcap_millions >= 10_000:
        return 'Large-Cap'
    elif mcap_millions >= 2_000:
        return 'Mid-Cap'
    elif mcap_millions >= 300:
        return 'Small-Cap'
    elif mcap_millions >= 50:
        return 'Micro-Cap'
    else:
        return 'Nano-Cap'

# Apply categorization
print("Categorizing market cap for each row...")
df['size'] = df['marketcap'].apply(categorize_market_cap)

# Show distribution
print()
print("="*80)
print("SIZE DISTRIBUTION ACROSS ALL MONTHS")
print("="*80)
size_counts = df['size'].value_counts()
size_pcts = (size_counts / len(df) * 100).round(2)

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
nov_pcts = (nov_counts / len(df_nov) * 100).round(2)

nov_summary = pd.DataFrame({
    'Count': nov_counts,
    'Percentage': nov_pcts
})

nov_summary = nov_summary.reindex([cat for cat in order if cat in nov_summary.index])
print(nov_summary)
print()

# Save updated data2.parquet
print("Saving updated data2.parquet...")
df.to_parquet('data2.parquet', index=False)
print(f"  Saved {len(df):,} rows with {len(df.columns)} columns")
print()

print("="*80)
print("SUMMARY")
print("="*80)
print("\nAdded 'size' column to data2.parquet")
print("\nSize categories based on market cap:")
print("  - Mega-Cap: >= $200B")
print("  - Large-Cap: $10B - $200B")
print("  - Mid-Cap: $2B - $10B")
print("  - Small-Cap: $300M - $2B")
print("  - Micro-Cap: $50M - $300M")
print("  - Nano-Cap: < $50M")
print("\nSample data for AAPL:")
sample = df[df['ticker'] == 'AAPL'].tail(5)
if not sample.empty:
    print(sample[['ticker', 'month', 'marketcap', 'size']].to_string())
