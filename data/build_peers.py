"""Annual peer sets: for each firm at each Jan 1, peers within a factor of 2 on
market cap (measured the last trading day of the prior year), widening through a
classification hierarchy until at least 10 peers are found.

Hierarchy, cumulative — each level ADDS to the set built so far:
    sic4 -> sic3 -> industry -> sic2 -> famaindustry -> sector
Stops at the first level reaching MIN_PEERS. A firm that never gets there is
recorded with whatever it had and level='insufficient'.
"""
import duckdb, numpy as np, pandas as pd

PANEL = "/Users/kerryback/repos/mgmt638/data/trading_multiples.parquet"
OUT   = "/Users/kerryback/repos/mgmt638/data/peers_annual.parquet"
MIN_PEERS = 10
BAND = 2.0                       # peer mktcap in [mc/2, mc*2]
LEVELS = ["sic4", "sic3", "industry", "sic2", "famaindustry", "sector"]

con = duckdb.connect()
p = con.execute(f"SELECT * FROM '{PANEL}' WHERE month LIKE '%-01'").fetchdf()
p["year"] = p.month.str[:4].astype(int)

def band_peers(sub, key):
    """Within each group of `key`, peers whose marketcap is within BAND. Returns
    dict ticker -> set(peer tickers). Contiguous slice on a sorted array."""
    res = {}
    for _, g in sub.groupby(key, sort=False):
        if len(g) < 2: continue
        g = g.sort_values("marketcap")
        mc = g.marketcap.to_numpy(); tk = g.ticker.to_numpy()
        lo = np.searchsorted(mc, mc / BAND, side="left")
        hi = np.searchsorted(mc, mc * BAND, side="right")
        for i in range(len(g)):
            s = set(tk[lo[i]:hi[i]]); s.discard(tk[i])
            if s: res[tk[i]] = s
    return res

rows = []
for year, x in p.groupby("year"):
    x = x[(x.marketcap.notna()) & (x.marketcap > 0)].copy()
    sic = x.siccode.astype("Int64").astype(str).where(x.siccode.notna())
    x["sic4"], x["sic3"], x["sic2"] = sic, sic.str[:3], sic.str[:2]

    peers  = {t: set() for t in x.ticker}
    level  = {t: None for t in x.ticker}
    for lv in LEVELS:
        sub = x[x[lv].notna() & (x[lv].astype(str).str.strip() != "")]
        found = band_peers(sub, lv)
        for t, s in found.items():
            if level[t] is None:
                peers[t] |= s
        for t in x.ticker:
            if level[t] is None and len(peers[t]) >= MIN_PEERS:
                level[t] = lv
        if all(v is not None for v in level.values()):
            break

    for t in x.ticker:
        lv = level[t] or "insufficient"
        for pt in sorted(peers[t]):
            rows.append((year, t, pt, lv))
    print(f"  {year}: {len(x):,} firms", flush=True)

peers_df = pd.DataFrame(rows, columns=["year", "ticker", "peer", "level"])
con.execute("CREATE TABLE pr AS SELECT * FROM peers_df")
con.execute(f"COPY pr TO '{OUT}' (FORMAT PARQUET, COMPRESSION SNAPPY)")
print(f"\nsaved {OUT}  rows={len(peers_df):,}")
