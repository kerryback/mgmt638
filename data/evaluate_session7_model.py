"""Test-period evaluation of the session 7 model -- the shape of what students do.

Fit once on 2015-2020, predict 2021-2026, sort on the prediction, never refit.
Two benchmarks, because "the model has a positive IC" is not the question. The
question is whether it beats a one-line sort on momentum and whether the boosting
beats a plain linear regression on the same features.
"""
import numpy as np, pandas as pd, joblib
from scipy.stats import spearmanr
from sklearn.linear_model import LinearRegression

bundle = joblib.load("session7_model.joblib")
model, FEATURES = bundle["model"], bundle["features"]
d = pd.read_parquet("session7_features.parquet")
tr, te = d[d.month <= bundle["train_end"]], d[d.month > bundle["train_end"]].copy()
te["pred"] = model.predict(te[FEATURES])

lin = LinearRegression().fit(tr[FEATURES], tr["target"])
te["pred_lin"] = lin.predict(te[FEATURES])

def report(col, label):
    ic = te.groupby("month").apply(lambda g: spearmanr(g[col], g.target).statistic,
                                   include_groups=False)
    q = te.groupby("month")[col].transform(lambda x: pd.qcut(x.rank(method="first"), 10, labels=False))
    m = te.groupby(["month", q]).ret.mean().unstack()
    sp = (m[9] - m[0]).dropna()
    t = sp.mean()/sp.std()*np.sqrt(len(sp))
    tic = ic.mean()/ic.std()*np.sqrt(len(ic))
    print(f"  {label:<34}{ic.mean():>8.4f}{tic:>7.1f}{sp.mean()*100:>12.2f}{t:>7.1f}"
          f"{(1+sp).prod()**(12/len(sp))*100-100:>11.1f}")
    return m

print(f"test period {te.month.min()} to {te.month.max()}, {te.month.nunique()} months, {len(te):,} rows\n")
print(f"  {'':<34}{'IC':>8}{'t':>7}{'D10-D1 %/mo':>12}{'t':>7}{'ann %':>11}")
m = report("pred", "gradient boosting")
report("pred_lin", "linear regression, same features")
report("momentum", "momentum alone")
report("grossprofitability", "gross profitability alone")

print("\ndecile means, %/month, gradient boosting:")
print("  " + "".join(f"D{i+1:<6}" for i in range(10)))
print("  " + "".join(f"{v*100:<7.2f}" for v in m.mean()))

imp = pd.Series(model.feature_importances_, index=FEATURES).sort_values(ascending=False)
print("\nfeature importances, all 15:")
for k, v in imp.items():
    print(f"  {k:<22}{v:.3f}")
