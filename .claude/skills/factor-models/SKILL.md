---
name: factor-models
description: "Expert in factor modeling, including Fama-French factors, quality factors, value factors, and multi-factor portfolio analysis. Use when students need to construct factor portfolios, run factor regressions, analyze factor exposures, or implement systematic equity strategies."
---

# Factor Models Expert

## When to Use This Skill

Use this skill when students need to:
- Construct factor portfolios (size, value, quality, profitability, etc.)
- Run factor regressions (CAPM, Fama-French 3-factor, 5-factor, etc.)
- Calculate factor loadings and exposures
- Analyze factor returns and performance
- Build multi-factor systematic strategies
- Perform risk attribution

## Common Factors

### Size Factor (SMB - Small Minus Big)
Based on market capitalization

```python
# Rank by market cap and form portfolios
df['size_rank'] = df.groupby('date')['marketcap'].transform(
    lambda x: pd.qcut(x, 2, labels=['Small', 'Big'], duplicates='drop')
)

# Calculate SMB factor return
smb = df.groupby(['date', 'size_rank'])['ret'].mean().unstack()
smb['SMB'] = smb['Small'] - smb['Big']
```

### Value Factor (HML - High Minus Low)
Based on book-to-market ratio

```python
# Calculate book-to-market
df['bm'] = df['equity'] / (df['marketcap'] * 1000)  # marketcap in thousands

# Rank by B/M
df['value_rank'] = df.groupby('date')['bm'].transform(
    lambda x: pd.qcut(x, 3, labels=['Low', 'Med', 'High'], duplicates='drop')
)

# Calculate HML factor return
hml = df.groupby(['date', 'value_rank'])['ret'].mean().unstack()
hml['HML'] = hml['High'] - hml['Low']
```

### Quality Factor (QMJ - Quality Minus Junk)
Based on profitability, growth, and safety metrics

```python
# Composite quality score
df['quality'] = (
    df['roe'].rank(pct=True) +
    df['roa'].rank(pct=True) +
    df['grossmargin'].rank(pct=True) -
    df['de'].rank(pct=True)  # Lower debt-to-equity is better
) / 4

# Rank by quality
df['quality_rank'] = df.groupby('date')['quality'].transform(
    lambda x: pd.qcut(x, 3, labels=['Junk', 'Med', 'Quality'], duplicates='drop')
)

# Calculate QMJ factor return
qmj = df.groupby(['date', 'quality_rank'])['ret'].mean().unstack()
qmj['QMJ'] = qmj['Quality'] - qmj['Junk']
```

### Profitability Factor (RMW - Robust Minus Weak)
Based on operating profitability

```python
# Operating profitability = (Revenue - COGS - SG&A) / Book Equity
df['op_profit'] = (df['revenue'] - df['cogs'] - df['sgna']) / df['equity']

# Rank by profitability
df['profit_rank'] = df.groupby('date')['op_profit'].transform(
    lambda x: pd.qcut(x, 3, labels=['Weak', 'Med', 'Robust'], duplicates='drop')
)

# Calculate RMW factor return
rmw = df.groupby(['date', 'profit_rank'])['ret'].mean().unstack()
rmw['RMW'] = rmw['Robust'] - rmw['Weak']
```

## Factor Regressions

### Fama-French 3-Factor Model

```python
import statsmodels.api as sm

# Prepare data
Y = df_stock['excess_ret']  # Stock return - risk-free rate
X = df_factors[['MKT', 'SMB', 'HML']]
X = sm.add_constant(X)

# Run regression
model = sm.OLS(Y, X).fit()
print(model.summary())

# Extract factor loadings
alpha = model.params['const']
beta_mkt = model.params['MKT']
beta_smb = model.params['SMB']
beta_hml = model.params['HML']

print(f"Alpha: {alpha:.4f} (t-stat: {model.tvalues['const']:.2f})")
print(f"Market Beta: {beta_mkt:.4f}")
print(f"Size Beta: {beta_smb:.4f}")
print(f"Value Beta: {beta_hml:.4f}")
print(f"R-squared: {model.rsquared:.4f}")
```

