"""Monthly cross-sectional signal panel for session 7.

Same contract as session4_monthly.parquet, and built the same shift/ffill way:
one row per ticker-month, `ret` is the total return EARNED OVER month t, and
every other column is dated the close of month t-1. That is what makes the file
safe to regress on -- there is no column in a row that a trader standing at the
start of the month could not have known.

The recipe, in order:

  1. per ticker-month aggregates from `sep` (month-end price, dollar volume,
     daily-return vol, Amihud) -> that month
  2. multiples from `daily` on the last trading day of each month -> that month
  3. groupby ticker, pct_change on closeadj -> the return over month t
  4. groupby ticker, shift forward 1, so month t carries month t-1's prices,
     multiples and volume statistics
  5. momentum and the trailing-vol window are built from lagged prices directly
  6. 10-K numbers land in the month of their `datekey`, then groupby ticker,
     ffill, then one more shift

Every shift, pct_change, rolling and ffill is grouped by ticker, and they all run
on a DENSE month grid -- one row per ticker per month between its first and last
observation. Without the dense grid, shift(1) means "one row back", which is one
month only if no month is missing.

Two Sharadar facts this file leans on, both verified in `indicators`:
  - `volume` AND `close` are split-adjusted, so volume*close is the actual
    dollars traded and the split factor cancels. Raw share volume is NOT
    carried into the file: it is restated by later splits, so a 2015 row would
    wear a share count that reflects a 2020 split.
  - `sharesbas` is already adjusted for splits, so the issuance ratio is clean.
"""
import sys
sys.path.insert(0, "/Users/kerryback/repos/skills/plugins/finance-data-augmented/skills/finance-data/scripts")
from sharadar_db import query, query_years, delisting_returns
import pandas as pd, numpy as np

# --live-only writes ONLY session7_live.parquet and leaves session7_monthly.parquet
# alone. Use it to refresh the app's input without disturbing the historical panel
# the fitted models were trained on -- a rebuild would pick up Sharadar restatements
# and silently move the ground under `session7_model_full.joblib`.
LIVE_ONLY = "--live-only" in sys.argv

# The bundle itself begins 2000-01-03 -- there is no earlier data to ask for.
# 2000 is burned: momentum needs 13 months of prices, and the year-over-year
# fundamentals (asset growth, issuance) need a PREVIOUS filing,
# which for most firms does not exist until their 2001 10-K. Momentum is
# therefore first available in 2001-02 and the YoY columns fill in through 2001.
PRICE_START, PRICE_END = 2000, 2026
FILING_START = 2000
FIRST_MONTH = pd.Period("2001-01", "M")

MULTIPLES = ["marketcap", "ev", "pb", "pe", "ps", "evebitda"]
MONTHLY_PX = ["dollarvol", "volatility", "illiquidity", "ndays"]

# Filing-level columns carried onto the grid. Levels used only to build the
# ratios are dropped before the file is written.
FUNDAMENTALS = [
    "datekey", "roe", "divyield",
    "accruals", "assetgrowth", "issuance", "grossprofitability",
]

# One pass over `sep` per year, aggregated server-side. Pulling 33M daily rows
# to pandas would not finish; this returns ~1M ticker-months a year.
#
# The window reaches back into the prior December so the LAG that makes daily
# returns is not broken at the January boundary -- without it every ticker
# loses its first trading day of each year and January's vol is computed from
# one observation too few.
SEP_SQL = """
WITH px AS (
  SELECT s.ticker, s.date::DATE AS date, s.closeadj, s.closeunadj, s.close, s.volume
  FROM sep s
  WHERE s.date::DATE >= '{prev_year}-12-01' AND s.date::DATE < '{next_year}-01-01'
),
r AS (
  SELECT p.*,
         p.closeadj / LAG(p.closeadj) OVER (PARTITION BY p.ticker ORDER BY p.date) - 1 AS dret
  FROM px p
),
y AS (
  SELECT r.*, DATE_TRUNC('month', r.date) AS m FROM r WHERE r.date >= '{year}-01-01'
),
agg AS (
  SELECT y.ticker, y.m,
         COUNT(*)                                   AS ndays,
         AVG(y.volume * y.close)                    AS dollarvol,
         STDDEV_SAMP(y.dret)                        AS volatility,
         AVG(CASE WHEN y.volume * y.close > 0
                  THEN abs(y.dret) / (y.volume * y.close) END) * 1e6 AS illiquidity
  FROM y GROUP BY 1, 2
),
me AS (
  SELECT y.ticker, y.date, y.m, y.closeadj, y.closeunadj,
         ROW_NUMBER() OVER (PARTITION BY y.ticker, y.m ORDER BY y.date DESC) AS rn
  FROM y
)
SELECT a.ticker, CAST(a.m AS VARCHAR) AS month, CAST(e.date AS VARCHAR) AS date,
       e.closeadj, e.closeunadj,
       a.ndays, a.dollarvol, a.volatility, a.illiquidity
FROM agg a JOIN me e ON e.ticker = a.ticker AND e.m = a.m AND e.rn = 1
"""

