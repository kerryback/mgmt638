"""Monthly panel for session 4, built the shift/ffill way.

The recipe, in order:

  1. multiples from `daily` on the last trading day of each month -> that month
  2. groupby ticker, shift forward 1, so month t carries month t-1's multiples
  3. closeadj from `sep` on the last trading day of each month -> that month
  4. groupby ticker, pct_change on closeadj -> the return over month t
  5. 10-K numbers land in the month of their `datekey`, then groupby ticker, ffill

Every shift, pct_change and ffill is grouped by ticker, and they all run on a
DENSE month grid -- one row per ticker per month between its first and last
observation. Without the dense grid, shift(1) means "one row back", which is one
month only if no month is missing.
"""
import sys
sys.path.insert(0, "/Users/kerryback/repos/skills/plugins/finance-data-augmented/skills/finance-data/scripts")
from sharadar_db import query, query_years, delisting_returns
import pandas as pd, numpy as np

PRICE_START, PRICE_END = 2014, 2026     # 2014 only supplies the Dec-2014 lag
FILING_START = 2012                     # deep enough that Jan-2015 has a prior 10-K
FIRST_MONTH = pd.Period("2015-01", "M")

MULTIPLES = ["marketcap", "ev", "pb", "pe", "ps", "evebitda"]
FUNDAMENTALS = [
    "datekey", "calendardate", "reportperiod",
    "revenueusd", "revenue_prev", "netinccmnusd", "ebitdausd", "equityusd",
    "assets", "debtusd", "ncfo", "fcf", "capex", "rnd", "sbcomp",
    "netmargin", "grossmargin", "ebitdamargin", "assetturnover",
    "roe", "roa", "roic", "de", "currentratio", "payoutratio", "divyield",
]

SEP_SQL = """
WITH me AS (
  SELECT ticker, date::DATE AS date, closeadj, closeunadj,
         ROW_NUMBER() OVER (PARTITION BY ticker, DATE_TRUNC('month', date::DATE)
                            ORDER BY date::DATE DESC) AS rn
  FROM sep
  WHERE date::DATE >= '{year}-01-01' AND date::DATE < '{next_year}-01-01'
)
SELECT ticker, CAST(date AS VARCHAR) AS date, closeadj, closeunadj
FROM me WHERE rn = 1
"""

DAILY_SQL = """
WITH me AS (
  SELECT ticker, date::DATE AS date, marketcap, ev, pb, pe, ps, evebitda,
         ROW_NUMBER() OVER (PARTITION BY ticker, DATE_TRUNC('month', date::DATE)
                            ORDER BY date::DATE DESC) AS rn
  FROM daily
  WHERE date::DATE >= '{year}-01-01' AND date::DATE < '{next_year}-01-01'
)
SELECT ticker, CAST(date AS VARCHAR) AS date, marketcap, ev, pb, pe, ps, evebitda
FROM me WHERE rn = 1
"""

print("pulling month-end prices ...", flush=True)
sep = query_years(SEP_SQL, PRICE_START, PRICE_END)
print("pulling month-end multiples ...", flush=True)
dly = query_years(DAILY_SQL, PRICE_START, PRICE_END)
for df in (sep, dly):
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")
print(f"  sep {len(sep):,} rows, daily {len(dly):,} rows", flush=True)

# ------------------------------------------------------- dense month grid --
# One row per ticker per month between its first and last month-end price.
# shift() and ffill() both count ROWS, so the grid has to have no holes.
span = sep.groupby("ticker")["month"].agg(["min", "max"])
grid = pd.DataFrame({
    "ticker": np.repeat(span.index.values, (span["max"] - span["min"]).apply(lambda x: x.n) + 1),
    "month": np.concatenate([pd.period_range(a, b, freq="M").to_numpy()
                             for a, b in zip(span["min"], span["max"])]),
})
grid["month"] = grid["month"].astype("period[M]")
grid = grid.sort_values(["ticker", "month"]).reset_index(drop=True)
print(f"  dense grid: {len(grid):,} ticker-months, {grid.ticker.nunique():,} tickers", flush=True)

# ---- STEP 1 & 3: put each month's own month-end values in that month's row --
grid = grid.merge(dly[["ticker", "month", "date"] + MULTIPLES]
                    .rename(columns={"date": "multiple_date"}),
                  on=["ticker", "month"], how="left")
