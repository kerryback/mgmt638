"""Fit the session 7 gradient boosting model and write the panel students predict on.

The instructor runs this once. Students get `session7_model.joblib` and
`session7_features.parquet` and do the prediction, the sort and the evaluation.

Three choices in here are worth a slide each:

1. FEATURES ARE CROSS-SECTIONAL PERCENTILE RANKS, month by month, exactly like
   the target. Trees do not care about scale, so this is not about scaling -- it
   is about drift. Median dollar volume and median market cap in 2026 are not
   what they were in 2015, so a split learned as "marketcap > 4,000" on the
   training years lands in the wrong place in the test years. Ranks are stationary
   by construction and the split "top 30% by size" means the same thing forever.
   It also makes the missing-value fill obvious: 0.5, the middle of the cross
   section. GradientBoostingRegressor rejects NaN outright, and 6.6% of rows have
   at least one, so something has to be done and this is the least arbitrary.

2. THE CV FOLDS ARE EXPANDING WINDOWS OF WHOLE MONTHS, not KFold. Two separate
   reasons. Whole months, because stocks inside one month share the market and
   their returns are massively correlated -- split a month across the fold
   boundary and the model sees half of it while being scored on the other half.
   Expanding, because the alternative trains on 2020 to predict 2016.

3. THE CV SCORE IS THE MEAN MONTHLY RANK IC, not R^2. R^2 on a rank target is
   near zero and negative about as often as not; it is a true number that tells
   a student nothing. The IC -- the correlation between predicted and realized
   rank inside a month -- is what the strategy actually monetizes.

4. INDUSTRY IS NOT A FEATURE. It was, in the first version of this file, as 11
   one-hot sector columns, and the result is the best argument against it: the
   sector dummies took 40% of the fitted importance, `sec_Energy` alone took 27%,
   and the model's out-of-sample IC was 0.000 against a cv IC of 0.021. Energy
   was the worst sector for most of 2015-2020 and the best in 2021-2022, so what
   the tree had actually learned was a sector bet with the wrong sign for the
   test period. A one-hot industry is the easiest way for a tree to fit the
   training years and the least stationary thing in the file. `sector` stays in
   the output panel as a DESCRIPTIVE column, for grouping results after the fact.
"""
import numpy as np, pandas as pd, joblib
from scipy.stats import spearmanr
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GridSearchCV

TRAIN_END = "2020-12"
MIN_PRICE = 5.0                          # a tradeable universe, applied BEFORE ranking
CAP_LO, CAP_HI = 1001, 3000              # market-cap ranks kept, inclusive
N_ESTIMATORS = 300

SIGNALS = ["momentum", "ret_1m", "volatility", "volatility_12m", "illiquidity",
           "dollarvol", "marketcap", "pb", "ps", "roe", "accruals", "assetgrowth",
           "issuance", "grossprofitability", "divyield"]

df = pd.read_parquet("session7_monthly.parquet")

# The screen comes first, so every rank is a rank WITHIN the investable universe.
# Ranking the full file and then screening would leave a stock's percentile
# describing a population it is no longer being compared against.
# The screen is RELATIVE, not a dollar threshold, and it is the Russell 2000:
# market-cap ranks 1001-3000, so the mega caps are dropped and what is left is
# the small-cap universe. A fixed dollar bar would not hold still -- the median
# market cap of a $5+ stock rose about fivefold over 2001-2026 -- and since every
# feature is a rank WITHIN this universe, a drifting universe changes what every
# number means. The cap rank is taken over the WHOLE cross-section, the way
# Russell ranks it; the price floor is then applied as a tradeability screen.
caprank = df.groupby("month").marketcap.rank(ascending=False, method="first")
d = df[(caprank >= CAP_LO) & (caprank <= CAP_HI) & (df.closeunadj > MIN_PRICE)].copy()
d = d.sort_values(["month", "ticker"]).reset_index(drop=True)