### Fama-French 5-Factor Model

```python
# Add investment (CMA) and profitability (RMW) factors
X = df_factors[['MKT', 'SMB', 'HML', 'RMW', 'CMA']]
X = sm.add_constant(X)

model = sm.OLS(Y, X).fit()
print(model.summary())
```

## Double-Sort Portfolios

### 2x3 Sort (Size x Value)

```python
# Step 1: Sort by size (2 groups)
df['size_group'] = df.groupby('date')['marketcap'].transform(
    lambda x: pd.qcut(x, 2, labels=['Small', 'Big'], duplicates='drop')
)

# Step 2: Within each size group, sort by B/M (3 groups)
df['value_group'] = df.groupby(['date', 'size_group'])['bm'].transform(
    lambda x: pd.qcut(x, 3, labels=['Low', 'Med', 'High'], duplicates='drop')
)

# Calculate portfolio returns
portfolio_returns = df.groupby(['date', 'size_group', 'value_group'])['ret'].mean()

# Extract specific portfolios
small_value = portfolio_returns.xs(('Small', 'High'), level=['size_group', 'value_group'])
big_growth = portfolio_returns.xs(('Big', 'Low'), level=['size_group', 'value_group'])
```

## Performance Attribution

```python
# Risk attribution using factor loadings
predicted_return = (
    alpha +
    beta_mkt * factors['MKT'] +
    beta_smb * factors['SMB'] +
    beta_hml * factors['HML']
)

# Decompose total return
actual_return = df_stock['excess_ret']
factor_return = predicted_return
idiosyncratic_return = actual_return - factor_return

print(f"Total Return: {actual_return.mean():.4f}")
print(f"Factor Return: {factor_return.mean():.4f}")
print(f"Idiosyncratic Return: {idiosyncratic_return.mean():.4f}")
```

## Example: Building a Multi-Factor Strategy

```python
import pandas as pd
import numpy as np

# Load data with multiple characteristics
df = pd.read_parquet('stock_characteristics.parquet')

# Calculate composite factor score
df['momentum_score'] = df.groupby('date')['momentum'].rank(pct=True)
df['value_score'] = df.groupby('date')['bm'].rank(pct=True)
df['quality_score'] = df.groupby('date')['roe'].rank(pct=True)

# Equal-weighted composite score
df['composite_score'] = (
    df['momentum_score'] +
    df['value_score'] +
    df['quality_score']
) / 3

# Form quintile portfolios
df['quintile'] = df.groupby('date')['composite_score'].transform(
    lambda x: pd.qcut(x, 5, labels=False, duplicates='drop')
)

# Calculate equal-weighted quintile returns
quintile_returns = df.groupby(['date', 'quintile'])['ret'].mean().unstack()

# Long-short strategy
quintile_returns['Long-Short'] = quintile_returns[4] - quintile_returns[0]

# Performance metrics
mean_ret = quintile_returns['Long-Short'].mean() * 12
volatility = quintile_returns['Long-Short'].std() * np.sqrt(12)
sharpe = mean_ret / volatility

print(f"Multi-Factor Strategy")
print(f"Annualized Return: {mean_ret:.2%}")
print(f"Annualized Volatility: {volatility:.2%}")
print(f"Sharpe Ratio: {sharpe:.2f}")

# Save results
quintile_returns.to_parquet('multifactor_returns.parquet')
```

## Best Practices

1. **Timing**: Use lagged fundamentals to avoid lookahead bias
2. **Outliers**: Winsorize extreme values (1st and 99th percentiles)
3. **Industry neutrality**: Consider industry adjustments for some factors
4. **Rebalancing frequency**: Monthly or quarterly depending on factors
5. **Transaction costs**: Account for turnover in factor portfolios
6. **Factor definitions**: Document exactly how each factor is constructed
