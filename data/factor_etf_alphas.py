"""Factor ETF returns and alphas relative to SPY.

Prices: Yahoo Finance adjusted closes (cached in factor_etfs_daily.csv).
Risk-free rate: Ken French's daily and monthly research-factor files.
Prints the performance table, the alpha regressions against SPY, and the
calendar-year table.

    python data/factor_etf_alphas.py [--refresh]
"""

import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
from pandas_datareader.famafrench import FamaFrenchReader

TICKERS = ["MTUM", "QUAL", "VLUE", "USMV", "SIZE", "SPY"]
FUNDS = TICKERS[:-1]
START = "2011-01-01"
CSV = "data/factor_etfs_daily.csv"

if "--refresh" in sys.argv:
    import yfinance as yf

    px = yf.download(TICKERS, start=START, auto_adjust=True, progress=False)["Close"]
    px[TICKERS].dropna(how="all").to_csv(CSV)

px = pd.read_csv(CSV, index_col="Date", parse_dates=True)[TICKERS]
common = px.dropna()                      # every fund trading: starts at QUAL's launch
ret_d = common.pct_change().dropna()

ff_d = FamaFrenchReader("F-F_Research_Data_Factors_daily", start=START).read()[0] / 100
ff_d.index = ff_d.index.to_timestamp()
rf_d = ff_d["RF"]

# French lags Yahoo by a month or two; excess returns stop where RF stops.
end = min(ret_d.index[-1], rf_d.index[-1])
print(f"prices: {common.index[0].date()} to {common.index[-1].date()}")
print(f"French RF ends {rf_d.index[-1].date()}; excess-return sample ends {end.date()}")

exc_d = ret_d.loc[:end].sub(rf_d.reindex(ret_d.loc[:end].index), axis=0)
assert exc_d.notna().all().all(), "RF gaps inside the sample"

# ---- performance over the full price history ---------------------------
years = (common.index[-1] - common.index[0]).days / 365.25
rows = []
for t in TICKERS:
    cagr = (common[t].iloc[-1] / common[t].iloc[0]) ** (1 / years) - 1
    vol = ret_d[t].std() * np.sqrt(252)
    dd = (common[t] / common[t].cummax() - 1).min()
    sharpe = exc_d[t].mean() / exc_d[t].std() * np.sqrt(252)
    rows.append([t, 100 * cagr, 100 * vol, 100 * dd, cagr / vol, sharpe])
perf = pd.DataFrame(rows, columns=["ticker", "CAGR%", "vol%", "maxDD%", "ret/vol", "Sharpe"])
print(f"\n=== Performance, {common.index[0].date()} to {common.index[-1].date()} ===")
print(perf.set_index("ticker").round(2).to_string())


def regress(exc, periods, label):
    out = []
    for t in FUNDS:
        fit = sm.OLS(exc[t], sm.add_constant(exc["SPY"])).fit(
            cov_type="HAC", cov_kwds={"maxlags": max(1, int(periods / 12))}
        )
        a, b = fit.params["const"], fit.params["SPY"]
        resid = exc[t] - a - b * exc["SPY"]
        out.append(
            [t, 100 * periods * a, fit.tvalues["const"], b, fit.tvalues["SPY"],
             fit.rsquared, 100 * resid.std() * np.sqrt(periods),
             periods * a / (resid.std() * np.sqrt(periods))]
        )
    df = pd.DataFrame(
        out,
        columns=["ticker", "alpha%/yr", "t(alpha)", "beta", "t(beta)", "R2", "TE%/yr", "IR"],
    ).set_index("ticker")
    print(f"\n=== Excess returns regressed on SPY excess return, {label} (Newey-West) ===")
    print(df.round(3).to_string())
    print(f"n = {len(exc)}")
    return df


regress(exc_d, 252, "daily")

px_m = common.loc[:end].resample("ME").last()
ret_m = px_m.pct_change().dropna()
ff_m = FamaFrenchReader("F-F_Research_Data_Factors", start=START).read()[0] / 100
ff_m.index = ff_m.index.to_timestamp(how="end").normalize()
rf_m = ff_m["RF"].reindex(ret_m.index)
ret_m, rf_m = ret_m[rf_m.notna()], rf_m.dropna()
exc_m = ret_m.sub(rf_m, axis=0)
regress(exc_m, 12, "monthly")

# ---- calendar years ----------------------------------------------------
cal = pd.concat([common.iloc[[0]], common.resample("YE").last()]).pct_change().dropna()
cal.index = cal.index.year
print("\n=== Calendar-year total returns (%) ===")
print((100 * cal).round(1).to_string())
print("\nbest fund each year:")
print(cal[FUNDS].idxmax(axis=1).to_string())
print("\nfunds beating SPY each year:")
print(cal[FUNDS].gt(cal["SPY"], axis=0).sum(axis=1).to_string())


# ---- joint test that all five alphas are zero (GRS, monthly) -----------
def grs(exc):
    from scipy import stats

    y = exc[FUNDS].to_numpy()
    f = exc[["SPY"]].to_numpy()
    X = np.column_stack([np.ones(len(f)), f])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b
    T, N, K = len(y), y.shape[1], 1
    sigma = e.T @ e / (T - K - 1)
    mu = f.mean(0)
    omega = np.cov(f.T, ddof=1).reshape(K, K)
    a = b[0]
    stat = (T - N - K) / N * (a @ np.linalg.solve(sigma, a)) / (1 + mu @ np.linalg.solve(omega, mu))
    p = 1 - stats.f.cdf(stat, N, T - N - K)
    return stat, p


stat, p = grs(exc_m)
print(f"\nGRS test, all five alphas = 0 (monthly): F = {stat:.3f}, p = {p:.3f}")