# ---------------------------------------------------- features and target ---
gm = d.groupby("month")
X = pd.DataFrame({c: gm[c].rank(pct=True) for c in SIGNALS}).fillna(0.5)

d["target"] = gm["ret"].rank(pct=True)

train = d.month <= TRAIN_END
Xtr, ytr = X[train], d.loc[train, "target"]
months_tr = d.loc[train, "month"].values
print(f"universe {len(d):,} rows, {X.shape[1]} features (signals only, no industry)")
print(f"train {train.sum():,} rows over {d.loc[train,'month'].nunique()} months "
      f"({d.loc[train,'month'].min()} to {d.loc[train,'month'].max()})")
print(f"test  {(~train).sum():,} rows over {d.loc[~train,'month'].nunique()} months "
      f"({d.loc[~train,'month'].min()} to {d.loc[~train,'month'].max()})\n")

# ------------------------------------------- expanding-window month folds ---
um = np.array(sorted(pd.unique(months_tr)))
blocks = np.array_split(um, 6)
pos = np.arange(len(Xtr))
folds = []
for i in range(5):
    tr_m = np.concatenate(blocks[: i + 1]); va_m = blocks[i + 1]
    folds.append((pos[np.isin(months_tr, tr_m)], pos[np.isin(months_tr, va_m)]))
print("cv folds (expanding, whole months):")
for i, (a, b) in enumerate(folds):
    print(f"  fold {i+1}: train {len(a):>7,} rows / {len(np.unique(months_tr[a])):>2} months"
          f"   validate {len(b):>6,} rows / {len(np.unique(months_tr[b])):>2} months")

MONTH_TR = months_tr
def ic_score(estimator, X_, y_):
    """Mean over validation months of the within-month Spearman correlation."""
    p = estimator.predict(X_)
    m = MONTH_TR[X_.index.values] if hasattr(X_, "index") else None
    out = [spearmanr(p[m == u], y_.values[m == u]).statistic for u in np.unique(m)]
    return float(np.nanmean(out))

# GridSearchCV hands the scorer the positionally-indexed slice, so reset the
# index to positions and the lookup above lines up.
Xtr = Xtr.reset_index(drop=True); ytr = ytr.reset_index(drop=True)

# The grid is shifted UP from the first pass: with industry gone the model
# wanted more capacity, not less, and 0.1 won at the boundary. A winner sitting
# on the edge of the grid is not a chosen hyperparameter, it is an unexplored one.
grid = {"learning_rate": [0.02, 0.05, 0.10, 0.20, 0.30],
        "max_depth": [2, 3, 5]}
gs = GridSearchCV(GradientBoostingRegressor(n_estimators=N_ESTIMATORS, random_state=0),
                  grid, scoring=ic_score, cv=folds, n_jobs=-1, verbose=1)
print(f"\nfitting {len(grid['learning_rate'])*len(grid['max_depth'])*len(folds)} models "
      f"(n_estimators fixed at {N_ESTIMATORS}) ...", flush=True)
gs.fit(Xtr, ytr)

print(f"\nbest: {gs.best_params_}   cv mean monthly IC {gs.best_score_:.4f}\n")
cv = pd.DataFrame(gs.cv_results_)
tbl = cv.pivot_table(index="param_learning_rate", columns="param_max_depth", values="mean_test_score")
print("cv mean monthly IC by hyperparameter:")
print(tbl.round(4).to_string())

joblib.dump({"model": gs.best_estimator_, "features": list(X.columns),
             "signals": SIGNALS, "train_end": TRAIN_END,
             "min_price": MIN_PRICE, "cap_ranks": (CAP_LO, CAP_HI)},
            "session7_model.joblib")

# `sector` rides along for post-hoc grouping. It is NOT in `features`.
out = pd.concat([d[["month", "ticker", "name", "sector", "ret", "target"]], X], axis=1)
out.to_parquet("session7_features.parquet", index=False, compression="zstd")
print(f"\nsaved session7_model.joblib and session7_features.parquet {out.shape}")
