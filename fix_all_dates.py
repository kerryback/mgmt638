import pandas as pd
import datetime

print("Fixing dates in all data files...")

# The dates are stored as Unix timestamps in SECONDS (not the default milliseconds)
# Example: 1264723200 = 2010-01-29

# Fix monthly returns
print("\n1. Fixing monthly_returns_momentum.parquet...")
df_returns = pd.read_parquet('monthly_returns_momentum.parquet')
# The dates are stored as datetime64[ns] but with wrong values - they're actually seconds
# Extract the integer values and convert from seconds
df_returns['date_seconds'] = df_returns['date'].astype('int64')  # This gives nanoseconds
df_returns['date'] = pd.to_datetime(df_returns['date_seconds'], unit='s')
df_returns['month'] = df_returns['date'].dt.strftime('%Y-%m')
df_returns = df_returns.drop(columns=['date_seconds'])
print(f"   Fixed {len(df_returns)} rows")
print(f"   Date range: {df_returns['date'].min()} to {df_returns['date'].max()}")
df_returns.to_parquet('monthly_returns_momentum.parquet', index=False)

# Fix monthly DAILY metrics
print("\n2. Fixing monthly_daily_metrics.parquet...")
df_daily = pd.read_parquet('monthly_daily_metrics.parquet')
df_daily['date_seconds'] = df_daily['date'].astype('int64')
df_daily['date'] = pd.to_datetime(df_daily['date_seconds'], unit='s')
df_daily['month'] = df_daily['date'].dt.strftime('%Y-%m')
df_daily = df_daily.drop(columns=['date_seconds'])
print(f"   Fixed {len(df_daily)} rows")
print(f"   Date range: {df_daily['date'].min()} to {df_daily['date'].max()}")
df_daily.to_parquet('monthly_daily_metrics.parquet', index=False)

# Fix market cap
print("\n3. Fixing marketcap.parquet...")
df_mktcap = pd.read_parquet('marketcap.parquet')
df_mktcap['date_seconds'] = df_mktcap['date'].astype('int64')
df_mktcap['date'] = pd.to_datetime(df_mktcap['date_seconds'], unit='s')
df_mktcap['month'] = df_mktcap['date'].dt.strftime('%Y-%m')
df_mktcap = df_mktcap.drop(columns=['date_seconds'])
print(f"   Fixed {len(df_mktcap)} rows")
print(f"   Date range: {df_mktcap['date'].min()} to {df_mktcap['date'].max()}")
df_mktcap.to_parquet('marketcap.parquet', index=False)

print("\n4. All files fixed! Now you can re-run the merge.")
print(f"\nSample of fixed returns data:")
print(df_returns[['ticker', 'month', 'date', 'close', 'return']].head(20))
