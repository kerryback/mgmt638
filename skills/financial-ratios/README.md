# Financial Ratios Skill

Expert guidance for calculating financial ratios from merged datasets containing stock prices and fundamental data.

## What This Skill Does

This skill helps you calculate common financial ratios used in equity analysis and portfolio construction. It:

- **Validates data availability**: Checks that required variables exist before attempting calculations
- **Provides clear formulas**: Shows exactly how each ratio is calculated
- **Handles edge cases**: Properly manages division by zero, missing values, and negative values
- **Suggests data sources**: Tells you where to get missing variables from the Rice Data Portal

## Currently Supported Ratios

### Book-to-Market Ratio
- **Formula**: equity / close
- **Required data**: equity (from SF1), close (from SEP)
- **Use case**: Value investing, Fama-French factor construction
- **Interpretation**: Higher ratio = value stock, Lower ratio = growth stock

## How to Use This Skill

### Basic Usage

When you need to calculate a financial ratio:

```
"Calculate book-to-market ratio for my dataset"
```

Claude will:
1. Check if your dataset has the required variables (equity and close)
2. If missing, tell you which variables are missing and where to get them
3. If present, calculate the ratio and add it as a new column
4. Show summary statistics of the calculated ratio

### Example Workflow

```
User: "I have a file with weekly returns and equity. Calculate book-to-market."

Claude: "I'll check if your dataset has the required variables for book-to-market ratio..."

Claude: "✗ Missing 'close' column. Book-to-market requires:
  - equity (found ✓)
  - close (missing ✗)

You can get close prices from the SEP table in the Rice Data Portal.
Would you like me to help you fetch close prices and merge them with your data?"
```

### With Complete Data

```
User: "Calculate book-to-market for aapl_msft_merged.parquet"

Claude: "✓ All required columns found (equity, close)
Calculating book-to-market ratio...

Book-to-market ratio calculated for 433 observations

Summary statistics:
  Mean: 0.1245
  Median: 0.1189
  Min: 0.0823
  Max: 0.2156

Data saved to aapl_msft_merged.parquet with new 'book_to_market' column"
```

## Requirements

- Python 3.x
- pandas library
- Merged dataset containing required variables for the ratio you want to calculate

## Data Sources

Variables for financial ratios typically come from:

- **SF1 table** (Rice Data Portal): Financial statement data
  - equity, assets, revenue, netinc, debt, etc.
  - Use ARQ dimension for quarterly data
  - Use ARY dimension for annual data

- **SEP table** (Rice Data Portal): Stock prices
  - close, closeadj, open, high, low, volume

- **DAILY table** (Rice Data Portal): Daily valuation metrics
  - marketcap, pe, pb, ps, ev, evebit, evebitda

## Future Ratios

This skill will be expanded to include:
- Price-to-Earnings (P/E)
- Price-to-Book (P/B)
- Debt-to-Equity (D/E)
- Return on Equity (ROE)
- Return on Assets (ROA)
- Current Ratio
- Quick Ratio
- And more...

## Tips

1. **Check your data first**: Use `df.columns.tolist()` to see what variables you have
2. **Merge before calculating**: Make sure you've merged price data with fundamental data
3. **Handle missing values**: The skill will preserve NaN values appropriately
4. **Understand the timing**: Make sure price and fundamental data are properly aligned (avoid look-ahead bias)

## Getting Help

If you encounter issues:
1. Check that you're using the rice-data-query skill to fetch data
2. Verify you've merged price and fundamental data correctly
3. Ensure you're using the merge skill for proper date alignment
4. Ask Claude Code to explain the ratio and its interpretation

## Installation

This skill is located in `.claude/skills/financial-ratios/`

To use it, simply ask Claude Code to calculate a financial ratio. Claude will automatically invoke this skill when needed.
