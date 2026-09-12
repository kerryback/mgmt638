"""Sharpe ratios and factor alphas for the session 7 strategy, 2021-2026.

Three portfolios, all equal-weighted and rebalanced monthly:
  long-short  decile 10 minus decile 1, self-financing
  long only   decile 10, in excess of the risk-free rate
  short only  minus decile 1, in excess of the risk-free rate

Two regressions, because the model trades momentum and low volatility and FF5
prices neither. An alpha that survives FF5 but dies once momentum is added is
not alpha, it is a momentum loading that the five-factor model cannot see.

Reported t-statistics are Newey-West with 3 lags. Monthly long-short returns are
mildly autocorrelated and plain OLS standard errors run a little small.
"""
import numpy as np, pandas as pd, joblib
import statsmodels.api as sm
import pandas_datareader.data as web

bundle = joblib.load("session7_model.joblib")
d = pd.read_parquet("session7_features.parquet")
te = d[d.month > bundle["train_end"]].copy()
te["pred"] = bundle["model"].predict(te[bundle["features"]])

q = te.groupby("month").pred.transform(lambda x: pd.qcut(x.rank(method="first"), 10, labels=False))
dec = te.groupby(["month", q]).ret.mean().unstack()
port = pd.DataFrame({"long_short": dec[9] - dec[0], "long_only": dec[9], "short_only": -dec[0]})
port.index = pd.PeriodIndex(port.index, freq="M")

ff5 = web.DataReader("F-F_Research_Data_5_Factors_2x3", "famafrench", start="2000-01-01")[0] / 100.0
mom = web.DataReader("F-F_Momentum_Factor", "famafrench", start="2000-01-01")[0] / 100.0
mom.columns = ["MOM"]
# Ken French publishes with a lag, so the factor file can end before the price
# panel does. Intersect rather than reindex, and say how many months that costs.
fac = ff5.join(mom)
keep = port.index.intersection(fac.index)
dropped = len(port) - len(keep)
port, f = port.loc[keep], fac.loc[keep]
FF5 = ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]

print(f"test period {port.index.min()} to {port.index.max()}, {len(port)} months"
      + (f"  ({dropped} month(s) dropped: no factor data yet)" if dropped else ""))
print(f"factor data {f.index.min()} to {f.index.max()}, RF averages "
      f"{f.RF.mean()*12*100:.2f}%/yr over the window\n")

print(f"{'portfolio':<13}{'mean %/mo':>11}{'sd %/mo':>9}{'ann ret %':>11}{'ann sd %':>10}{'Sharpe':>8}")
for name in port.columns:
    r = port[name]
    ex = r if name == "long_short" else r - f.RF      # long-short is self-financing
    ann = (1 + r).prod() ** (12 / len(r)) - 1
    print(f"{name:<13}{r.mean()*100:>11.2f}{r.std()*100:>9.2f}{ann*100:>11.1f}"
          f"{r.std()*np.sqrt(12)*100:>10.1f}{ex.mean()/ex.std()*np.sqrt(12):>8.2f}")

def reg(y, cols, label):
    X = sm.add_constant(f[cols])
    m = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    a = m.params["const"]
    print(f"  {label:<26}{a*12*100:>9.2f}{m.tvalues['const']:>8.2f}"
          + "".join(f"{m.params[c]:>8.2f}" for c in cols) + f"{m.rsquared:>8.2f}")

for name in port.columns:
    r = port[name]
    y = r if name == "long_short" else r - f.RF
    print(f"\n{name}:")
    print(f"  {'model':<26}{'alpha %/yr':>9}{'t':>8}" + "".join(f"{c:>8}" for c in FF5) + f"{'R2':>8}")
    reg(y, FF5, "Fama-French 5-factor")
    print(f"  {'':<26}{'':>9}{'':>8}" + "".join(f"{c:>8}" for c in FF5 + ["MOM"]))
    reg(y, FF5 + ["MOM"], "FF5 + momentum")
