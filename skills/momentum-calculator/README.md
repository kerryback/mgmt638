# Momentum Calculator Skill

Calculate stock momentum from month-end adjusted closing prices.

## Overview

This skill calculates momentum as the percentage return from 13 months ago to 2 months ago, following the methodology from Jegadeesh & Titman's momentum research.

**Momentum Formula:**
```
momentum = closeadj(t-2) / closeadj(t-13) - 1
```

## Quick Start

### 1. Prerequisites

- Python 3.x with pandas and pyarrow installed
- A parquet file with month-end prices containing columns: `ticker`, `date`, `closeadj`

### 2. Usage with Claude Code

Simply ask Claude Code to calculate momentum from your price data:

```
"Calculate momentum from my month-end prices in month_end_prices.parquet"
```

Claude will:
1. Ask you to confirm the input file path
2. Ask you for an output filename
3. Run the calculation and save results

### 3. Manual Usage

You can also run the script directly:

```bash
python .claude/skills/momentum-calculator/calculate_momentum.py input.parquet output.parquet
```

## Input Requirements

Your input parquet file must have:

| Column   | Type     | Description                    |
|----------|----------|--------------------------------|
| ticker   | string   | Stock ticker symbol            |
| date     | datetime | Month-end date                 |
| closeadj | float    | Adjusted closing price         |

**Important:**
- Data should be month-end prices (last trading day of each month)
- At least 13 months of history per ticker is needed for momentum calculation
- The script will automatically sort by ticker and date

## Output Format

The output parquet file contains:

| Column    | Type          | Description                          |
|-----------|---------------|--------------------------------------|
| ticker    | string        | Stock ticker symbol                  |
| month     | Period('M')   | Month in YYYY-MM format             |
| closeadj  | float         | Adjusted closing price              |
| momentum  | float         | Momentum value (percentage return)  |

**Notes:**
- The `month` column uses pandas Period format (not string)
- Rows with missing momentum values (first 13 months) are dropped
- Period format allows easy sorting, filtering, and date arithmetic

## Example

```python
# Input data (month_end_prices.parquet):
ticker  date        closeadj
AAPL    2020-01-31  74.757
AAPL    2020-02-28  66.185
...
AAPL    2021-02-26  121.260  # t-13
...
AAPL    2021-12-31  177.570  # t-2
AAPL    2022-01-31  174.780  # t-1
AAPL    2022-02-28  165.120  # t

# Output data (momentum.parquet):
ticker  month    closeadj  momentum
AAPL    2021-02  121.260   NaN       # (dropped - no data 13 months prior)
...
AAPL    2022-02  165.120   0.4647    # (177.570 / 121.260) - 1 = 46.47% return
```

## Why Period Format?

The skill uses pandas `Period('M')` for monthly dates because:

1. **Native pandas support** - designed for time period data
2. **Chronological sorting** - automatically sorts correctly
3. **Easy arithmetic** - can add/subtract months easily
4. **Type safety** - prevents format inconsistencies
5. **Efficient storage** - more compact than strings in parquet

Period values display as `2021-06` but retain full time intelligence.

## Momentum Methodology

The 2-13 month momentum calculation:

- **Skip recent month (t-2 vs t-1)**: Avoids short-term reversal effects and microstructure noise
- **12-month lookback (t-13)**: Standard momentum period used in academic research
- **Monthly rebalancing**: Suitable for institutional and retail portfolios

This matches the methodology in:
- Jegadeesh & Titman (1993, 2001)
- Fama & French momentum factor (MOM)

## Files in This Skill

```
momentum-calculator/
├── SKILL.md                  # Skill definition for Claude
├── README.md                 # This file
└── calculate_momentum.py     # Python script that does the calculation
```

## Troubleshooting

**Error: "Missing required columns"**
- Ensure your parquet file has columns: ticker, date, closeadj
- Column names are case-sensitive

**Error: "Input file not found"**
- Check the file path is correct
- Use absolute path if relative path doesn't work

**Warning: "Many NaN values in momentum"**
- Normal for first 13 months of each ticker
- These rows are automatically dropped
- Ensure you have at least 13 months of data

## Dependencies

```bash
pip install pandas pyarrow
```

These are typically already installed if you're working with parquet files from the Rice Data Portal.
