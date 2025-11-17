import pandas as pd

print("Converting data2_nov2025.parquet to Excel...")

# Load parquet file
df = pd.read_parquet('data2_nov2025.parquet')
print(f"Loaded {len(df)} rows, {len(df.columns)} columns")

# Save to Excel
df.to_excel('data2_nov2025.xlsx', index=False)
print(f"\nData saved to data2_nov2025.xlsx")

print(f"\nColumns in the file:")
for i, col in enumerate(df.columns, 1):
    print(f"{i}. {col}")