grid = grid.merge(sep[["ticker", "month", "date", "closeadj", "closeunadj"]],
                  on=["ticker", "month"], how="left")

g = grid.groupby("ticker", sort=False)

# ---- STEP 4: return over month t, from closeadj -----------------------------
grid["ret"] = g["closeadj"].pct_change()

# ---- STEP 2: shift the multiples forward one month --------------------------
# After this, month t's row holds the multiples printed at the end of month t-1,
# which is the instant before the return in the same row starts.
# The same shift also gives a clean LAGGED price. closeadj/closeunadj in a row
# are the END of the return month -- contemporaneous with ret, so they are not
# usable as a filter. prior_closeunadj is, which is what a penny-stock screen
# needs. prior_date comes off `sep`, not `daily`, so it is populated whenever the
# prior month traded even if `daily` has no row.
shifted = g[MULTIPLES + ["multiple_date", "date", "closeadj", "closeunadj"]].shift(1)
grid[MULTIPLES] = shifted[MULTIPLES]
grid["prior_date"]       = shifted["date"]
grid["prior_closeadj"]   = shifted["closeadj"]
grid["prior_closeunadj"] = shifted["closeunadj"]
grid = grid.drop(columns=["multiple_date"])

# ------------------------------------------------------------- 10-K data ----
# ARY, not MRY: ARY is as-originally-reported and its `datekey` is the real SEC
# filing date. MRY is restated and copies the period end into datekey.
print("pulling annual filings (ARY) ...", flush=True)
fun = query(f"""
SELECT ticker, datekey, calendardate, reportperiod,
       revenueusd, netinccmnusd, ebitdausd, equityusd, assets, debtusd,
       ncfo, fcf, capex, rnd, sbcomp,
       netmargin, grossmargin, ebitdamargin, assetturnover,
       roe, roa, roic, de, currentratio, payoutratio, divyield
FROM sf1
WHERE dimension = 'ARY' AND datekey >= '{FILING_START}-01-01'
""")
fun["datekey"] = pd.to_datetime(fun["datekey"])
fun = fun.sort_values(["ticker", "datekey"]).reset_index(drop=True)
print(f"  {len(fun):,} filings, {fun.ticker.nunique():,} tickers", flush=True)

# last year's revenue is the PREVIOUS FILING, on the filing clock -- never a
# 12-month calendar shift, because filings are not evenly spaced.
fun["revenue_prev"] = fun.groupby("ticker")["revenueusd"].shift(1)

# ---- STEP 5a: each filing lands in the month of its datekey -----------------
fun["month"] = fun["datekey"].dt.to_period("M")
fun = fun.drop_duplicates(subset=["ticker", "month"], keep="last")   # two in one month -> the later
grid = grid.merge(fun[["ticker", "month"] + FUNDAMENTALS], on=["ticker", "month"], how="left")

# ---- STEP 5b: carry it forward until the next filing arrives ----------------
# ffill only. bfill here would reach into the future and is the look-ahead bug.
grid[FUNDAMENTALS] = grid.groupby("ticker", sort=False)[FUNDAMENTALS].ffill()

# ---- STEP 5c: then shift forward one month ----------------------------------
# The ffill alone puts a 10-K into the month it was FILED, and that month's
# return started before the filing existed. One more grouped shift moves it to
# the first month that opens after the filing. Grouped again, deliberately:
# .ffill().shift(1) on the result of a groupby would shift across ticker
# boundaries and hand each ticker the last row of the one before it.
grid[FUNDAMENTALS] = grid.groupby("ticker", sort=False)[FUNDAMENTALS].shift(1)

grid["filing_age_days"] = (grid["month"].dt.to_timestamp() - grid["datekey"]).dt.days

# ------------------------------------------------------ derived features ----
grid["growth"]   = grid.revenueusd / grid.revenue_prev - 1
grid["capexint"] = -grid.capex / grid.revenueusd
grid["rndint"]   = grid.rnd / grid.revenueusd
grid = grid.replace([np.inf, -np.inf], np.nan)

