---
name: momentum-calculator
description: "Calculate stock momentum from month-end prices. Use this skill when users want to calculate momentum from a parquet file of month-end adjusted closing prices. This skill runs a Python script that computes momentum as closeadj.shift(2)/closeadj.shift(13) - 1."
---

# Momentum Calculator

This skill calculates stock momentum from month-end adjusted closing prices stored in a parquet file.

## What This Skill Does

Given a parquet file with month-end prices (columns: ticker, date, closeadj), this skill:

1. Reads the parquet file
2. Sorts data by ticker and date
3. Calculates momentum for each ticker as: **(price 2 months ago / price 13 months ago) - 1**
   - `closeadj.shift(2) / closeadj.shift(13) - 1`
4. Converts dates to monthly period format (e.g., `2021-06`)
5. Prompts user for output filename
6. Saves results as parquet file with columns: ticker, month, closeadj, momentum

## Momentum Calculation

The momentum measure used is:

```
momentum = closeadj(t-2) / closeadj(t-13) - 1
```

Where:
- `t` is the current month
- `t-2` is 2 months ago (skip most recent month to avoid microstructure effects)
- `t-13` is 13 months ago (12-month lookback + 1 month skip)
- The result is expressed as a decimal return (e.g., 0.25 = 25% return)

This is a standard momentum measure used in academic research (Jegadeesh & Titman).

## How to Use This Skill

When a user requests momentum calculation:

1. **Ask for the input file path**: "What is the path to your month-end prices parquet file?"
2. **Validate the file exists** and has required columns (ticker, date, closeadj)
3. **Ask for the output filename**: "What filename would you like for the momentum data? (e.g., 'momentum_2020_2025.parquet')"
4. **Run the calculation script**:
   ```python
   import subprocess
   import os

   # Get the script path (in the same directory as this SKILL.md)
   script_dir = os.path.dirname(__file__)
   script_path = os.path.join(script_dir, 'calculate_momentum.py')

   # Run the script
   result = subprocess.run(
       ['python', script_path, input_file, output_file],
       capture_output=True,
       text=True
   )

   if result.returncode == 0:
       print(result.stdout)
   else:
       print(f"Error: {result.stderr}")
   ```
5. **Confirm completion** and show summary statistics

## Required Input Format

The input parquet file must have these columns:
- **ticker**: Stock ticker symbol (string)
- **date**: Date in datetime format
- **closeadj**: Adjusted closing price (float)

The data should be:
- Month-end prices (last trading day of each month)
- Sorted by ticker and date (the script will sort if needed)
- At least 13 months of history per ticker for momentum calculation

## Output Format

The output parquet file contains:
- **ticker**: Stock ticker symbol
- **month**: Monthly period in format YYYY-MM (pandas Period type)
- **closeadj**: Adjusted closing price for that month
- **momentum**: Calculated momentum value (price(t-2) / price(t-13) - 1)

Rows with missing momentum values (first 13 months per ticker) are dropped.

## Example Usage

```python
# User has a file 'month_end_prices.parquet' with AAPL, MSFT, GOOGL prices
# The skill would:

# 1. Ask: "What is the path to your month-end prices parquet file?"
#    User: "month_end_prices.parquet"

# 2. Ask: "What filename would you like for the momentum data?"
#    User: "momentum_data.parquet"

# 3. Run calculation and show results:
#    Reading data from month_end_prices.parquet...
#    Calculating momentum for 3 tickers...
#    Saving 180 rows to momentum_data.parquet...
#
#    Summary:
#      Tickers: 3
#      Date range: 2021-02 to 2025-10
#      Total rows: 180
```

## Technical Notes

1. **Period format**: Dates are converted to pandas Period('M') format
   - More efficient than strings
   - Supports chronological sorting
   - Easy to work with in pandas

2. **Missing values**: The first 13 months of data for each ticker will have NaN momentum values and are dropped

3. **Grouping**: Calculations are done per ticker using `groupby('ticker')` to ensure shift operations work correctly

4. **Performance**: Efficient for datasets with thousands of tickers and many years of monthly data

## Dependencies

- pandas
- pyarrow (for parquet support)

These should already be installed if the user is working with parquet files.
