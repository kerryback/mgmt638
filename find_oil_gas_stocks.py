import pandas as pd

print("Finding mid-cap oil & gas stocks in November 2025...\n")

# Load November 2025 data
df = pd.read_excel('data2_nov2025.xlsx')

# Filter for oil & gas related industries
oil_gas_industries = [
    'Oil & Gas E&P',
    'Oil & Gas Equipment & Services',
    'Oil & Gas Integrated',
    'Oil & Gas Midstream',
    'Oil & Gas Refining & Marketing'
]

df_oil = df[df['industry'].isin(oil_gas_industries)].copy()

print(f"Total oil & gas stocks: {len(df_oil)}\n")

# Mid-cap typically: $2B - $10B market cap
# Market cap in the data is in thousands, so:
# Mid-cap: 2,000,000 - 10,000,000 (thousands)
df_oil['marketcap_billions'] = df_oil['marketcap'] / 1_000_000

df_midcap = df_oil[(df_oil['marketcap_billions'] >= 2) &
                    (df_oil['marketcap_billions'] <= 10)].copy()

print(f"Mid-cap oil & gas stocks (${2}B - ${10}B): {len(df_midcap)}\n")

# Sort by market cap
df_midcap = df_midcap.sort_values('marketcap_billions', ascending=False)

# Show relevant columns
cols = ['ticker', 'close', 'marketcap_billions', 'industry',
        'pe', 'pb', 'roe', 'revenue', 'equity', 'debt',
        'revenue_5y_growth', 'momentum', 'return']

print("Mid-Cap Oil & Gas Stocks:")
print("="*100)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 30)
print(df_midcap[cols].to_string(index=False))

# Show detailed info for a few good candidates
print("\n\n" + "="*100)
print("RECOMMENDED STOCKS FOR VALUATION:")
print("="*100)

# Filter for stocks with complete fundamental data
df_complete = df_midcap[
    df_midcap['revenue'].notna() &
    df_midcap['equity'].notna() &
    df_midcap['pe'].notna() &
    df_midcap['roe'].notna()
].copy()

print(f"\nStocks with complete fundamental data: {len(df_complete)}\n")

for i, row in df_complete.head(5).iterrows():
    print(f"\n{row['ticker']} - {row['industry']}")
    print(f"  Market Cap: ${row['marketcap_billions']:.2f}B")
    print(f"  Price: ${row['close']:.2f}")
    print(f"  P/E: {row['pe']:.1f}")
    print(f"  P/B: {row['pb']:.2f}")
    print(f"  ROE: {row['roe']:.2f}%")
    print(f"  Revenue: ${row['revenue']/1e9:.2f}B")
    print(f"  Equity: ${row['equity']/1e9:.2f}B")
    print(f"  Debt/Equity: {(row['debt']/row['equity']):.2f}")
    print(f"  5Y Revenue Growth: {row['revenue_5y_growth']*100:.1f}%")
    print(f"  Momentum: {row['momentum']*100:.1f}%")
    print(f"  Nov 2025 Return: {row['return']*100:.1f}%")