# ---------------------------------------------------- delisting returns -----
dl = delisting_returns()
last_month = grid.dropna(subset=["closeadj"]).groupby("ticker")["month"].max().rename("final_month")
dl = dl.merge(last_month, left_on="ticker", right_index=True, how="inner")
dl = dl[["ticker", "final_month", "delisting_return"]]
grid = grid.merge(dl, left_on=["ticker", "month"],
                  right_on=["ticker", "final_month"], how="left")
hit = grid["delisting_return"].notna() & grid["ret"].notna()
grid.loc[hit, "ret"] = (1 + grid.loc[hit, "ret"]) * (1 + grid.loc[hit, "delisting_return"]) - 1
print(f"  delisting return applied to {int(hit.sum()):,} ticker-months", flush=True)

# ------------------------------------------------------- classifications ----
# `tickers` carries only the CURRENT classification -- a company that changed
# SIC code wears today's code in 2015. Sharadar ships no history here.
tk = query("""
SELECT ticker, permaticker, name, exchange, siccode, sicsector, sicindustry,
       famaindustry, sector, industry, scalemarketcap, scalerevenue, location
FROM tickers
""")
grid = grid.merge(tk, on="ticker", how="left")

sic4 = grid.siccode.map(lambda v: f"{int(v):04d}" if pd.notna(v) else None).astype("object")
sic4 = sic4.where(sic4.map(lambda v: isinstance(v, str)), None)
grid["sic4"] = sic4
grid["sic3"] = sic4.map(lambda s: s[:3] if isinstance(s, str) else None)
grid["sic2"] = sic4.map(lambda s: s[:2] if isinstance(s, str) else None)

# ------------------------------------------------------- shape and save -----
grid = grid[grid["month"] >= FIRST_MONTH]
grid = grid[grid["ret"].notna()]                   # drop grid rows with no traded return
last = grid["month"].max()
if grid.loc[grid.month == last, "date"].max() < last.end_time - pd.Timedelta(days=3):
    print(f"  dropping incomplete final month {last}", flush=True)
    grid = grid[grid["month"] < last]

# Only lagged prices survive into the file. closeadj and the raw month-end
# closeunadj are contemporaneous with `ret`, so keeping them invites a filter
# built on the outcome. The lagged unadjusted close takes the name `closeunadj`.
grid = grid.drop(columns=["closeadj", "closeunadj", "prior_closeadj"])
grid = grid.rename(columns={"prior_closeunadj": "closeunadj"})

grid["month"] = grid["month"].astype(str)
for c in ("date", "prior_date", "datekey"):
    grid[c] = pd.to_datetime(grid[c]).dt.strftime("%Y-%m-%d")

# `date` and `prior_date` were scaffolding for checking the alignment; `month`
# is the identifier, and every column but `ret` is dated the prior month end.
# The file carries only what a backtest reads: the return, the multiples, size,
# industry, and the ratios. Filing levels, filing dates, scale buckets and
# location are dropped -- the ratios built from the levels survive, and the
# feature set is then identical to session4.parquet.
cols = (["month", "ticker", "permaticker", "name", "exchange", "ret", "closeunadj"]
      + ["ps", "pe", "pb", "evebitda", "marketcap", "ev"]
      + ["revenueusd", "equityusd", "netinccmnusd", "ebitdausd"]
      + ["siccode", "sic4", "sic3", "sic2", "sicsector", "sicindustry",
         "famaindustry", "sector", "industry"]
      + ["filing_age_days"]
      + ["netmargin", "grossmargin", "ebitdamargin", "assetturnover", "roe", "roa", "roic",
         "de", "currentratio", "payoutratio", "divyield"]
      + ["growth", "capexint", "rndint"])
missing = set(cols) - set(grid.columns)
assert not missing, missing
out_df = grid[cols].sort_values(["month", "ticker"]).reset_index(drop=True)

out_df.to_parquet("session4_monthly.parquet", index=False, compression="zstd")
print()
print(f"saved session4_monthly.parquet  shape {out_df.shape}")
print(f"months {out_df.month.min()} to {out_df.month.max()}, {out_df.ticker.nunique():,} tickers")
print()
print("coverage:")
for c in ["ret","ps","pe","pb","evebitda","marketcap","netmargin","growth","sector"]:
    print(f"  {c:14s} {out_df[c].notna().sum():>9,}  ({out_df[c].notna().mean()*100:5.1f}%)")
