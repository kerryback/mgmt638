"""Turn the raw live panel into the app-ready file: screened, then ranked.

`build_session7_monthly.py --live-only` writes `session7_live_raw.parquet`, which
is the whole September cross-section with raw feature values -- 4,354 tickers,
mega caps included, nothing filtered. That is the right thing for the builder to
emit, because filtering is a decision someone should make on purpose. It is the
wrong thing to hand an app.

Fed raw, `model.predict` does not fail. The column names all match, so it
returns numbers -- meaningless ones, because a `marketcap` of 5,320,798 lands in
a tree whose splits were learned on values between 0 and 1. A silently wrong
answer is the failure mode this script exists to prevent.

THE ORDER MATTERS AND IT IS NOT ARBITRARY. Screen first, then rank, exactly as
`train_session7_model.py` did it:

  1. Rank market cap over the FULL cross-section and keep ranks 1001-3000, the
     way Russell ranks it, then apply the price floor.
  2. Rank every feature WITHIN what survives.

Ranking first and screening second would leave each percentile describing a
population the model never sees.

Every screen parameter is read out of the model bundle rather than repeated
here, so the data cannot drift away from the model it feeds. Change the model
and this file follows.

Run after the builder:

    python build_session7_monthly.py --live-only
    python make_session7_live.py
"""
import joblib
import pandas as pd

BUNDLE = "session7_model_full.joblib"
RAW = "session7_live_raw.parquet"
OUT = "session7_live.parquet"

b = joblib.load(BUNDLE)
SIGNALS = b["signals"]
CAP_LO, CAP_HI = b["cap_ranks"]
MIN_PRICE = b["min_price"]

raw = pd.read_parquet(RAW)
month = raw["month"].iloc[0]
assert raw["month"].nunique() == 1, "the live panel should hold exactly one month"
assert "ret" not in raw.columns, "the live panel must not carry a realized return"

# ---- 1. the screen, on the full cross-section -------------------------------
caprank = raw.groupby("month").marketcap.rank(ascending=False, method="first")
d = raw[(caprank >= CAP_LO) & (caprank <= CAP_HI)
        & (raw.closeunadj > MIN_PRICE)].copy()
d = d.sort_values("ticker").reset_index(drop=True)

# ---- 2. the ranks, within what survived -------------------------------------
gm = d.groupby("month")
X = pd.DataFrame({c: gm[c].rank(pct=True) for c in SIGNALS}).fillna(0.5)

out = pd.concat([d[["month", "ticker", "name"]], X], axis=1)

# Same column contract as session7_test.parquet minus `ret` and `target`, which
# do not exist for a month that has not finished.
assert list(out.columns) == ["month", "ticker", "name"] + b["features"]
assert out[b["features"]].isna().sum().sum() == 0
assert out[b["features"]].min().min() >= 0 and out[b["features"]].max().max() <= 1

out.to_parquet(OUT, index=False, compression="zstd")

print(f"{RAW}: {len(raw):,} rows, raw and unscreened")
print(f"  screened to cap ranks {CAP_LO}-{CAP_HI} and close > ${MIN_PRICE:g}: {len(d):,}")
print(f"{OUT}: month {month}, {out.shape[0]:,} rows x {out.shape[1]} columns")
print(f"  features ranked within the screened universe, missing filled at 0.5")

# A prediction here is not a test of the model, only of the file's shape.
p = b["model"].predict(out[b["features"]])
top = out.assign(pred=p).nlargest(5, "pred")[["ticker", "name", "pred"]]
print("\nhighest predicted ranks this month:")
print(top.to_string(index=False))
