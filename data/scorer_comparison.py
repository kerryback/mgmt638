"""Does mean-monthly-Spearman pick the same hyperparameters as MSE?

The argument for "no difference" runs: the target is a rank, so Spearman equals
Pearson; Pearson squared is R-squared; maximizing R-squared minimizes MSE. If
every link held, the scorer would be decoration.

Two links do not hold, so the question is empirical. Every model below is fit
ONCE and scored BOTH ways on the same validation rows, so the comparison is not
contaminated by refitting:

  ic    mean over validation months of the within-month Spearman correlation
  mse   pooled mean squared error over all validation rows
  r2p   mean over months of the SQUARED PEARSON correlation -- the quantity the
        argument conflates with R-squared. Reported to show it is not the same
        ordering as mse either.

Same universe, folds and grid as train_session7_model.py.
"""
import numpy as np, pandas as pd
from scipy.stats import spearmanr, pearsonr
from sklearn.ensemble import GradientBoostingRegressor
from joblib import Parallel, delayed

N_ESTIMATORS = 300
N_JOBS = 10
TRAIN_END = "2020-12"

d = pd.read_parquet("session7_features.parquet")
d = d[d.month <= TRAIN_END].reset_index(drop=True)
FEAT = [c for c in d.columns
        if c not in ("month", "ticker", "name", "sector", "ret", "target")]
X, y = d[FEAT].values, d["target"].values
months = d["month"].values

um = np.array(sorted(pd.unique(months)))
blocks = np.array_split(um, 6)
pos = np.arange(len(d))
folds = [(pos[np.isin(months, np.concatenate(blocks[: i + 1]))],
          pos[np.isin(months, blocks[i + 1])]) for i in range(5)]

print(f"{len(d):,} training rows, {len(um)} months, {len(FEAT)} features")
print(f"folds: {[len(v) for _, v in folds]} validation rows each\n", flush=True)

grid = [(lr, md) for lr in (0.02, 0.05, 0.10, 0.20, 0.30) for md in (1, 2, 3, 5)]

def one(lr, md, tr, va):
    """Fit once, score three ways on the same validation rows."""
    m = GradientBoostingRegressor(n_estimators=N_ESTIMATORS, learning_rate=lr,
                                  max_depth=md, random_state=0).fit(X[tr], y[tr])
    p, yv, mv = m.predict(X[va]), y[va], months[va]
    u = np.unique(mv)
    return (np.nanmean([spearmanr(p[mv == k], yv[mv == k]).statistic for k in u]),
            float(np.mean((p - yv) ** 2)),
            np.nanmean([pearsonr(p[mv == k], yv[mv == k]).statistic ** 2 for k in u]))

jobs = [(lr, md, tr, va) for lr, md in grid for tr, va in folds]
print(f"fitting {len(jobs)} models across {N_JOBS} workers ...", flush=True)
res = Parallel(n_jobs=N_JOBS, verbose=5)(delayed(one)(*j) for j in jobs)

rows = []
for i, (lr, md) in enumerate(grid):
    chunk = res[i * len(folds):(i + 1) * len(folds)]
    rows.append({"lr": lr, "depth": md,
                 "ic": np.mean([c[0] for c in chunk]),
                 "mse": np.mean([c[1] for c in chunk]),
                 "r2_pearson": np.mean([c[2] for c in chunk])})
    print(f"  lr={lr:<5} depth={md}  ic={rows[-1]['ic']:.4f}  "
          f"mse={rows[-1]['mse']:.6f}  r2p={rows[-1]['r2_pearson']:.5f}", flush=True)

r = pd.DataFrame(rows)
r["rank_ic"] = r.ic.rank(ascending=False)       # 1 = best
r["rank_mse"] = r.mse.rank(ascending=True)      # 1 = best
r["rank_r2p"] = r.r2_pearson.rank(ascending=False)

print("\n" + "=" * 68)
print(r.sort_values("rank_ic").to_string(index=False))

print("\nwinners")
print(f"  by IC   : lr={r.loc[r.rank_ic.idxmin(),'lr']}, "
      f"depth={int(r.loc[r.rank_ic.idxmin(),'depth'])}")
print(f"  by MSE  : lr={r.loc[r.rank_mse.idxmin(),'lr']}, "
      f"depth={int(r.loc[r.rank_mse.idxmin(),'depth'])}")
print(f"  by r2p  : lr={r.loc[r.rank_r2p.idxmin(),'lr']}, "
      f"depth={int(r.loc[r.rank_r2p.idxmin(),'depth'])}")

print("\nagreement of the two orderings over all "
      f"{len(r)} hyperparameter settings")
print(f"  Spearman(rank_ic, rank_mse)  = {spearmanr(r.rank_ic, r.rank_mse).statistic:.3f}")
print(f"  Spearman(rank_ic, rank_r2p)  = {spearmanr(r.rank_ic, r.rank_r2p).statistic:.3f}")
print(f"  Spearman(rank_mse, rank_r2p) = {spearmanr(r.rank_mse, r.rank_r2p).statistic:.3f}")
r.to_csv("scorer_comparison.csv", index=False)
print("\nsaved scorer_comparison.csv")
