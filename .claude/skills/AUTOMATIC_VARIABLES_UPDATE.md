# Automatic Variables Update

## Summary

Updated both weekly-analysis and monthly-analysis skills to automatically include standard variables in all datasets, even when not explicitly requested by the user.

## Automatic Variables Included

### All Datasets (Weekly and Monthly)
- **ticker**: Stock ticker symbol
- **date**: Week or month label (YYYY-WW for weekly, YYYY-MM for monthly)
- **close**: Closing price (split-adjusted)
- **return**: Period return (decimal)
- **momentum**: Long-term momentum (decimal)
- **lag_month**: Lag return metric (decimal)
  - Weekly: 4-week return from 5 weeks ago to 1 week ago
  - Monthly: Prior month's return
- **industry**: Industry classification (from TICKERS table)
- **sector**: Sector classification (from TICKERS table)
- **marketcap**: Market capitalization (end-of-period)
- **size**: Size category based on marketcap percentiles

### Weekly Only
- **lag_week**: Prior week's return (decimal)

## Size Categories

Size is calculated each period (week or month) based on marketcap percentiles:
- **Mega-Cap**: top 1.47%
- **Large-Cap**: next 19.93%
- **Mid-Cap**: next 27.14%
- **Small-Cap**: next 32.63%
- **Micro-Cap**: next 15.49%
- **Nano-Cap**: bottom 3.34%

## Files Updated

### Scripts
1. `.claude/skills/weekly-analysis/fetch_weekly_data.py`
   - Updated SQL to join with TICKERS table
   - Added marketcap to query
   - Added size calculation logic
   - Updated output columns

2. `.claude/skills/rice-data-query/fetch_monthly_data.py`
   - Updated SQL to join with TICKERS table
   - Added marketcap to query
   - Added lag_month calculation
   - Added size calculation logic
   - Updated output columns

### Documentation
3. `.claude/skills/weekly-analysis/SKILL.md`
   - Updated output columns section
   - Added size category descriptions

4. `.claude/skills/weekly-analysis/README.md`
   - Updated output format table
   - Added size category details

5. `.claude/skills/monthly-analysis/SKILL.md`
   - Updated output columns section
   - Added size category descriptions

6. `.claude/skills/monthly-analysis/README.md`
   - Updated output format table
   - Added size category details
   - Clarified which columns come from returns vs merge

## Key Implementation Details

### SQL Changes
Both scripts now join the SEP table with TICKERS table:
```sql
SELECT m.ticker, m.date, m.close, m.closeadj, m.marketcap,
       t.sector, t.industry
FROM month_ends m
LEFT JOIN tickers t ON m.ticker = t.ticker
```

### Size Calculation
Size is calculated using a percentile-based approach for each period:
```python
def assign_size(row):
    if pd.isna(row['marketcap']):
        return None
    period_data = df[df['period'] == row['period']]['marketcap']
    percentile = (period_data < row['marketcap']).sum() / len(period_data) * 100

    if percentile >= 98.53:  # Top 1.47%
        return 'Mega-Cap'
    elif percentile >= 78.60:  # Next 19.93%
        return 'Large-Cap'
    # ... etc
```

## Usage

Users no longer need to explicitly request these variables. They are automatically included in all datasets:

```bash
# Weekly data - automatically includes all variables
python .claude/skills/weekly-analysis/fetch_weekly_data.py AAPL,MSFT 2020-01-01 weekly_data.parquet

# Monthly data - automatically includes all variables
python .claude/skills/rice-data-query/fetch_monthly_data.py AAPL,MSFT 2020-01-01 monthly_data.parquet
```

## Backwards Compatibility

These changes are backwards compatible. Existing code that uses these scripts will continue to work, but will now receive additional columns automatically.
