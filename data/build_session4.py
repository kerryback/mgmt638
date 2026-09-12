import sys
sys.path.insert(0, "/Users/kerryback/repos/skills/plugins/finance-data-augmented/skills/finance-data/scripts")
from sharadar_db import query
import pandas as pd, numpy as np

AS_OF = "2026-09-01"

SQL = f"""
WITH latest AS (
  SELECT ticker, MAX(datekey) AS dk
  FROM sf1 WHERE dimension = 'MRY'
  GROUP BY ticker
),
fun AS (
  SELECT s.ticker, s.datekey, s.calendardate, s.reportperiod,
         s.revenueusd, s.netmargin, s.grossmargin, s.ebitdamargin,
         s.assetturnover, s.roe, s.roa, s.roic, s.de, s.currentratio,
         s.capex, s.rnd, s.sbcomp, s.payoutratio, s.divyield,
         s.equityusd, s.assets, s.debtusd, s.ncfo, s.fcf, s.ebitdausd,
         s.netinccmnusd
  FROM sf1 s JOIN latest l ON s.ticker = l.ticker AND s.datekey = l.dk
  WHERE s.dimension = 'MRY'
),
prev AS (
  SELECT s.ticker, s.revenueusd AS revenue_prev, s.datekey AS datekey_prev,
         ROW_NUMBER() OVER (PARTITION BY s.ticker ORDER BY s.datekey DESC) AS rn
  FROM sf1 s JOIN latest l ON s.ticker = l.ticker
  WHERE s.dimension = 'MRY' AND s.datekey < l.dk
),
d AS (
  SELECT ticker, marketcap, ev, ps, pe, pb, evebitda
  FROM daily WHERE date = DATE '{AS_OF}'
)
SELECT
  t.ticker, t.permaticker, t.name, t.exchange,
  d.marketcap, d.ev, d.ps, d.pe, d.pb, d.evebitda,
  f.datekey, f.calendardate, f.reportperiod,
  f.revenueusd, p.revenue_prev, f.netinccmnusd, f.ebitdausd,
  f.netmargin, f.grossmargin, f.ebitdamargin,
  f.assetturnover, f.roe, f.roa, f.roic, f.de, f.currentratio,
  f.capex, f.rnd, f.sbcomp, f.payoutratio, f.divyield,
  f.equityusd, f.assets, f.debtusd, f.ncfo, f.fcf,
  t.siccode, t.sicsector, t.sicindustry,
  t.famaindustry, t.sector, t.industry,
  t.scalemarketcap, t.scalerevenue, t.location
FROM tickers t
JOIN d   ON d.ticker = t.ticker
JOIN fun f ON f.ticker = t.ticker
LEFT JOIN prev p ON p.ticker = t.ticker AND p.rn = 1
"""

df = query(SQL)
print("rows from join:", len(df))

# ---- SIC at three levels of aggregation ---------------------------------
# siccode arrives as a float; SIC codes are zero-padded four-digit strings
# (0100 Agricultural Production is not 100), so format before slicing.
sic4 = df.siccode.map(lambda v: f"{int(v):04d}" if pd.notna(v) else None).astype("object")
sic4 = sic4.where(sic4.map(lambda v: isinstance(v, str)), None)
df["sic4"] = sic4
df["sic3"] = sic4.map(lambda s: s[:3] if isinstance(s, str) else None)
df["sic2"] = sic4.map(lambda s: s[:2] if isinstance(s, str) else None)

# ---- the three derived features the session-4 deck uses -----------------
df["growth"]   = df.revenueusd / df.revenue_prev - 1
df["capexint"] = -df.capex / df.revenueusd      # Sharadar signs capex negative
df["rndint"]   = df.rnd / df.revenueusd
df = df.replace([np.inf, -np.inf], np.nan)

df["date"] = pd.Timestamp(AS_OF).date()

# Same feature set as session4_monthly.parquet. Each multiple ships with its own
# denominator -- revenue for ps, book equity for pb, net income for pe, EBITDA
# for evebitda -- so a multiple can always be taken apart. The remaining filing
# levels, the filing dates, the scale buckets and location are dropped.
order = (["ticker", "permaticker", "name", "exchange", "date"]
       + ["ps", "pe", "pb", "evebitda", "marketcap", "ev"]
       + ["revenueusd", "equityusd", "netinccmnusd", "ebitdausd"]
       + ["siccode", "sic4", "sic3", "sic2", "sicsector", "sicindustry",
          "famaindustry", "sector", "industry"]
       + ["netmargin", "grossmargin", "ebitdamargin", "assetturnover", "roe", "roa", "roic",
          "de", "currentratio", "payoutratio", "divyield"]
       + ["growth", "capexint", "rndint"])
missing = set(order) - set(df.columns)
assert not missing, missing
df = df[order]

df.to_parquet("session4.parquet", index=False)
print("saved session4.parquet", df.shape)
print()
print("distinct values per classification:")
for c in ["sic4","sic3","sic2","sicsector","sicindustry","famaindustry",
          "sector","industry","exchange"]:
    print(f"  {c:15s} {df[c].nunique():5d} groups   {df[c].isna().sum():4d} missing")
print()
print("multiples, non-missing and positive:")
for c in ["ps","pe","pb","evebitda"]:
    print(f"  {c:9s} {df[c].notna().sum():5d} present  {(df[c] > 0).sum():5d} positive  max {df[c].max():,.0f}")
print()
print("marketcap (raw, in $ millions):", df.marketcap.describe().round(1).to_dict())
