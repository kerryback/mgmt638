"""
Clean data5.parquet by:
1. Dropping rows with any missing data
2. Dropping rows where close < 5.00
"""
import pandas as pd

print("Loading data5.parquet...")
df = pd.read_parquet('data5.parquet')
print(f"Original: {len(df)} rows, {df['ticker'].nunique()} tickers")

# Show missing data by column
print("\nMissing data by column:")
missing = df.isnull().sum()
print(missing[missing > 0].to_string())

# Drop rows with any missing data
print("\nDropping rows with any missing data...")
df_clean = df.dropna()
print(f"After dropna: {len(df_clean)} rows ({len(df_clean)/len(df)*100:.1f}% retained)")

# Drop rows where close < 5.00
print("\nDropping rows where close < 5.00...")
df_clean = df_clean[df_clean['close'] >= 5.00]
print(f"After price filter: {len(df_clean)} rows ({len(df_clean)/len(df)*100:.1f}% of original)")

# Summary
print(f"\nFinal dataset:")
print(f"  Rows: {len(df_clean)}")
print(f"  Tickers: {df_clean['ticker'].nunique()}")
print(f"  Weeks: {df_clean['week'].nunique()}")
print(f"  Week range: {df_clean['week'].min()} to {df_clean['week'].max()}")

# Save
df_clean.to_parquet('data5.parquet', index=False)
print(f"\nSaved cleaned data to data5.parquet")

# Show sample
print("\nSample data:")
print(df_clean.head(10).to_string(index=False))
