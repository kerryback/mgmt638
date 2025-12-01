# Monthly Analysis Skill

This skill enables Claude Code to perform complete monthly stock analysis, including fetching monthly returns and merging with fundamental data.

## What This Skill Does

Provides a complete monthly analysis workflow:
- **Fetch end-of-month prices** from Rice Data Portal
- **Calculate monthly returns** and momentum automatically
- **Merge with fundamental data** from 10K/10Q filings
- **Proper timing** to avoid look-ahead bias

## Setup

### Prerequisites

This skill uses scripts from the rice-data-query and merge skills:

1. **Access Token**: Get your token from [https://data-portal.rice-business.org](https://data-portal.rice-business.org)
2. **Environment File**: Create `.env` file with `RICE_ACCESS_TOKEN=your_token_here`
3. **Python Packages**: Install `requests`, `pandas`, and `python-dotenv`

See the [rice-data-query README](../rice-data-query/README.md) for detailed setup instructions.

## Usage

### Using the Utility Scripts Directly

```bash
# 1. Fetch monthly returns
python .claude/skills/rice-data-query/fetch_monthly_data.py AAPL,MSFT 2020-01-01 monthly_returns.parquet

# 2. Fetch fundamentals
python .claude/skills/rice-data-query/rice_sf1_query.py AAPL,MSFT pb,roe,assets ARY 2020-01-01 fundamentals.parquet

# 3. Merge (required!)
python .claude/skills/merge/merge_returns_fundamentals.py monthly_returns.parquet fundamentals.parquet merged.parquet --frequency monthly
```

### Asking Claude Code

Simply ask Claude to perform monthly analysis:

**Example prompts:**
- "Get monthly returns for AAPL from 2020 to 2024 and merge with fundamentals"
- "Fetch monthly data for tech stocks with pb and roe from 10Ks"
- "Create a monthly analysis dataset for the top 10 stocks"

Claude will automatically:
1. Fetch monthly returns using the utility script
2. Fetch fundamental data from 10Ks or 10Qs
3. Calculate any growth rates BEFORE merging
4. Merge the datasets with proper timing
5. Save the final merged dataset

## Output Format

The monthly returns dataset automatically includes these columns:

| Column | Description | Example |
|--------|-------------|---------|
| ticker | Stock ticker symbol | 'AAPL' |
| month | Month (YYYY-MM) | '2025-01' |
| date | Actual date of end-of-month | 2025-01-31 |
| close | Closing price (split-adjusted) | 187.45 |
| return | Monthly return (decimal) | 0.0350 (= 3.50%) |
| momentum | 12-month momentum (decimal) | 0.2500 (= 25.00%) |
| lag_month | Prior month's return (decimal) | 0.0280 (= 2.80%) |
| industry | Industry classification | 'Technology Hardware' |
| sector | Sector classification | 'Technology' |
| marketcap | Market capitalization (end-of-month) | 2.85e+12 |
| size | Size category based on marketcap percentiles | 'Mega-Cap' |

**Size categories are calculated each month based on marketcap percentiles:**
- Mega-Cap: top 1.47%
- Large-Cap: next 19.93%
- Mid-Cap: next 27.14%
- Small-Cap: next 32.63%
- Micro-Cap: next 15.49%
- Nano-Cap: bottom 3.34%

After merging with fundamentals, additional columns are added:
- pb, roe, assets, and any other requested fundamental variables
- `close` is shifted to represent prior month's closing price
- `date` is dropped from the final output

**All return metrics are expressed as DECIMALS (not percentages) and rounded to 4 decimal places.**

## Timing and Date Alignment

**Critical for avoiding look-ahead bias:**

1. **Filing Date**: 10K filed on Oct 30, 2020
2. **Available Month**: Data becomes available in '2020-11' (November 2020)
3. **Forward Fill**: Fundamental data propagates until next filing
4. **Close Price**: Shifted to represent prior month (known at start of current month)

**Example (November 2010):**
- `close = 10.749` → October 2010 closing price (known at start of Nov)
- `return = 0.0339` → November 2010 return
- `momentum = 0.2150` → 12-month momentum as of November
- `pb = 28.326`, `roe = 0.752` → From 10-K filed Oct 27, 2010 (available starting Nov)

## IMPORTANT: Calculate Growth Rates BEFORE Merging

**When requesting fundamental data, if you need growth rates:**
1. Calculate them from the fundamental data BEFORE merging
2. Growth should be year-to-year (ARY) or quarter-to-quarter (ARQ)
3. DO NOT calculate growth after merging (will be zero due to forward-fill)

**Example:**
```python
# BEFORE merging: Calculate YoY growth from fundamental data
df_fund['assets_yoy_growth_pct'] = (
    df_fund.groupby('ticker')['assets'].pct_change() * 100
).round(2)
# THEN merge with monthly data
```

## Integration with Other Skills

**Complete Workflow:**
1. Use **rice-data-query** to fetch monthly returns and fundamentals
2. Calculate growth rates if needed (on fundamental data)
3. Use **merge** skill to combine datasets
4. Use **monthly-analysis** skill for the complete workflow

## Important Notes

1. **Month Labels are Strings**: e.g., '2025-01', not Period objects
2. **End-of-Month = Last Trading Day**: Respects market holidays
3. **Year-by-Year Queries**: Script automatically loops over years to avoid timeouts
4. **Always Merge**: Don't skip the merge step - ensures proper timing

## More Information

For database schema and query documentation:
- [Rice Data Portal Guide](https://portal-guide.rice-business.org)
- [Rice Data Portal API](https://data-portal.rice-business.org)
