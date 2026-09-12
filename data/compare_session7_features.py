"""Four ways to feed the same signals to the same model.

The CV column is the one allowed to choose. The test column is reported beside
it to show whether the choice held up -- picking the treatment by its test score
is the exact selection bias the train/test split exists to prevent, and doing it
in front of the class is worth more than pretending the temptation isn't there.
"""
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import GradientBoostingRegressor

SIGNALS = ["momentum","ret_1m","volatility","volatility_12m","illiquidity","dollarvol",
           "marketcap","pb","ps","roe","accruals","assetgrowth","issuance",
           "grossprofitability","divyield"]
TRAIN_END, PARAMS = "2020-12", dict(n_estimators=300, learning_rate=0.02, max_depth=2, random_state=0)

df = pd.read_parquet("session7_monthly.parquet")
d = df[(df.closeunadj > 5) & (df.marketcap > 500)].copy()
d = d.sort_values(["month","ticker"]).reset_index(drop=True)
d["sector"] = d["sector"].replace("", "Unclassified")
d["target"] = d.groupby("month").ret.rank(pct=True)
sect = pd.get_dummies(d["sector"], prefix="sec").astype(float)

xs   = pd.DataFrame({c: d.groupby("month")[c].rank(pct=True) for c in SIGNALS}).fillna(0.5)
wit  = pd.DataFrame({c: d.groupby(["month","sector"])[c].rank(pct=True) for c in SIGNALS}).fillna(0.5)
raw  = d[SIGNALS].apply(lambda c: c.fillna(c.median()))

VARIANTS = {
 "raw levels + sector dummies":        pd.concat([raw, sect], axis=1),
 "cross-sectional ranks + dummies":    pd.concat([xs,  sect], axis=1),
 "cross-sectional ranks, no dummies":  xs,
 "within-sector ranks, no dummies":    wit,
}

train = (d.month <= TRAIN_END).values
mon = d.month.values
um = np.array(sorted(pd.unique(mon[train]))); blocks = np.array_split(um, 6)

def ic(pred, y, m):
    return np.nanmean([spearmanr(pred[m==u], y[m==u]).statistic for u in np.unique(m)])

print(f"{'features':<36}{'cv IC':>9}{'test IC':>10}{'D10-D1 %/mo':>13}{'t':>6}{'sector imp':>12}")
for name, X in VARIANTS.items():
    Xv, y = X.values, d.target.values
    cvs = []
    for i in range(5):
        a = np.isin(mon, np.concatenate(blocks[:i+1])); b = np.isin(mon, blocks[i+1])
        mdl = GradientBoostingRegressor(**PARAMS).fit(Xv[a], y[a])
        cvs.append(ic(mdl.predict(Xv[b]), y[b], mon[b]))
    mdl = GradientBoostingRegressor(**PARAMS).fit(Xv[train], y[train])
    p = mdl.predict(Xv[~train]); yt, mt = y[~train], mon[~train]
    t = pd.DataFrame({"month": mt, "p": p, "ret": d.ret.values[~train]})
    q = t.groupby("month").p.transform(lambda x: pd.qcut(x.rank(method="first"),10,labels=False))
    sp = (t.groupby(["month",q]).ret.mean().unstack()[9] - t.groupby(["month",q]).ret.mean().unstack()[0]).dropna()
    imp = pd.Series(mdl.feature_importances_, index=X.columns)
    si = imp[[c for c in X.columns if c.startswith("sec_")]].sum()
    print(f"{name:<36}{np.mean(cvs):>9.4f}{ic(p,yt,mt):>10.4f}{sp.mean()*100:>13.2f}"
          f"{sp.mean()/sp.std()*np.sqrt(len(sp)):>6.1f}{si:>12.3f}")
