import pandas as pd

df = pd.read_excel('data2_nov2025.xlsx')
max_row = df.loc[df['marketcap'].idxmax()]

print(f"Largest Market Cap in November 2025:")
print(f"=====================================")
print(f"Ticker: {max_row['ticker']}")
print(f"Market Cap: ${max_row['marketcap']:,.0f} thousand")
print(f"Market Cap: ${max_row['marketcap']/1000:,.2f} million")
print(f"Market Cap: ${max_row['marketcap']/1_000_000:,.2f} billion")
print(f"Close Price: ${max_row['close']:.2f}")
print(f"Industry: {max_row['industry']}")
print(f"P/E Ratio: {max_row['pe']:.2f}" if pd.notna(max_row['pe']) else "P/E Ratio: N/A")
