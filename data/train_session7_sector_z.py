"""Session 7 model, refit with SECTOR Z-SCORES instead of cross-sectional ranks.

Same universe, same target, same folds, same grid as `train_session7_model.py`.
The only thing that changes is the feature transform, so the two out-of-sample
numbers are directly comparable and the difference is attributable.

    rank version    x -> percentile of x within the month
    this version    x -> (x - mean of x in month x sector) / (sd in month x sector)

WHAT THE CHANGE ACTUALLY DOES

Not scaling. Trees are invariant to any monotone transform applied uniformly,
and within a single month-sector cell the z-score IS monotone in x -- it cannot
reorder two stocks in the same sector in the same month. What changes is what a
split MEANS when it is compared across cells:

1. It removes the sector level from every feature. A stock can no longer be
   cheap because energy is cheap, only cheap FOR AN ENERGY STOCK. This is the
   same construction MSCI uses for QUAL and VLUE, and it makes the model
   sector-neutral by construction rather than by constraint. Compare the
   docstring of `train_session7_model.py`, point 4: one-hot sectors let the tree
   learn a sector bet that had the wrong sign out of sample. Sector z-scores go
   the other way and deny it the information entirely.

2. It keeps the SPREAD that ranks throw away. Two stocks one percentile apart
   are one percentile apart whether the cross-section is tight or dispersed. In
   z-scores the same pair is far apart in a tight month and close in a wild one.
   That is either extra information or extra noise, and the test-period IC is
   the thing that decides which.

WINSORIZING IS NOT OPTIONAL HERE

The raw features are viciously skewed -- pooled skewness is 745 for volatility,
369 for illiquidity, 224 for ps. A mean and an sd computed on that is a
description of one stock, and every other stock in the cell gets crushed toward
zero. So raw values are winsorized inside the cell before the moments are taken,
and the resulting z is clipped at +/- 3, which is MSCI's own recipe. Set
WINSOR = None to see how bad it is without this; several features collapse to a
spike at zero with a handful of rows pinned at the clip.

Missing values fill to 0.0, the cell mean, exactly as the rank version fills to
0.5, the cross-sectional median.

225 rows (0.04%) carry no sector and are dropped -- fewer than one per month, so
there is no cell to z-score them against. Every other choice is unchanged.
"""
import numpy as np, pandas as pd, joblib
from scipy.stats import spearmanr
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GridSearchCV

TRAIN_END = "2020-12"
MIN_PRICE = 5.0
CAP_LO, CAP_HI = 1001, 3000
N_ESTIMATORS = 300
WINSOR = 0.01                            # raw tails trimmed inside each cell
ZCLIP = 3.0                              # MSCI winsorizes the composite at +/- 3

SIGNALS = ["momentum", "ret_1m", "volatility", "volatility_12m", "illiquidity",
           "dollarvol", "marketcap", "pb", "ps", "roe", "accruals", "assetgrowth",
           "issuance", "grossprofitability", "divyield"]

df = pd.read_parquet("session7_monthly.parquet")

caprank = df.groupby("month").marketcap.rank(ascending=False, method="first")
d = df[(caprank >= CAP_LO) & (caprank <= CAP_HI) & (df.closeunadj > MIN_PRICE)].copy()
n_before = len(d)
d = d[d.sector.notna()]
d = d.sort_values(["month", "ticker"]).reset_index(drop=True)
print(f"universe {len(d):,} rows ({n_before - len(d)} dropped for missing sector)")

# ------------------------------------------------- sector z-score features ---
cell = d.groupby(["month", "sector"])

def sector_z(col):
    x = d[col]
    if WINSOR:
        lo = cell[col].transform(lambda s: s.quantile(WINSOR))
        hi = cell[col].transform(lambda s: s.quantile(1 - WINSOR))
        x = x.clip(lo, hi)
    mu = x.groupby([d.month, d.sector]).transform("mean")
    sd = x.groupby([d.month, d.sector]).transform("std")
    z = (x - mu) / sd.replace(0, np.nan)
    return z.clip(-ZCLIP, ZCLIP)

X = pd.DataFrame({c: sector_z(c) for c in SIGNALS}).fillna(0.0)

# The TARGET is unchanged: the cross-sectional percentile rank of the return,
# over the whole month, NOT within sector. The question being asked is still
# "which stocks beat the market next month", not "which beat their own sector".
d["target"] = d.groupby("month")["ret"].rank(pct=True)

print("\nfeature health after the transform (want sd near 1, |skew| small):")
print(pd.DataFrame({"sd": X.std(), "skew": X.skew(),
                    "at_clip_%": (X.abs() >= ZCLIP - 1e-9).mean() * 100})
      .round(2).to_string())

train = d.month <= TRAIN_END
Xtr, ytr = X[train], d.loc[train, "target"]
months_tr = d.loc[train, "month"].values
print(f"\ntrain {train.sum():,} rows over {d.loc[train,'month'].nunique()} months "
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
    p = estimator.predict(X_)
    m = MONTH_TR[X_.index.values] if hasattr(X_, "index") else None
    out = [spearmanr(p[m == u], y_.values[m == u]).statistic for u in np.unique(m)]
    return float(np.nanmean(out))

Xtr = Xtr.reset_index(drop=True); ytr = ytr.reset_index(drop=True)

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
             "min_price": MIN_PRICE, "cap_ranks": (CAP_LO, CAP_HI),
             "transform": "sector_z", "winsor": WINSOR, "zclip": ZCLIP},
            "session7_model_sector_z.joblib")

out = pd.concat([d[["month", "ticker", "name", "sector", "ret", "target"]], X], axis=1)
out.to_parquet("session7_features_sector_z.parquet", index=False, compression="zstd")
print(f"\nsaved session7_model_sector_z.joblib and "
      f"session7_features_sector_z.parquet {out.shape}")
