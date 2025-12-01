# Weekly Data Skill

This skill enables Claude Code to create weekly datasets from the Rice Data Portal using ISO calendar week formatting.

## What This Skill Does

Creates weekly stock price datasets with:
- **End-of-week prices**: Last trading day in each ISO calendar week
- **ISO week labels**: YYYY-WW format (e.g., '2025-01', '2025-52')
- **Proper week alignment**: Uses Python's `isocalendar()` for consistent week numbering
- **All stocks**: Supports any number of tickers

## Setup

### 1. Prerequisites

1. **Access Token**: Get your token from [https://data-portal.rice-business.org](https://data-portal.rice-business.org)
2. **Environment File**: Create `.env` file with `RICE_ACCESS_TOKEN=your_token_here`
3. **Python Packages**: Install `requests`, `pandas`, and `python-dotenv`

See the [rice-data-query README](../rice-data-query/README.md) for detailed setup instructions.

### 2. Copy This Skill Folder

Copy this entire `weekly-analysis` folder to your `.claude/skills/` directory:

```
your-project/
├── .env                          # Your access token
├── .claude/
│   └── skills/
│       ├── rice-data-query/      # For general queries
│       ├── merge/                # For merging datasets
│       └── weekly-analysis/          # This skill folder
│           ├── SKILL.md          # Main skill file
│           ├── README.md         # This file
│           └── fetch_weekly_data.py  # Utility script
```

## Usage

### Using the Utility Script Directly

```bash
python .claude/skills/weekly-analysis/fetch_weekly_data.py AAPL,MSFT,GOOGL 2020-01-01 weekly_prices.parquet
```

**Parameters:**
- Tickers: Comma-separated list (no spaces)
- Start date: YYYY-MM-DD format
- Output file: .parquet, .xlsx, or .csv

### Asking Claude Code

Simply ask Claude to fetch weekly data:

**Example prompts:**
- "Get weekly prices for AAPL from 2020 to 2024"
- "Fetch end-of-week prices for tech stocks since 2022"
- "Create a weekly dataset for the top 10 stocks"

Claude will automatically:
1. Use the weekly-analysis skill
2. Fetch end-of-week prices using the correct SQL
3. Label weeks using ISO calendar format (YYYY-WW)
4. Save the data to your specified filename

## Output Format

The weekly dataset automatically includes these columns:

| Column | Description | Example |
|--------|-------------|---------|
| ticker | Stock ticker symbol | 'AAPL' |
| week | ISO calendar week (YYYY-WW) | '2025-01' |
| date | Actual date of end-of-week price | 2025-01-03 |
| close | Split-adjusted closing price | 187.45 |
| return | Weekly return (decimal) | 0.0250 (= 2.50%) |
| momentum | 48-week momentum (53 weeks ago to 5 weeks ago) | 0.2500 (= 25.00%) |
| lag_month | 4-week return (5 weeks ago to 1 week ago) | 0.0526 (= 5.26%) |
| lag_week | Prior week's return (decimal) | 0.0180 (= 1.80%) |
| industry | Industry classification | 'Technology Hardware' |
| sector | Sector classification | 'Technology' |
| marketcap | Market capitalization (end-of-week) | 2.85e+12 |
| size | Size category based on marketcap percentiles | 'Mega-Cap' |

**Size categories are calculated each week based on marketcap percentiles:**
- Mega-Cap: top 1.47%
- Large-Cap: next 19.93%
- Mid-Cap: next 27.14%
- Small-Cap: next 32.63%
- Micro-Cap: next 15.49%
- Nano-Cap: bottom 3.34%

**All return metrics are expressed as DECIMALS (not percentages) and rounded to 4 decimal places.**

## Understanding ISO Calendar Weeks

**ISO 8601 Week Numbering:**
- Week 1 = first week with at least 4 days in the new year
- Weeks run Monday to Sunday
- Week numbers: 01 to 52 (or 53 in long years)

**Edge Cases:**
- Early January dates may belong to prior year's last week
- Late December dates may belong to next year's first week

**Examples:**
- Jan 1, 2025 → '2025-01' (Week 1 has 5 days: Wed-Sun)
- Dec 30, 2024 → '2025-01' (Monday starts next year's Week 1)
- Dec 31, 2023 → '2023-52' (Sunday ends Week 52)

## IMPORTANT: Always Merge with Fundamentals

**When requesting fundamental data, ALWAYS merge it with weekly returns using the merge utility script.**

### Complete Workflow:

```bash
# 1. Get weekly data (this skill)
python .claude/skills/weekly-analysis/fetch_weekly_data.py AAPL,MSFT 2020-01-01 weekly_data.parquet

# 2. Get fundamentals (rice-data-query skill)
# Ask Claude: "Get pb, roe, and assets from 10Ks for AAPL and MSFT since 2020"
# This uses ARY dimension (As Reported Annual) and saves as fundamentals.parquet
# IMPORTANT: If you need growth rates (e.g., YoY asset growth), calculate them
# from the fundamental data BEFORE merging (year-to-year or quarter-to-quarter,
# NOT week-to-week or month-to-month)

# 3. MERGE (required!) - uses the weekly-specific merge script
python .claude/skills/weekly-analysis/merge_weekly_fundamentals.py weekly_data.parquet fundamentals.parquet merged_data.parquet
```

### What the Merge Does:

1. **Define isocalendar week** of the filing date (datekey)
2. **Shift data one week forward** - data filed in week 2025-01 becomes available in week 2025-02
3. **Merge on (ticker, week)** - proper alignment
4. **Forward fill fundamentals** - propagate values until next filing
5. **Shift close prices** - represent prior week's closing price

### Timing Example:

- 10K filed: Oct 30, 2020 (Friday, week 2020-44)
- Data available: Week 2020-45 (one week later)
- Forward fills: Until next 10K filing

This creates a dataset with:
- Weekly prices (close - shifted to prior week)
- Weekly returns and momentum (automatically calculated)
- Lag month and lag week metrics (automatically calculated)
- Fundamental data (properly aligned with one-week lag, forward-filled)

## Important Notes

1. **Week Labels are Strings**: e.g., '2025-01', not Period objects
2. **End-of-Week = Last Trading Day**: Usually Friday, respects market holidays
3. **Year-by-Year Queries**: Script automatically loops over years to avoid timeouts
4. **Long Years**: Some years have 53 weeks (2020, 2026, 2032, etc.)

## Troubleshooting

**Error: "RICE_ACCESS_TOKEN not found"**
- Create a `.env` file in your project directory
- Add the line: `RICE_ACCESS_TOKEN=your_token_here`
- Get your token from https://data-portal.rice-business.org

**Error: "API request failed"**
- Check your access token is valid
- Ensure you have internet connectivity
- Try with a smaller ticker list

**Unexpected week labels**
- This is normal with ISO calendar weeks
- Jan 1-3 may belong to prior year's Week 52/53
- Dec 29-31 may belong to next year's Week 01

## More Information

For database schema and query documentation:
- [Rice Data Portal Guide](https://portal-guide.rice-business.org)
- [Rice Data Portal API](https://data-portal.rice-business.org)
