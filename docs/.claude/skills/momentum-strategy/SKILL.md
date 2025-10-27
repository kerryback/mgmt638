---
name: momentum-strategy
description: "Expert in constructing momentum trading strategies and factor portfolios. Use when students need to calculate momentum signals, form portfolios based on past returns, implement ranking strategies, or analyze momentum factor performance."
---

# Momentum Strategy Expert

## When to Use This Skill

Use this skill when students need to:
- Calculate momentum signals (past returns over various windows)
- Form momentum portfolios (winners vs losers)
- Implement portfolio sorting strategies
- Backtest momentum trading strategies
- Analyze momentum factor returns

## Core Momentum Calculations

### Simple Momentum Signal
Most common: 12-month momentum skipping the most recent month

```python
import pandas as pd

# Calculate 12-month momentum (t-12 to t-2)
df = df.sort_values(['ticker', 'date'])
df['ret'] = df.groupby('ticker')['closeadj'].pct_change()

# 12-month cumulative return skipping most recent month
df['momentum'] = df.groupby('ticker')['ret'].transform(
    lambda x: (1 + x).shift(1).rolling(11).apply(lambda y: y.prod() - 1, raw=True)
)
```

### Alternative Momentum Specifications
- **6-month momentum**: `rolling(6)`
- **3-month momentum**: `rolling(3)`
- **12-month with recent month**: `rolling(12)` without shift

## Portfolio Formation

### Quintile Portfolios

```python
# Rank stocks into quintiles each month
df['momentum_rank'] = df.groupby('date')['momentum'].transform(
    lambda x: pd.qcut(x, 5, labels=False, duplicates='drop')
)

# Calculate equal-weighted portfolio returns
portfolio_returns = df.groupby(['date', 'momentum_rank'])['ret'].mean()

# Long-short strategy
long_short = portfolio_returns.xs(4, level='momentum_rank') - portfolio_returns.xs(0, level='momentum_rank')
```

### Decile Portfolios

```python
# Rank stocks into deciles
df['momentum_rank'] = df.groupby('date')['momentum'].transform(
    lambda x: pd.qcut(x, 10, labels=False, duplicates='drop')
)
```

## Strategy Implementation Steps

1. **Calculate past returns** over formation period
2. **Rank stocks** based on momentum signal
3. **Form portfolios** (equal-weighted or value-weighted)
4. **Hold period** (typically 1 month)
5. **Rebalance** monthly
6. **Calculate strategy returns**

## Example End-to-End Workflow

```python
import pandas as pd
import numpy as np

# Load monthly returns data
df = pd.read_parquet('monthly_returns.parquet')
df = df.sort_values(['ticker', 'date'])

# Calculate momentum signal (12-2 months)
df['ret'] = df.groupby('ticker')['closeadj'].pct_change()
df['momentum'] = df.groupby('ticker')['ret'].transform(
    lambda x: (1 + x).shift(1).rolling(11).apply(lambda y: y.prod() - 1, raw=True)
)

# Remove NaN momentum values
df = df.dropna(subset=['momentum'])

# Rank into quintiles each month
df['quintile'] = df.groupby('date')['momentum'].transform(
    lambda x: pd.qcut(x, 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'], duplicates='drop')
)

# Calculate equal-weighted quintile returns
quintile_returns = df.groupby(['date', 'quintile'])['ret'].mean().unstack()

# Long-short momentum strategy
quintile_returns['Long-Short'] = quintile_returns['Q5'] - quintile_returns['Q1']

# Calculate cumulative returns
cumulative_returns = (1 + quintile_returns).cumprod()

# Performance metrics
sharpe_ratio = quintile_returns['Long-Short'].mean() / quintile_returns['Long-Short'].std() * np.sqrt(12)
print(f"Momentum Long-Short Sharpe Ratio: {sharpe_ratio:.2f}")

# Save results
quintile_returns.to_parquet('momentum_quintile_returns.parquet')
cumulative_returns.to_parquet('momentum_cumulative_returns.parquet')
```

## Common Pitfalls to Avoid

1. **Lookahead bias**: Don't use future returns in signal calculation
2. **Survivorship bias**: Include delisted stocks if available
3. **Microstructure issues**: Skip most recent month to avoid bid-ask bounce
4. **Missing data**: Handle NaNs appropriately (dropna vs fillna)
5. **Transaction costs**: Remember momentum strategies trade frequently

## Performance Analysis

```python
# Calculate strategy statistics
returns = df['Long-Short']
mean_return = returns.mean() * 12  # Annualized
volatility = returns.std() * np.sqrt(12)  # Annualized
sharpe = mean_return / volatility
max_dd = (returns.cumsum() - returns.cumsum().cummax()).min()

print(f"Annualized Return: {mean_return:.2%}")
print(f"Annualized Volatility: {volatility:.2%}")
print(f"Sharpe Ratio: {sharpe:.2f}")
print(f"Max Drawdown: {max_dd:.2%}")
```
