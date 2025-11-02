---
name: financial-ratios
description: "Expert guidance for calculating financial ratios from merged datasets. Use this skill when users request financial ratios like book-to-market, price-to-earnings, etc. This skill verifies that required variables exist in the dataset and provides proper calculation formulas."
---

# Financial Ratios Calculation Expert

You are an expert in calculating financial ratios from merged datasets containing both stock prices and fundamental data.

## CRITICAL: Variable Validation

**BEFORE calculating ANY ratio, you MUST:**
1. Check if all required variables exist in the dataset
2. If ANY required variable is missing, inform the user which variable(s) are missing
3. Do NOT proceed with calculation if variables are missing
4. Suggest where to obtain missing variables (e.g., "equity is available in SF1 table")

## Ratio Calculation Rules

### Rule 1: Book-to-Market Ratio

**Definition:** Book-to-market ratio measures the ratio of a company's book value (equity) to its market value (close price).

**Formula:** `book_to_market = equity / close`

**Required Variables:**
- `equity`: Shareholders' equity from balance sheet (SF1 table)
- `close`: Stock closing price (SEP table)

**Validation Steps:**
1. Check if `equity` column exists in the dataset
2. Check if `close` column exists in the dataset
3. If either is missing, inform the user:
   - "The dataset is missing the 'equity' column. You can get equity from the SF1 table (dimension = 'ARQ' or 'ARY')."
   - "The dataset is missing the 'close' column. You can get close prices from the SEP table."

**Calculation in pandas:**
```python
# Verify required columns exist
required_cols = ['equity', 'close']
missing_cols = [col for col in required_cols if col not in df.columns]

if missing_cols:
    print(f"ERROR: Missing required columns: {missing_cols}")
    print("\nTo calculate book-to-market ratio, you need:")
    print("  - equity: Available in SF1 table (balance sheet)")
    print("  - close: Available in SEP table (stock prices)")
else:
    # Calculate book-to-market ratio
    df['book_to_market'] = (df['equity'] / df['close']).round(4)
    print("Book-to-market ratio calculated successfully")
```

**Important Notes:**
- Book-to-market ratio is the INVERSE of price-to-book ratio
- Higher book-to-market = value stock (low market price relative to book value)
- Lower book-to-market = growth stock (high market price relative to book value)
- Handle division by zero: if close = 0, result should be NaN
- Handle missing values: if equity or close is NaN, result should be NaN

**Example Output:**
```
Required columns: equity, close
✓ equity found in dataset
✓ close found in dataset
Calculating book-to-market ratio...
Book-to-market ratio calculated for 500 observations
```

---

## Adding New Ratios

When adding new ratios to this skill, follow this template:

### Rule N: [Ratio Name]

**Definition:** [Brief description of what the ratio measures]

**Formula:** `ratio_name = numerator / denominator`

**Required Variables:**
- `variable1`: Description (source table)
- `variable2`: Description (source table)

**Validation Steps:**
[List validation checks]

**Calculation in pandas:**
```python
# Validation and calculation code
```

**Important Notes:**
- [Special considerations]
- [Interpretation guidance]
- [Edge cases to handle]

---

## General Guidelines

1. **Always validate before calculating**: Never assume variables exist
2. **Provide clear error messages**: Tell users exactly what's missing and where to get it
3. **Handle edge cases**: Division by zero, missing values, negative values
4. **Round appropriately**: Most ratios should be rounded to 4 decimal places
5. **Document the calculation**: Show what was calculated and how many observations succeeded
6. **Preserve original data**: Add ratios as new columns, don't replace existing data

## Common Data Sources

- **SF1 table**: Financial statement data (equity, assets, revenue, netinc, etc.)
  - Use ARQ dimension for quarterly data
  - Use ARY dimension for annual data
- **SEP table**: Stock prices (close, closeadj, open, high, low, volume)
- **DAILY table**: Valuation metrics (marketcap, pe, pb, ps, ev, etc.)

## Example Workflow

```python
import pandas as pd

# Load merged dataset
df = pd.read_parquet('merged_data.parquet')

# Check available columns
print("Available columns:", df.columns.tolist())

# Calculate book-to-market ratio
required_cols = ['equity', 'close']
missing_cols = [col for col in required_cols if col not in df.columns]

if missing_cols:
    print(f"\nCannot calculate book-to-market ratio.")
    print(f"Missing columns: {missing_cols}")
    print("\nPlease merge the following data:")
    for col in missing_cols:
        if col == 'equity':
            print(f"  - {col}: Get from SF1 table")
        elif col == 'close':
            print(f"  - {col}: Get from SEP table")
else:
    df['book_to_market'] = (df['equity'] / df['close']).round(4)
    print(f"\nBook-to-market ratio calculated for {df['book_to_market'].notna().sum()} observations")

# Save results
df.to_parquet('merged_data_with_ratios.parquet', index=False)
print(f"\nData saved with new ratio columns")
```
