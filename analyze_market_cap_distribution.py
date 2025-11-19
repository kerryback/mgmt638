import pandas as pd
import numpy as np

print("Analyzing Market Cap Distribution in November 2025...\n")

# Load November 2025 data
df = pd.read_excel('data2_nov2025.xlsx')

# Market cap is in MILLIONS of dollars
# Convert breakpoints to millions for comparison
# Breakpoints in billions, converted to millions:
# Mega-Cap: >= $200B = 200,000 millions
# Large-Cap: $10B - $200B = 10,000 - 200,000 millions
# Mid-Cap: $2B - $10B = 2,000 - 10,000 millions
# Small-Cap: $300M - $2B = 300 - 2,000 millions
# Micro-Cap: $50M - $300M = 50 - 300 millions
# Nano-Cap: < $50M = < 50 millions

def categorize_market_cap(mcap_millions):
    if pd.isna(mcap_millions):
        return 'Unknown'
    elif mcap_millions >= 200_000:
        return 'Mega-Cap (>=$200B)'
    elif mcap_millions >= 10_000:
        return 'Large-Cap ($10B-$200B)'
    elif mcap_millions >= 2_000:
        return 'Mid-Cap ($2B-$10B)'
    elif mcap_millions >= 300:
        return 'Small-Cap ($300M-$2B)'
    elif mcap_millions >= 50:
        return 'Micro-Cap ($50M-$300M)'
    else:
        return 'Nano-Cap (<$50M)'

df['category'] = df['marketcap'].apply(categorize_market_cap)

# Count and percentage by category
category_counts = df['category'].value_counts()
category_pcts = (category_counts / len(df) * 100).round(2)

print("="*80)
print("MARKET CAP DISTRIBUTION - November 2025")
print("="*80)
print(f"\nTotal companies: {len(df):,}\n")

# Create summary table
summary = pd.DataFrame({
    'Count': category_counts,
    'Percentage': category_pcts
})

# Reorder by market cap size
order = ['Mega-Cap (>=$200B)', 'Large-Cap ($10B-$200B)', 'Mid-Cap ($2B-$10B)',
         'Small-Cap ($300M-$2B)', 'Micro-Cap ($50M-$300M)', 'Nano-Cap (<$50M)', 'Unknown']
summary = summary.reindex([cat for cat in order if cat in summary.index])

print(summary)
print()

# Calculate cumulative percentages
print("="*80)
print("CUMULATIVE DISTRIBUTION")
print("="*80)
cumulative = 0
for cat in summary.index:
    if cat != 'Unknown':
        cumulative += summary.loc[cat, 'Percentage']
        print(f"{cat}: {cumulative:.2f}% cumulative")

# Show some statistics
print("\n" + "="*80)
print("MARKET CAP STATISTICS")
print("="*80)
valid_mcap = df[df['marketcap'].notna()]['marketcap']
print(f"In millions:")
print(f"  Mean:   ${valid_mcap.mean():,.2f} million")
print(f"  Median: ${valid_mcap.median():,.2f} million")
print(f"  Min:    ${valid_mcap.min():,.2f} million")
print(f"  Max:    ${valid_mcap.max():,.2f} million")
print(f"\nIn billions:")
print(f"  Mean:   ${valid_mcap.mean()/1000:,.2f} billion")
print(f"  Median: ${valid_mcap.median()/1000:,.2f} billion")
print(f"  Max:    ${valid_mcap.max()/1000:,.2f} billion")

# Show percentiles
print(f"\nPercentiles (in millions):")
print(f"  10th: ${valid_mcap.quantile(0.10):,.2f}M")
print(f"  25th: ${valid_mcap.quantile(0.25):,.2f}M")
print(f"  50th: ${valid_mcap.quantile(0.50):,.2f}M")
print(f"  75th: ${valid_mcap.quantile(0.75):,.2f}M")
print(f"  90th: ${valid_mcap.quantile(0.90):,.2f}M")

print(f"\nPercentiles (in billions):")
print(f"  10th: ${valid_mcap.quantile(0.10)/1000:,.2f}B")
print(f"  25th: ${valid_mcap.quantile(0.25)/1000:,.2f}B")
print(f"  50th: ${valid_mcap.quantile(0.50)/1000:,.2f}B")
print(f"  75th: ${valid_mcap.quantile(0.75)/1000:,.2f}B")
print(f"  90th: ${valid_mcap.quantile(0.90)/1000:,.2f}B")

# Show examples from each category
print("\n" + "="*80)
print("EXAMPLES FROM EACH CATEGORY")
print("="*80)

for cat in summary.index:
    if cat != 'Unknown':
        print(f"\n{cat}:")
        examples = df[df['category'] == cat].nlargest(5, 'marketcap')[['ticker', 'marketcap', 'industry']]
        for idx, row in examples.iterrows():
            mcap_b = row['marketcap'] / 1_000
            print(f"  {row['ticker']}: ${mcap_b:,.2f}B (${row['marketcap']:,.2f}M) - {row['industry']}")
