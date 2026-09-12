import sys
sys.path.insert(0, "/Users/kerryback/repos/skills/plugins/finance-data-augmented/skills/finance-data/scripts")
import pandas as pd
from sharadar_db import query, query_years, delisting_returns

START, END = 2014, 2026     # 2014 pulled only for the Dec-2014 lag

SEP_SQL = """
WITH me AS (
  SELECT a.ticker, a.date::DATE AS date, a.closeadj, a.closeunadj,
         ROW_NUMBER() OVER (PARTITION BY a.ticker, DATE_TRUNC('month', a.date::DATE)
                            ORDER BY a.date::DATE DESC) AS rn
  FROM sep a
  WHERE a.date::DATE >= '{year}-01-01' AND a.date::DATE < '{next_year}-01-01'
)
SELECT ticker, CAST(date AS VARCHAR) AS date, closeadj, closeunadj
FROM me WHERE rn = 1
"""

DAILY_SQL = """
WITH me AS (
  SELECT d.ticker, d.date::DATE AS date,
         d.marketcap, d.pb, d.pe, d.ps, d.evebitda,
         ROW_NUMBER() OVER (PARTITION BY d.ticker, DATE_TRUNC('month', d.date::DATE)
                            ORDER BY d.date::DATE DESC) AS rn
  FROM daily d
  WHERE d.date::DATE >= '{year}-01-01' AND d.date::DATE < '{next_year}-01-01'
)
SELECT ticker, CAST(date AS VARCHAR) AS date, marketcap, pb, pe, ps, evebitda
FROM me WHERE rn = 1
"""

print("pulling sep month-ends ...", flush=True)
sep = query_years(SEP_SQL, START, END)
print(f"  {len(sep):,} rows", flush=True)

print("pulling daily month-ends ...", flush=True)
dly = query_years(DAILY_SQL, START, END)
print(f"  {len(dly):,} rows", flush=True)

for df in (sep, dly):
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")

# ---- returns: month t closeadj over month t-1 closeadj -------------------
prior = sep[["ticker", "month", "date", "closeadj", "closeunadj"]].copy()
prior["month"] = prior["month"] + 1          # align onto the month it predicts
prior = prior.rename(columns={"date": "prior_date", "closeadj": "prior_closeadj",
                              "closeunadj": "closeunadj"})

panel = sep.drop(columns=["closeunadj"]).merge(prior, on=["ticker", "month"], how="inner")
panel["ret"] = panel["closeadj"] / panel["prior_closeadj"] - 1

# ---- valuation ratios as of the last trading day of month t-1 -----------
val = dly.drop(columns=["month"]).rename(columns={"date": "prior_date"})
panel = panel.merge(val, on=["ticker", "prior_date"], how="left")

# ---- delisting returns, compounded onto each ticker's final month -------
dl = delisting_returns()
last_month = panel.groupby("ticker")["month"].max().rename("final_month")
dl = dl.merge(last_month, left_on="ticker", right_index=True, how="inner")
dl = dl[["ticker", "final_month", "delisting_return", "basis"]]

panel = panel.merge(dl, left_on=["ticker", "month"],
                    right_on=["ticker", "final_month"], how="left")
hit = panel["delisting_return"].notna()
panel.loc[hit, "ret"] = (1 + panel.loc[hit, "ret"]) * (1 + panel.loc[hit, "delisting_return"]) - 1
print(f"delisting return applied to {int(hit.sum()):,} ticker-months", flush=True)

# ---- ticker attributes ---------------------------------------------------
tk = query("""
SELECT ticker, permaticker, siccode, famaindustry, industry, sector
FROM tickers
""")
panel = panel.merge(tk, on="ticker", how="left")

# ---- shape and save ------------------------------------------------------
panel = panel[panel["month"] >= pd.Period("2015-01", "M")]
panel["month"] = panel["month"].astype(str)
panel["date"] = panel["date"].dt.strftime("%Y-%m-%d")
panel["prior_date"] = panel["prior_date"].dt.strftime("%Y-%m-%d")

cols = ["month", "ticker", "permaticker", "prior_date", "date",
        "closeunadj", "marketcap", "pb", "pe", "ps", "evebitda", "ret",
        "siccode", "famaindustry", "industry", "sector",
        "delisting_return", "basis"]
panel = panel[cols].sort_values(["month", "ticker"]).reset_index(drop=True)

out = "/Users/kerryback/repos/mgmt638/data/sharadar_monthly_panel.csv"
panel.to_csv(out, index=False)

print()
print(f"saved {out}")
print(f"shape {panel.shape}")
print(f"months {panel['month'].min()} to {panel['month'].max()}, {panel['ticker'].nunique():,} tickers")
print()
print(panel.head(3).to_string())
print()
print("non-null counts:")
print(panel[["closeunadj","marketcap","pb","pe","ps","evebitda","ret","siccode","famaindustry","industry","sector"]].notna().sum().to_string())
