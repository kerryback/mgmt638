import pandas as pd

print("Fixing month column in returns data...")

# Load returns data
df_returns = pd.read_parquet('monthly_returns_momentum.parquet')

print(f"\nOriginal data:")
print(f"Rows: {len(df_returns)}")
print(f"Date column dtype: {df_returns['date'].dtype}")
print(f"Month column dtype: {df_returns['month'].dtype}")
print(f"\nFirst 20 rows:")
print(df_returns[['ticker', 'month', 'date', 'close']].head(20))

# The issue is that dates are Unix timestamps (nanoseconds since 1970)
# Let me convert them properly
df_returns['date'] = pd.to_datetime(df_returns['date'], unit='ns')

# Recreate month column
df_returns['month'] = df_returns['date'].dt.strftime('%Y-%m')

print(f"\nFixed data:")
print(f"Date column dtype: {df_returns['date'].dtype}")
print(f"Month column dtype: {df_returns['month'].dtype}")
print(f"\nFirst 20 rows:")
print(df_returns[['ticker', 'month', 'date', 'close']].head(20))

# Save fixed data
df_returns.to_parquet('monthly_returns_momentum_fixed.parquet', index=False)
print(f"\nFixed data saved to monthly_returns_momentum_fixed.parquet")
