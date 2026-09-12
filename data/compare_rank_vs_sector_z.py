"""Rank features vs sector z-score features, same universe, same test period.

Both models are fit on 2001-2020 and never refit. This scores them on the
IDENTICAL set of test rows -- the sector-z panel drops 225 rows with no sector,
so the two panels are inner-joined on (month, ticker) before anything is
measured. Otherwise a difference of a few basis points could just be a
difference of population.

Three numbers per model, because they answer different questions:

  IC                 does the prediction order stocks correctly, market-wide
  within-sector IC   does it still order them correctly AFTER both the
                     prediction and the return are demeaned inside each
                     month x sector cell -- i.e. with every sector bet removed
  sector tilt        mean ABSOLUTE deviation, in percentage points, of the
                     long decile's sector weights from the universe's. This,
                     not the largest single share: the biggest sector in the
                     decile is large mostly because the universe's biggest
                     sector is large, so max-share barely moves between models
                     and says nothing. The deviation does.

The point of the comparison: sector z-scores cannot express "energy is cheap",
so if the sector-z model holds its IC while running a less concentrated book,
the ranking is coming from stock selection rather than from a sector tilt.
"""
import numpy as np, pandas as pd, joblib
from scipy.stats import spearmanr

def load(model_file, panel_file, tag):
    b = joblib.load(model_file)
    d = pd.read_parquet(panel_file)
    te = d[d.month > b["train_end"]].copy()
    te[f"pred_{tag}"] = b["model"].predict(te[b["features"]])
    return b, te[["month", "ticker", "sector", "ret", "target", f"pred_{tag}"]]

b_rank, te_rank = load("session7_model.joblib", "session7_features.parquet", "rank")
b_secz, te_secz = load("session7_model_sector_z.joblib",
                       "session7_features_sector_z.parquet", "secz")

te = te_rank.merge(te_secz[["month", "ticker", "pred_secz"]], on=["month", "ticker"])
print(f"test {te.month.min()} to {te.month.max()}, {te.month.nunique()} months, "
      f"{len(te):,} rows common to both panels")
print(f"  (rank panel {len(te_rank):,}, sector-z panel {len(te_secz):,})\n")

# within-cell demeaning: strips the sector's own mean from both sides
def demean(g, col):
    return g[col] - g.groupby(["month", "sector"])[col].transform("mean")

te["ret_w"] = demean(te, "ret")

def report(col, label):
    ic = te.groupby("month").apply(
        lambda g: spearmanr(g[col], g.target).statistic, include_groups=False)
    # within-sector IC: demean prediction and return inside each month x sector
    p_w = demean(te, col)
    r_w = te["ret_w"]
    icw = (pd.DataFrame({"m": te.month, "p": p_w, "r": r_w})
           .groupby("m").apply(lambda g: spearmanr(g.p, g.r).statistic,
                               include_groups=False))
    q = te.groupby("month")[col].transform(
        lambda x: pd.qcut(x.rank(method="first"), 10, labels=False))
    m = te.groupby(["month", q]).ret.mean().unstack()
    sp = (m[9] - m[0]).dropna()
    t = sp.mean() / sp.std() * np.sqrt(len(sp))
    # sector tilt: mean absolute deviation of the long decile's sector mix
    # from the universe's, in percentage points
    top = te[q == 9]
    sh = top.groupby("sector").size() / len(top) * 100
    uni = te.groupby("sector").size() / len(te) * 100
    conc = (sh - uni).abs().mean()
    print(f"  {label:<32}{ic.mean():>7.4f}{icw.mean():>9.4f}"
          f"{sp.mean()*100:>10.2f}{t:>7.1f}"
          f"{(1+sp).prod()**(12/len(sp))*100-100:>10.1f}{conc:>9.1f}")
    return m

print(f"  {'':<32}{'IC':>7}{'IC w/in':>9}{'D10-D1':>10}{'t':>7}{'ann %':>10}{'tilt pp':>9}")
m_rank = report("pred_rank", "GBM, cross-sectional ranks")
m_secz = report("pred_secz", "GBM, sector z-scores")
report("target", "perfect foresight (ceiling)")

print("\ndecile means, %/month")
print(f"  {'':<14}" + "".join(f"D{i+1:<6}" for i in range(10)))
print(f"  {'ranks':<14}" + "".join(f"{v*100:<7.2f}" for v in m_rank.mean()))
print(f"  {'sector z':<14}" + "".join(f"{v*100:<7.2f}" for v in m_secz.mean()))

print("\nagreement between the two predictions:")
agree = te.groupby("month").apply(
    lambda g: spearmanr(g.pred_rank, g.pred_secz).statistic, include_groups=False)
print(f"  mean monthly rank correlation of the two predictions: {agree.mean():.3f}")

print("\nfeature importances, side by side:")
i_rank = pd.Series(b_rank["model"].feature_importances_, index=b_rank["features"])
i_secz = pd.Series(b_secz["model"].feature_importances_, index=b_secz["features"])
comp = pd.DataFrame({"ranks": i_rank, "sector_z": i_secz})
comp["diff"] = comp.sector_z - comp.ranks
print(comp.sort_values("sector_z", ascending=False).round(3).to_string())
