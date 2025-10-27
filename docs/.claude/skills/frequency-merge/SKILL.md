---
name: frequency-merge
description: "Expert in merging financial data of different frequencies (daily, monthly, quarterly, annual). Use when students need to combine datasets with mismatched time intervals, such as merging daily prices with quarterly fundamentals, or monthly returns with annual financial statements."
---

# Frequency Merge Expert

## When to Use This Skill

Use this skill when students need to:
- Merge daily price data with monthly, quarterly, or annual data
- Combine quarterly fundamentals with daily valuations
- Align time series data with different sampling frequencies
- Handle forward-fill or backward-fill logic for mixed frequencies

## Key Principles

### Forward-Fill Strategy (Most Common)
When merging lower frequency data (e.g., quarterly) with higher frequency data (e.g., daily):
- Use `pd.merge_asof()` with `direction='backward'` to fill forward
- Ensures you only use information available at that point in time (no lookahead bias)

Example:
```python
# Merge daily prices with quarterly fundamentals
df_merged = pd.merge_asof(
    df_daily.sort_values('date'),
    df_quarterly.sort_values('reportperiod'),
    left_on='date',
    right_on='reportperiod',
    by='ticker',
    direction='backward'  # Use most recent past quarterly data
)
```

### Point-in-Time Considerations
- Quarterly data: Use `reportperiod` for the actual period end
- Avoid lookahead bias: Never use future fundamentals with past prices
- Filing delays: Consider using `datekey` from SF1 if you need filing dates

### Common Patterns

**Daily + Quarterly:**
```python
# Daily prices + quarterly fundamentals
pd.merge_asof(df_daily, df_quarterly, left_on='date', right_on='reportperiod', by='ticker', direction='backward')
```

**Monthly + Annual:**
```python
# Monthly returns + annual financials
pd.merge_asof(df_monthly, df_annual, left_on='date', right_on='reportperiod', by='ticker', direction='backward')
```

**Quarterly + Daily (for valuations):**
```python
# Quarterly fundamentals at quarter-end prices
pd.merge(df_quarterly, df_daily, left_on=['ticker', 'reportperiod'], right_on=['ticker', 'date'], how='left')
```

## Best Practices

1. **Always sort** both DataFrames by date/time column before merging
2. **Specify `by='ticker'`** to ensure merges happen within each stock
3. **Check for duplicates** after merging to avoid data issues
4. **Verify no lookahead bias** by checking that fundamentals align with correct dates
5. **Document the merge logic** in comments for future reference

## Example Workflow

```python
import pandas as pd

# Load data
df_prices = pd.read_parquet('daily_prices.parquet')
df_fundamentals = pd.read_parquet('quarterly_fundamentals.parquet')

# Ensure date columns are datetime
df_prices['date'] = pd.to_datetime(df_prices['date'])
df_fundamentals['reportperiod'] = pd.to_datetime(df_fundamentals['reportperiod'])

# Merge with forward-fill logic
df_merged = pd.merge_asof(
    df_prices.sort_values(['ticker', 'date']),
    df_fundamentals.sort_values(['ticker', 'reportperiod']),
    left_on='date',
    right_on='reportperiod',
    by='ticker',
    direction='backward'
)

# Save result
df_merged.to_parquet('merged_data.parquet')
print(f"Merged data saved: {len(df_merged)} rows")
```
