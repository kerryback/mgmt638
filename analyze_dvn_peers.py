import pandas as pd
import numpy as np

print("Analyzing DVN and its peers in Oil & Gas E&P...\n")

# Load November 2025 data
df = pd.read_excel('data2_nov2025.xlsx')

# Get DVN info
dvn = df[df['ticker'] == 'DVN'].iloc[0]
dvn_marketcap = dvn['marketcap']  # in thousands
dvn_industry = dvn['industry']
dvn_pe = dvn['pe']

print(f"DVN (Devon Energy)")
print(f"  Industry: {dvn_industry}")
print(f"  Market Cap: ${dvn_marketcap:,.0f} thousand = ${dvn_marketcap/1000:,.2f} million")
print(f"  P/E Ratio: {dvn_pe:.1f}")
print(f"  Price: ${dvn['close']:.2f}")
print()

# Define similar market cap range (±50% of DVN's market cap)
lower_bound = dvn_marketcap * 0.5
upper_bound = dvn_marketcap * 1.5

print(f"Looking for peers in {dvn_industry}")
print(f"Market cap range: ${lower_bound:,.0f} to ${upper_bound:,.0f} thousand")
print(f"                  ${lower_bound/1000:,.2f}M to ${upper_bound/1000:,.2f}M")
print()

# Filter for same industry and similar market cap
peers = df[
    (df['industry'] == dvn_industry) &
    (df['marketcap'] >= lower_bound) &
    (df['marketcap'] <= upper_bound) &
    (df['ticker'] != 'DVN')  # Exclude DVN itself
].copy()

# Add DVN to the list for comparison
all_companies = pd.concat([peers, df[df['ticker'] == 'DVN']], ignore_index=True)

# Sort by market cap
all_companies = all_companies.sort_values('marketcap', ascending=False)

# Calculate market cap in millions
all_companies['marketcap_millions'] = all_companies['marketcap'] / 1000

print(f"Found {len(peers)} peer companies (plus DVN = {len(all_companies)} total)\n")
print("="*100)
print("PEER COMPANIES IN OIL & GAS E&P (Similar Market Cap)")
print("="*100)

# Display relevant columns
cols = ['ticker', 'marketcap_millions', 'pe', 'pb', 'roe', 'revenue_5y_growth', 'momentum', 'close']
display_df = all_companies[cols].copy()

# Format for display
pd.set_option('display.max_rows', None)
pd.set_option('display.width', None)
pd.set_option('display.float_format', lambda x: f'{x:,.2f}' if pd.notna(x) else 'NaN')

print(display_df.to_string(index=False))

# Calculate median P/E ratio (excluding NaN and extreme values)
pe_values = all_companies['pe'].dropna()
# Remove extreme outliers (negative and very high PE ratios)
pe_values_clean = pe_values[(pe_values > 0) & (pe_values < 100)]

print("\n" + "="*100)
print("P/E RATIO ANALYSIS")
print("="*100)
print(f"\nDVN P/E Ratio: {dvn_pe:.1f}")
print(f"\nPeer Group P/E Statistics (excluding outliers):")
print(f"  Count: {len(pe_values_clean)}")
print(f"  Median: {pe_values_clean.median():.1f}")
print(f"  Mean: {pe_values_clean.mean():.1f}")
print(f"  Min: {pe_values_clean.min():.1f}")
print(f"  Max: {pe_values_clean.max():.1f}")
print(f"  25th percentile: {pe_values_clean.quantile(0.25):.1f}")
print(f"  75th percentile: {pe_values_clean.quantile(0.75):.1f}")

print(f"\nDVN's P/E ({dvn_pe:.1f}) vs Median ({pe_values_clean.median():.1f}): ", end="")
if dvn_pe < pe_values_clean.median():
    print(f"DVN is trading at a DISCOUNT (lower P/E)")
else:
    print(f"DVN is trading at a PREMIUM (higher P/E)")

# Show all companies with their P/E ratios sorted
print("\n" + "="*100)
print("ALL COMPANIES SORTED BY P/E RATIO")
print("="*100)
valid_pe = all_companies[all_companies['pe'].notna()].copy()
valid_pe = valid_pe.sort_values('pe')
print(valid_pe[['ticker', 'pe', 'marketcap_millions', 'roe', 'revenue_5y_growth']].to_string(index=False))
