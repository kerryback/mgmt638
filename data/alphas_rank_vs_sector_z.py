"""Factor alphas and Sharpe ratios for the rank and sector-z models.

The IC and the raw decile spread in `compare_rank_vs_sector_z.py` say the sort
works. They do not say it is worth anything: the model's features ARE factor
proxies -- momentum, gross profitability, price-to-book, market cap, volatility
-- so a long-short spread built from them could be entirely a repackaging of
factors you can buy for four basis points. The regression is what separates the
two, and for this course it is the more honest number.

Two portfolios per model, both equal-weighted, rebalanced monthly:

  D10 - D1   zero-cost long-short. No risk-free subtraction: you are not
             funding it. Sharpe = mean / sd.
  D10        long only, excess of RF. This is the one a student can actually
             hold, and the one whose Sharpe is comparable to a fund's.

Regressed on Fama-French 5 factors plus momentum. MOM is in there because
`momentum` is a model feature and leaving it out would hand the strategy an
alpha that is just the momentum premium.
"""
import numpy as np, pandas as pd, joblib
import pandas_datareader.data as web
import statsmodels.api as sm

FACTORS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]
CAPM = ["Mkt-RF"]

# Both models are reported because they answer different questions. CAPM asks
# "did this beat the market", which is what a client asks. FF6 asks "did this
# beat the factors you could have bought instead", which is the question that
# decides whether the model earned its keep. When the CAPM alpha is large and
# the FF6 alpha is not, the strategy is a factor portfolio wearing a machine-
# learning label -- and that gap is the whole lesson.

def deciles(model_file, panel_file):
    b = joblib.load(model_file)
    d = pd.read_parquet(panel_file)
    te = d[d.month > b["train_end"]].copy()
    te["pred"] = b["model"].predict(te[b["features"]])
    q = te.groupby("month")["pred"].transform(
        lambda x: pd.qcut(x.rank(method="first"), 10, labels=False))
    m = te.groupby(["month", q]).ret.mean().unstack()
    return pd.DataFrame({"ls": m[9] - m[0], "long": m[9], "short": m[0]}).dropna()

port = {"ranks": deciles("session7_model.joblib", "session7_features.parquet"),
        "sector z": deciles("session7_model_sector_z.joblib",
                            "session7_features_sector_z.parquet")}

ff5 = web.DataReader("F-F_Research_Data_5_Factors_2x3", "famafrench",
                     start="2020-01-01")[0] / 100.0
mom = web.DataReader("F-F_Momentum_Factor", "famafrench", start="2020-01-01")[0] / 100.0
mom.columns = ["Mom"]
ff = ff5.join(mom, how="inner")
ff.index = ff.index.astype(str)
print(f"Fama-French factors available {ff.index.min()} to {ff.index.max()}\n")

def run(r, rf, label, zero_cost):
    """r: portfolio return series. Prints CAPM and FF6 side by side."""
    excess = r if zero_cost else r - rf
    cap = sm.OLS(excess, sm.add_constant(ff.loc[r.index, CAPM])).fit()
    ff6 = sm.OLS(excess, sm.add_constant(ff.loc[r.index, FACTORS])).fit()
    sharpe = excess.mean() / excess.std() * np.sqrt(12)
    print(f"  {label:<26}{r.mean()*1200:>8.2f}{r.std()*np.sqrt(12)*100:>7.1f}"
          f"{sharpe:>7.2f}"
          f"{cap.params['const']*1200:>9.2f}{cap.tvalues['const']:>6.2f}"
          f"{cap.rsquared:>6.2f}"
          f"{ff6.params['const']*1200:>9.2f}{ff6.tvalues['const']:>6.2f}"
          f"{ff6.rsquared:>6.2f}")
    return ff6

print(f"  {'':<26}{'':>8}{'':>7}{'':>7}{'------ CAPM ------':>21}"
      f"{'------- FF6 ------':>21}")
print(f"  {'':<26}{'ann ret%':>8}{'vol%':>7}{'Sharpe':>7}"
      f"{'alpha%':>9}{'t':>6}{'R2':>6}{'alpha%':>9}{'t':>6}{'R2':>6}")
fits = {}
for name, p in port.items():
    common = p.index.intersection(ff.index)
    p = p.loc[common]
    rf = ff.loc[common, "RF"]
    fits[(name, "ls")] = run(p["ls"], rf, f"{name}: D10-D1", zero_cost=True)
    fits[(name, "long")] = run(p["long"], rf, f"{name}: D10 long only", zero_cost=False)
    fits[(name, "short")] = run(p["short"], rf, f"{name}: D1 (the short leg)", zero_cost=False)

print(f"\nmonths in the regression: "
      f"{len(port['ranks'].index.intersection(ff.index))}")

print("\nFF6 factor loadings (D10-D1):")
print(f"  {'':<12}" + "".join(f"{f:>9}" for f in FACTORS))
for name in port:
    f = fits[(name, "ls")]
    print(f"  {name:<12}" + "".join(f"{f.params[k]:>9.2f}" for k in FACTORS))
    print(f"  {'t':<12}" + "".join(f"{f.tvalues[k]:>9.1f}" for k in FACTORS))
