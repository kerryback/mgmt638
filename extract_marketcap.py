import pandas as pd

print("Extracting market cap data from monthly_data.parquet...")

# Load the monthly data
df_monthly = pd.read_parquet('monthly_data.parquet')

# Extract just ticker, month, date, and marketcap
df_marketcap = df_monthly[['ticker', 'month', 'date', 'marketcap']].copy()

print(f"Extracted {len(df_marketcap)} rows")
print(f"\nFirst few rows:")
print(df_marketcap.head(20))

# Save to parquet
df_marketcap.to_parquet('marketcap.parquet', index=False)
print(f"\nMarket cap data saved to marketcap.parquet")