DAILY_SQL = """
WITH me AS (
  SELECT d.ticker, d.date::DATE AS date, d.marketcap, d.ev, d.pb, d.pe, d.ps, d.evebitda,
         ROW_NUMBER() OVER (PARTITION BY d.ticker, DATE_TRUNC('month', d.date::DATE)
                            ORDER BY d.date::DATE DESC) AS rn
  FROM daily d
  WHERE d.date::DATE >= '{year}-01-01' AND d.date::DATE < '{next_year}-01-01'
)
SELECT ticker, CAST(date AS VARCHAR) AS date, marketcap, ev, pb, pe, ps, evebitda
FROM me WHERE rn = 1
"""


def per_year(sql, start, end):
    """query_years() only formats {year}/{next_year}; SEP_SQL also needs {prev_year}."""
    frames = []
    for year in range(start, end + 1):
        frames.append(query(sql.format(year=year, next_year=year + 1, prev_year=year - 1)))
    return pd.concat(frames, ignore_index=True)


print("pulling month-end prices and volume statistics ...", flush=True)
sep = per_year(SEP_SQL, PRICE_START, PRICE_END)
sep["date"] = pd.to_datetime(sep["date"])
sep["month"] = pd.PeriodIndex(sep["month"], freq="M")

print("pulling month-end multiples ...", flush=True)
dly = query_years(DAILY_SQL, PRICE_START, PRICE_END)
dly["date"] = pd.to_datetime(dly["date"])
dly["month"] = dly["date"].dt.to_period("M")
print(f"  sep {len(sep):,} ticker-months, daily {len(dly):,} ticker-months", flush=True)

# ------------------------------------------------------- dense month grid --
# One row per ticker per month between its first and last month-end price.
# shift(), rolling() and ffill() all count ROWS, so the grid has to have no holes.
span = sep.groupby("ticker")["month"].agg(["min", "max"])
grid = pd.DataFrame({
    "ticker": np.repeat(span.index.values, (span["max"] - span["min"]).apply(lambda x: x.n) + 1),
    "month": np.concatenate([pd.period_range(a, b, freq="M").to_numpy()
                             for a, b in zip(span["min"], span["max"])]),
})
grid["month"] = grid["month"].astype("period[M]")
grid = grid.sort_values(["ticker", "month"]).reset_index(drop=True)
print(f"  dense grid: {len(grid):,} ticker-months, {grid.ticker.nunique():,} tickers", flush=True)

# ---- STEPS 1 & 2: each month's own month-end values in that month's row -----
grid = grid.merge(dly[["ticker", "month"] + MULTIPLES], on=["ticker", "month"], how="left")
grid = grid.merge(sep[["ticker", "month", "date", "closeadj", "closeunadj"] + MONTHLY_PX],
                  on=["ticker", "month"], how="left")

g = grid.groupby("ticker", sort=False)

# ---- STEP 3: return over month t, from closeadj -----------------------------
grid["ret"] = g["closeadj"].pct_change()

# ---- STEP 5: momentum, reversal and trailing volatility ---------------------
# momentum is the 11-month return ending at the close of month t-2. The skipped
# month t-1 is deliberate: at a one-month horizon the same stocks reverse, and
# leaving it in mixes the two effects. It is carried separately as ret_1m.
grid["momentum"] = g["closeadj"].shift(2) / g["closeadj"].shift(13) - 1
grid["ret_1m"] = g["ret"].shift(1)
lagged_ret = g["ret"].shift(1)
grid["volatility_12m"] = (lagged_ret.groupby(grid["ticker"], sort=False)
                                    .rolling(12, min_periods=6).std()
                                    .reset_index(level=0, drop=True))

