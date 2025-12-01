"""
Compare data5_monthly.parquet and data4.parquet row-by-row.
Drop Nov 2025 from both datasets before comparing.
"""
import pandas as pd
import numpy as np

print("Loading datasets...")
df_new = pd.read_parquet('data5_monthly.parquet')
df_old = pd.read_parquet('data4.parquet')

print(f"data5_monthly.parquet: {len(df_new):,} rows")
print(f"data4.parquet: {len(df_old):,} rows")

# Drop Nov 2025 from both
print("\nDropping November 2025...")
df_new = df_new[df_new['month'] != '2025-11']
df_old = df_old[df_old['month'] != '2025-11']

print(f"After filtering:")
print(f"  data5_monthly: {len(df_new):,} rows")
print(f"  data4: {len(df_old):,} rows")

# Sort both datasets by ticker and month for comparison
print("\nSorting datasets by ticker and month...")
df_new = df_new.sort_values(['ticker', 'month']).reset_index(drop=True)
df_old = df_old.sort_values(['ticker', 'month']).reset_index(drop=True)

# Check which (ticker, month) pairs are in one but not the other
print("\n" + "="*60)
print("CHECKING ROW COVERAGE")
print("="*60)

new_keys = set(zip(df_new['ticker'], df_new['month']))
old_keys = set(zip(df_old['ticker'], df_old['month']))

only_in_new = new_keys - old_keys
only_in_old = old_keys - new_keys
in_both = new_keys & old_keys

print(f"Rows only in data5_monthly: {len(only_in_new):,}")
print(f"Rows only in data4: {len(only_in_old):,}")
print(f"Rows in both datasets: {len(in_both):,}")

if len(only_in_new) > 0:
    print(f"\nSample rows only in data5_monthly (first 10):")
    sample_new = list(only_in_new)[:10]
    for ticker, month in sample_new:
        print(f"  {ticker:10s} {month}")

if len(only_in_old) > 0:
    print(f"\nSample rows only in data4 (first 10):")
    sample_old = list(only_in_old)[:10]
    for ticker, month in sample_old:
        print(f"  {ticker:10s} {month}")

# Compare common rows
print("\n" + "="*60)
print("COMPARING COMMON ROWS")
print("="*60)

# Merge on ticker and month
df_merged = pd.merge(
    df_new,
    df_old,
    on=['ticker', 'month'],
    how='inner',
    suffixes=('_new', '_old')
)

print(f"Common rows to compare: {len(df_merged):,}")

# Compare each column
numeric_cols = ['return', 'momentum', 'lagged_return', 'close', 'marketcap',
                'pb', 'asset_growth', 'roe', 'gp_to_assets', 'grossmargin',
                'assetturnover', 'leverage']

categorical_cols = ['sector', 'industry', 'size']

print("\nNumeric columns comparison:")
print(f"{'Column':<20s} {'Exact Match':<15s} {'Mean Diff':<15s} {'Max Diff':<15s} {'Rows Differ':<15s}")
print("-" * 80)

differences = {}

for col in numeric_cols:
    col_new = f"{col}_new"
    col_old = f"{col}_old"

    # Handle NaN values - consider NaN == NaN as match
    both_nan = df_merged[col_new].isna() & df_merged[col_old].isna()
    both_not_nan = df_merged[col_new].notna() & df_merged[col_old].notna()

    # Calculate differences only where both are not NaN
    diff = np.abs(df_merged[col_new] - df_merged[col_old])

    # Exact match: either both NaN or values are equal (within floating point tolerance)
    exact_match = both_nan | (both_not_nan & (diff < 1e-10))

    num_exact = exact_match.sum()
    pct_exact = (num_exact / len(df_merged) * 100)

    # Stats for non-matching rows
    mean_diff = diff[both_not_nan & ~exact_match].mean() if (~exact_match & both_not_nan).any() else 0
    max_diff = diff[both_not_nan].max() if both_not_nan.any() else 0

    num_differ = (~exact_match).sum()

    differences[col] = {
        'exact_match': num_exact,
        'pct_exact': pct_exact,
        'mean_diff': mean_diff,
        'max_diff': max_diff,
        'num_differ': num_differ
    }

    print(f"{col:<20s} {num_exact:>7,} ({pct_exact:5.1f}%)  {mean_diff:>12.6f}  {max_diff:>12.6f}  {num_differ:>7,}")

print("\nCategorical columns comparison:")
print(f"{'Column':<20s} {'Exact Match':<15s} {'Rows Differ':<15s}")
print("-" * 55)

for col in categorical_cols:
    col_new = f"{col}_new"
    col_old = f"{col}_old"

    exact_match = df_merged[col_new] == df_merged[col_old]
    num_exact = exact_match.sum()
    pct_exact = (num_exact / len(df_merged) * 100)
    num_differ = (~exact_match).sum()

    differences[col] = {
        'exact_match': num_exact,
        'pct_exact': pct_exact,
        'num_differ': num_differ
    }

    print(f"{col:<20s} {num_exact:>7,} ({pct_exact:5.1f}%)  {num_differ:>7,}")

# Show examples of differences
print("\n" + "="*60)
print("EXAMPLES OF DIFFERENCES")
print("="*60)

# Find rows with any differences
has_diff = pd.Series([False] * len(df_merged))
for col in numeric_cols:
    col_new = f"{col}_new"
    col_old = f"{col}_old"
    diff = np.abs(df_merged[col_new] - df_merged[col_old])
    has_diff |= (diff > 1e-10) & df_merged[col_new].notna() & df_merged[col_old].notna()

for col in categorical_cols:
    col_new = f"{col}_new"
    col_old = f"{col}_old"
    has_diff |= (df_merged[col_new] != df_merged[col_old])

num_rows_with_diff = has_diff.sum()
print(f"\nTotal rows with at least one difference: {num_rows_with_diff:,} ({num_rows_with_diff/len(df_merged)*100:.1f}%)")

if num_rows_with_diff > 0:
    print(f"\nShowing first 5 rows with differences:")
    diff_rows = df_merged[has_diff].head(5)

    for idx, row in diff_rows.iterrows():
        print(f"\n{row['ticker']} {row['month']}:")
        for col in numeric_cols + categorical_cols:
            col_new = f"{col}_new"
            col_old = f"{col}_old"
            val_new = row[col_new]
            val_old = row[col_old]

            if pd.isna(val_new) and pd.isna(val_old):
                continue
            elif pd.isna(val_new) or pd.isna(val_old):
                print(f"  {col:20s}: {val_new} (new) vs {val_old} (old)")
            elif isinstance(val_new, str):
                if val_new != val_old:
                    print(f"  {col:20s}: {val_new} (new) vs {val_old} (old)")
            else:
                diff = abs(val_new - val_old)
                if diff > 1e-10:
                    print(f"  {col:20s}: {val_new} (new) vs {val_old} (old) [diff: {diff}]")
