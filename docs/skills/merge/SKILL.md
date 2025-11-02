---
name: merge
description: "Expert in merging financial datasets with different frequencies and alignment requirements. Use when students need to combine weekly returns with SF1 fundamentals, or other datasets requiring careful date alignment."
---

# Financial Data Merge Expert

You are an expert in merging financial datasets with different time frequencies and alignment requirements.

## MERGING WEEKLY RETURNS WITH SF1 FUNDAMENTALS

When merging weekly return data with SF1 fundamental data, proper date alignment is critical to avoid look-ahead bias.

### Rule 1: SF1 Date Alignment for Weekly Data

**CRITICAL**: SF1 fundamental data filed on `datekey` should become available starting with the first Monday AFTER the filing date.

**Implementation**:

```python
# After getting SF1 data with datekey
df_sf1['datekey'] = pd.to_datetime(df_sf1['datekey'])

# Find the next Monday that is STRICTLY after datekey
# Calculate days until next Monday (0 = Monday, 6 = Sunday)
days_since_monday = df_sf1['datekey'].dt.weekday
days_until_next_monday = 7 - days_since_monday

df_sf1['week_start'] = df_sf1['datekey'] + pd.to_timedelta(days_until_next_monday, unit='D')
```

**Examples**:
- If datekey is Monday (weekday=0): week_start is 7 days later (next Monday)
- If datekey is Tuesday (weekday=1): week_start is 6 days later (next Monday)
- If datekey is Friday (weekday=4): week_start is 3 days later (next Monday)
- If datekey is Sunday (weekday=6): week_start is 1 day later (next Monday)

### Rule 2: Weekly Returns Date Preparation

The weekly returns data from rice-data-query skill has:
- `date`: The end-of-week date (typically Friday or last trading day)
- `week`: Period format string (e.g., '2023-01-02/2023-01-08')

**Create a week_start column for merging**:

```python
# The 'date' column is the end-of-week
# Create week_start as the Monday of that week
df_weekly['week_start'] = df_weekly['date'] - pd.to_timedelta(
    df_weekly['date'].dt.weekday, unit='D'
)
```

### Rule 3: Performing the Merge

```python
# Merge on ticker and week_start
df_merged = pd.merge(
    df_weekly,
    df_sf1,
    on=['ticker', 'week_start'],
    how='left'  # Keep all weekly observations
)

# Forward fill fundamental data within each ticker
# This carries forward the most recent fundamental values
df_merged = df_merged.sort_values(['ticker', 'week_start'])
fund_columns = [col for col in df_sf1.columns if col not in ['ticker', 'datekey', 'week_start']]
df_merged[fund_columns] = df_merged.groupby('ticker')[fund_columns].ffill()
```

**Important Notes**:
- The `how='left'` ensures all weekly return observations are kept
- Forward filling propagates fundamental data to subsequent weeks until the next filing
- Always sort by ticker and date before forward filling
- This approach ensures no look-ahead bias (fundamentals only available after filing)

## FUTURE MERGE PATTERNS

Additional merge patterns will be added here for:
- Monthly returns with quarterly fundamentals
- Daily data with monthly fundamentals
- Cross-sectional merges with company characteristics

