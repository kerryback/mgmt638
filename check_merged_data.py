import pandas as pd

print("Checking merged data...")

# Load the final merged data
df_final = pd.read_parquet('final_merged_data.parquet')
print(f"Final merged data: {len(df_final)} rows")
print(f"Unique tickers: {df_final['ticker'].nunique()}")
print(f"Columns: {df_final.columns.tolist()}")

print(f"\nFirst 50 rows:")
print(df_final.head(50))

print(f"\nChecking for duplicates:")
print(f"Duplicate (ticker, month) pairs: {df_final.duplicated(['ticker', 'month']).sum()}")

print(f"\nSample data for ticker 'A':")
print(df_final[df_final['ticker'] == 'A'].head(30))
