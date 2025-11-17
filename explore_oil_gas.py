import pandas as pd
import numpy as np

print("Exploring oil & gas stocks in November 2025...\n")

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
df_oil['marketcap_billions'] = df_oil['marketcap'] / 1_000_000

print(f"Total oil & gas stocks: {len(df_oil)}\n")

# Show market cap distribution
print("Market Cap Distribution:")
print(df_oil['marketcap_billions'].describe())
print()

# Show all stocks sorted by market cap
print("\nAll Oil & Gas Stocks (sorted by market cap):")
print("="*120)

# Filter for stocks with complete data
df_complete = df_oil[
    df_oil['revenue'].notna() &
    df_oil['equity'].notna() &
    df_oil['marketcap_billions'].notna()
].copy()

df_complete = df_complete.sort_values('marketcap_billions', ascending=False)

cols = ['ticker', 'close', 'marketcap_billions', 'industry',
        'pe', 'pb', 'roe', 'revenue_5y_growth', 'momentum']

pd.set_option('display.max_rows', 50)
print(df_complete[cols].to_string(index=False))

# Find stocks in $500M - $5B range (small to mid-cap)
print("\n\n" + "="*120)
print("STOCKS IN $500M - $5B RANGE (Good for valuation exercise):")
print("="*120)

df_target = df_complete[(df_complete['marketcap_billions'] >= 0.5) &
                        (df_complete['marketcap_billions'] <= 5)].copy()

print(f"\nFound {len(df_target)} stocks\n")

for i, row in df_target.head(10).iterrows():
    print(f"\n{row['ticker']} - {row['industry']}")
    print(f"  Market Cap: ${row['marketcap_billions']:.2f}B")
    print(f"  Price: ${row['close']:.2f}")
    print(f"  P/E: {row['pe']:.1f}" if pd.notna(row['pe']) else "  P/E: N/A")
    print(f"  P/B: {row['pb']:.2f}" if pd.notna(row['pb']) else "  P/B: N/A")
    print(f"  ROE: {row['roe']:.1f}%" if pd.notna(row['roe']) else "  ROE: N/A")
    if pd.notna(row['revenue_5y_growth']):
        print(f"  5Y Revenue Growth: {row['revenue_5y_growth']*100:.1f}%")
    if pd.notna(row['momentum']):
        print(f"  Momentum: {row['momentum']*100:.1f}%")
