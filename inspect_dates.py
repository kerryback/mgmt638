import pandas as pd

# Load the data
df = pd.read_parquet('monthly_returns_momentum.parquet')

print("Investigating date issue...")
print(f"\nDate column info:")
print(f"dtype: {df['date'].dtype}")
print(f"Min: {df['date'].min()}")
print(f"Max: {df['date'].max()}")

# Show the actual integer values
print(f"\nFirst few date values as integers:")
df['date_int'] = df['date'].astype('int64')
print(df[['ticker', 'month', 'date', 'date_int']].head(20))

# Try to figure out what unit these are in
# The API said we queried from 2010-01-01, so let's see what that would be
import datetime
jan_2010 = datetime.datetime(2010, 1, 1)
jan_2010_ns = int(jan_2010.timestamp() * 1e9)
print(f"\n2010-01-01 in nanoseconds: {jan_2010_ns}")

# Check if dates are actually epoch days
print(f"\nChecking if dates are epoch days:")
df['date_from_days'] = pd.to_datetime(df['date_int'], unit='D', origin='unix')
print(df[['ticker', 'date', 'date_int', 'date_from_days']].head(20))