# ---- STEP 4: shift everything month-end forward one month -------------------
# After this, month t's row holds what was printed at the close of month t-1,
# which is the instant before the return in the same row starts. closeadj and
# closeunadj as merged are the END of the return month -- contemporaneous with
# `ret`, so they are not usable as a filter. The lagged unadjusted close is,
# which is what a penny-stock screen needs.
LAGGABLE = MULTIPLES + MONTHLY_PX + ["date", "closeadj", "closeunadj"]
shifted = g[LAGGABLE].shift(1)
grid[MULTIPLES + MONTHLY_PX] = shifted[MULTIPLES + MONTHLY_PX]
grid["prior_date"]       = shifted["date"]
grid["prior_closeunadj"] = shifted["closeunadj"]

# ------------------------------------------------------------- 10-K data ----
# ARY, not MRY: ARY is as-originally-reported and its `datekey` is the real SEC
# filing date. MRY is restated and copies the period end into datekey.
print("pulling annual filings (ARY) ...", flush=True)
fun = query(f"""
SELECT ticker, datekey, assets, assetsavg, netinc, ncfo, gp, sharesbas, roe, divyield
FROM sf1
WHERE dimension = 'ARY' AND datekey >= '{FILING_START}-01-01'
""")
fun["datekey"] = pd.to_datetime(fun["datekey"])
fun = fun.sort_values(["ticker", "datekey"]).reset_index(drop=True)
print(f"  {len(fun):,} filings, {fun.ticker.nunique():,} tickers", flush=True)

# Year-over-year changes run on the FILING CLOCK -- the previous filing, never a
# 12-month calendar shift. Filings are not evenly spaced, and one late 10-K would
# silently turn asset growth into a two-year number.
fg = fun.groupby("ticker")
fun["assets_prev"] = fg["assets"].shift(1)
fun["shares_prev"] = fg["sharesbas"].shift(1)

fun["assetgrowth"] = fun.assets / fun.assets_prev - 1
fun["issuance"] = np.log(fun.sharesbas / fun.shares_prev)
fun["grossprofitability"] = fun.gp / fun.assets
# Sloan (1996) accruals: the part of earnings that is not cash. Scaled by average
# assets, falling back to the two-filing average when `assetsavg` is missing.
denom = fun["assetsavg"].where(fun["assetsavg"] > 0, (fun.assets + fun.assets_prev) / 2)
fun["accruals"] = (fun.netinc - fun.ncfo) / denom

# ---- STEP 6a: each filing lands in the month of its datekey -----------------
fun["month"] = fun["datekey"].dt.to_period("M")
fun = fun.drop_duplicates(subset=["ticker", "month"], keep="last")   # two in one month -> the later
grid = grid.merge(fun[["ticker", "month"] + FUNDAMENTALS], on=["ticker", "month"], how="left")

# ---- STEP 6b: carry it forward until the next filing arrives ----------------
# ffill only. bfill here would reach into the future and is the look-ahead bug.
grid[FUNDAMENTALS] = grid.groupby("ticker", sort=False)[FUNDAMENTALS].ffill()

# ---- STEP 6c: then shift forward one month ----------------------------------
# The ffill alone puts a 10-K into the month it was FILED, and that month's
# return started before the filing existed. One more grouped shift moves it to
# the first month that opens after the filing. Grouped again, deliberately:
# .ffill().shift(1) on the result of a groupby would shift across ticker
# boundaries and hand each ticker the last row of the one before it.
grid[FUNDAMENTALS] = grid.groupby("ticker", sort=False)[FUNDAMENTALS].shift(1)

grid["filing_age_days"] = (grid["month"].dt.to_timestamp() - grid["datekey"]).dt.days
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
       famaindustry, sector, industry
