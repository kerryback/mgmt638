# Course Instructions

## Data Query

When asked to get data from the Rice database, use the **monthly-analysis** skill or the **weekly-analysis** skill.

All information about the Rice database schema, SQL syntax, and query patterns is contained in the monthly-analysis skill and also in the weekly-analysis skill.

## Financial Ratios

When calculating any ratio with equity in the numerator or denominator:
- **ALWAYS set the ratio to NaN if equity <= 0**
- Negative or zero equity indicates financial distress and makes valuation ratios meaningless

Example:
```python
df['book_to_market'] = (df['equity'] / df['close']).round(4)
df.loc[df['equity'] <= 0, 'book_to_market'] = float('nan')
```

## Changes and Growth Rates

When calculating changes or growth rates on any dataframe that contains a 'ticker' column:
- **ALWAYS group by ticker before performing the operation**
- This ensures calculations are done separately for each ticker
- Prevents mixing data across different companies

Example:
```python
# Calculate percent change by ticker
df['return'] = df.groupby('ticker')['price'].pct_change()

# Calculate growth rate by ticker
df['revenue_growth'] = df.groupby('ticker')['revenue'].pct_change()

# Calculate lagged differences by ticker
df['price_change'] = df.groupby('ticker')['price'].diff()
```