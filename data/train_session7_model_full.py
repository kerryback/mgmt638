"""The rank model refit on ALL of 2001-2026, for deployment in the session 7 app.

Identical to `train_session7_model.py` -- same universe, same rank features, same
rank target, same expanding-month folds -- with two changes.

1. NO HOLDOUT. Every month through the end of the panel is training data.
   That is right for a model that is going to make live recommendations: the
   2021-2026 period is the most recent regime and the most relevant to next
   month, and throwing it away to preserve a test set buys nothing once the
   question has stopped being "does this approach work" and become "what does it
   say about September".

   The cost has to be stated rather than finessed: THIS MODEL HAS NO HONEST
   OUT-OF-SAMPLE NUMBER AND NEVER WILL. The evidence that the approach works is
   the 2021-2026 test of the split model in `session7_model.joblib`, which is a
   different fit. Quote that number when the app needs a track record, and say
   which model produced it. Any evaluation of THIS model on ANY month in the
   panel is in-sample and will flatter it.

2. THE GRID IS EXTENDED DOWNWARD. The split model's chosen hyperparameters were
   learning_rate 0.02 and max_depth 2 -- the bottom-left corner of the old grid,
   with both parameters on the boundary. By the reasoning already written into
   `train_session7_model.py` ("a winner sitting on the edge of the grid is not a
   chosen hyperparameter, it is an unexplored one"), that corner needed opening
   up. The grid now reaches learning_rate 0.01 and max_depth 1, so the optimum
   has room to be interior. The full cv table is printed; if the winner is STILL
   in the corner, extend it again rather than shipping it.

The saved bundle is `session7_model_full.joblib`, deliberately NOT overwriting
`session7_model.joblib`, which the session 7 evaluation needs to keep its
train/test split intact.
"""
import numpy as np, pandas as pd, joblib
from scipy.stats import spearmanr
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GridSearchCV

MIN_PRICE = 5.0
CAP_LO, CAP_HI = 1001, 3000
N_ESTIMATORS = 300

SIGNALS = ["momentum", "ret_1m", "volatility", "volatility_12m", "illiquidity",
           "dollarvol", "marketcap", "pb", "ps", "roe", "accruals", "assetgrowth",
           "issuance", "grossprofitability", "divyield"]

df = pd.read_parquet("session7_monthly.parquet")

caprank = df.groupby("month").marketcap.rank(ascending=False, method="first")
d = df[(caprank >= CAP_LO) & (caprank <= CAP_HI) & (df.closeunadj > MIN_PRICE)].copy()
d = d.sort_values(["month", "ticker"]).reset_index(drop=True)

gm = d.groupby("month")
X = pd.DataFrame({c: gm[c].rank(pct=True) for c in SIGNALS}).fillna(0.5)
d["target"] = gm["ret"].rank(pct=True)

TRAIN_END = d.month.max()                     # everything
months_tr = d["month"].values
Xtr, ytr = X, d["target"]
print(f"universe {len(d):,} rows, {X.shape[1]} features")
print(f"train {len(d):,} rows over {d.month.nunique()} months "
      f"({d.month.min()} to {d.month.max()}) -- no holdout\n")

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

grid = {"learning_rate": [0.01, 0.02, 0.05, 0.10, 0.20],
        "max_depth": [1, 2, 3, 5]}
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

if gs.best_params_["learning_rate"] == min(grid["learning_rate"]):
    print("\n  WARNING: learning_rate won at the bottom of the grid. Extend it.")
if gs.best_params_["max_depth"] == 1:
    print("\n  NOTE: max_depth 1 won, and 1 is the FLOOR -- a depth-1 tree is a"
          "\n  single split, so there is no smaller grid to extend to. This is not"
          "\n  an unexplored boundary, it is a result: the best model uses stumps,"
          "\n  which means NO feature interactions at all. Boosted stumps are an"
          "\n  additive model. Whatever this beats, it does not beat it by finding"
          "\n  interactions, so check it against a linear model on the same"
          "\n  features before claiming the boosting earned its complexity.")

joblib.dump({"model": gs.best_estimator_, "features": list(X.columns),
             "signals": SIGNALS, "train_end": TRAIN_END,
             "min_price": MIN_PRICE, "cap_ranks": (CAP_LO, CAP_HI),
             "transform": "cross_sectional_rank", "holdout": None,
             "note": "fit on all months; no out-of-sample evaluation is possible"},
            "session7_model_full.joblib")

out = pd.concat([d[["month", "ticker", "name", "sector", "ret", "target"]], X], axis=1)
out.to_parquet("session7_features_full.parquet", index=False, compression="zstd")
print(f"\nsaved session7_model_full.joblib and session7_features_full.parquet {out.shape}")