FROM tickers
""")
grid = grid.merge(tk, on="ticker", how="left")

sic4 = grid.siccode.map(lambda v: f"{int(v):04d}" if pd.notna(v) else None).astype("object")
sic4 = sic4.where(sic4.map(lambda v: isinstance(v, str)), None)
grid["sic4"] = sic4
grid["sic3"] = sic4.map(lambda s: s[:3] if isinstance(s, str) else None)
grid["sic2"] = sic4.map(lambda s: s[:2] if isinstance(s, str) else None)

# ------------------------------------------------------- shape and save -----
COLS = (["month", "ticker", "permaticker", "name", "exchange", "ret"]
      + ["momentum", "ret_1m", "volatility", "volatility_12m", "illiquidity",
         "dollarvol", "ndays", "closeunadj"]
      + ["marketcap", "pb", "ps", "pe", "ev", "evebitda"]
      + ["roe", "accruals", "assetgrowth", "issuance", "grossprofitability",
         "divyield", "filing_age_days"]
      + ["siccode", "sic4", "sic3", "sic2", "sicsector", "sicindustry",
         "famaindustry", "sector", "industry"])

grid_all = grid.copy()                             # before any return-based filtering
grid = grid[grid["month"] >= FIRST_MONTH]
grid = grid[grid["ret"].notna()]                   # drop grid rows with no traded return
last = grid["month"].max()
if grid.loc[grid.month == last, "date"].max() < last.end_time - pd.Timedelta(days=3):
    print(f"  dropping incomplete final month {last}", flush=True)
    grid = grid[grid["month"] < last]

# ----------------------------------------------------------- live month ----
# The month the recommender app has to predict for: the one that OPENS after the
# last complete return month. Its row already exists in the dense grid, built by
# exactly the same shifts as every historical row, so every feature is dated the
# close of the previous month and nothing in it is unknowable today.
#
# `ret` is deleted rather than carried. The grid does hold a value for it -- a
# partial-month return from the first of the month to whatever the latest price
# is -- and that number is the single most dangerous column in this file. It is
# a realized return the app must never see and must never be scored against.
LIVE_MONTH = grid["month"].max() + 1
live = grid_all[grid_all["month"] == LIVE_MONTH].copy()
live = live.drop(columns=["ret"])
print(f"  live month {LIVE_MONTH}: {len(live):,} ticker rows", flush=True)

def finish(frame):
    """The rename/drop/format block, applied identically to both outputs."""
    frame = frame.rename(columns={"prior_closeunadj": "closeunadj_lag"})
    frame = frame.drop(columns=["closeadj", "closeunadj"])
    frame = frame.rename(columns={"closeunadj_lag": "closeunadj"})
    frame["month"] = frame["month"].astype(str)
    for c in ("date", "prior_date", "datekey"):
        frame[c] = pd.to_datetime(frame[c]).dt.strftime("%Y-%m-%d")
    return frame

live = finish(live)
live_cols = [c for c in COLS if c != "ret"]
missing_live = set(live_cols) - set(live.columns)
assert not missing_live, missing_live
live[live_cols].sort_values("ticker").reset_index(drop=True).to_parquet(
    "session7_live.parquet", index=False, compression="zstd")
print(f"\nsaved session7_live.parquet  month {LIVE_MONTH}  "
      f"{len(live):,} rows, no `ret` column")

if LIVE_ONLY:
    print("--live-only: session7_monthly.parquet left untouched")
    raise SystemExit(0)

grid = grid.rename(columns={"prior_closeunadj": "closeunadj_lag"})
grid = grid.drop(columns=["closeadj", "closeunadj"])
grid = grid.rename(columns={"closeunadj_lag": "closeunadj"})

grid["month"] = grid["month"].astype(str)
for c in ("date", "prior_date", "datekey"):
    grid[c] = pd.to_datetime(grid[c]).dt.strftime("%Y-%m-%d")

# `date` and `prior_date` were scaffolding for checking the alignment. `month`
# is the identifier, and every column but `ret` is dated the prior month end.
# The file is left RAW: nothing is winsorized and nothing is screened out. It
# carries the columns a screen needs -- closeunadj, marketcap, dollarvol,
# exchange -- so filtering stays a decision the student makes and can see.
cols = COLS
missing = set(cols) - set(grid.columns)
assert not missing, missing
out_df = grid[cols].sort_values(["month", "ticker"]).reset_index(drop=True)

out_df.to_parquet("session7_monthly.parquet", index=False, compression="zstd")
print()
print(f"saved session7_monthly.parquet  shape {out_df.shape}")
print(f"months {out_df.month.min()} to {out_df.month.max()}, {out_df.ticker.nunique():,} tickers")
print()
print("coverage:")
for c in cols:
    if c in ("month", "ticker"):
        continue
    print(f"  {c:20s} {out_df[c].notna().sum():>9,}  ({out_df[c].notna().mean()*100:5.1f}%)")
