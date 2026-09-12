"""Build the two files the students receive: the fitted model and the test panel.

The test panel is 2021 onward ONLY. The training years are deliberately withheld
-- the exercise is to evaluate a model on data it has never seen, and handing
over the training rows invites the one mistake the whole design is built to
prevent. Industry columns are dropped because the model does not use them.
"""
import joblib, pandas as pd

bundle = joblib.load("session7_model.joblib")
d = pd.read_parquet("session7_features.parquet")

te = d[d.month > bundle["train_end"]].copy()
te = te[["month", "ticker", "name", "ret", "target"] + bundle["features"]]
te = te.sort_values(["month", "ticker"]).reset_index(drop=True)
te.to_parquet("session7_test.parquet", index=False, compression="zstd")

joblib.dump(bundle, "session7_model.joblib")

print(f"session7_test.parquet  {te.shape}")
print(f"  months {te.month.min()} to {te.month.max()} ({te.month.nunique()} months)")
print(f"  {te.ticker.nunique():,} tickers, {len(te)/te.month.nunique():.0f} stocks per month")
print(f"  columns: {list(te.columns)}")
print(f"  any nulls: {te.isna().any().any()}")
print(f"\nsession7_model.joblib  {bundle['model']}")
