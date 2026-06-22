# MGMT638 Data Architecture: Bucket Layout & Ingestion

Companion to `mgmt638-setup.md`. That doc established the hosting decision
(DO Spaces + DuckDB, querying parquet via `httpfs` from student nspawn
containers). This doc specifies the concrete bucket layout, the partitioning
scheme, and the one-time ingestion pipeline for each dataset.

## Two classes of data

The lab holds data with two very different lifecycles. Keeping them under
separate prefixes is a safety boundary, not just organization: the daily refresh
script must only ever touch the live prefixes and can never reach the static
corpora.

| Class | Prefix | Lifecycle | Source |
|-------|--------|-----------|--------|
| Live | `prices/`, `fundamentals/` | Daily wipe-and-replace | Existing download workflow |
| Static | `fnspid/` | Load once, never refreshed | HuggingFace `Zihan1004/FNSPID` — parquet, 29.6 GB, 10M+ news rows |
| Static | `stocktwits/` | Load once, never refreshed | Public S3 `s3://stocktwits-nyu/dataset/v1/data/csv` — CSV, 550M+ posts |

## Bucket layout

One bucket, four top-level prefixes:

```
s3://<bucket>/
├── prices/                 # live, refreshed daily
│   └── *.parquet
├── fundamentals/           # live, refreshed daily
│   └── *.parquet
├── fnspid/                 # static, news corpus
│   └── news/symbol=<T>/year=<Y>/*.parquet
└── stocktwits/             # static
    ├── symbol_sentiments/symbol=<T>/year=<Y>/*.parquet
    ├── sentiments/symbol=<T>/year=<Y>/*.parquet
    ├── symbols/symbol=<T>/year=<Y>/*.parquet
    ├── msg_info/...         # include only if needed
    ├── messages/...         # large; include only if needed (see below)
    └── feature_wo_messages/...
```

## Partitioning principle

Partition every static table by `symbol` first, then `year`. In a
stock-analysis course students always start from a ticker (or a small set), so
this lets DuckDB prune to a few MB per query instead of scanning the whole
corpus. This is the single decision that makes Spaces + DuckDB viable for the
large StockTwits corpus instead of forcing a paid server-side engine.

```sql
-- reads only the AAPL / 2020 slice
SELECT *
FROM read_parquet('s3://<bucket>/stocktwits/symbol_sentiments/symbol=AAPL/year=2020/*.parquet');
```

Partitioning is done once (static data), so it is worth doing carefully.

## Dataset 1: FNSPID

Financial News and Stock Price Integration Dataset. The HuggingFace
`Zihan1004/FNSPID` release is the news corpus: 10M+ articles, already in
parquet, 29.6 GB total. (The original project also ships price history
separately, but the lab already has live prices, so only the news is hosted
here.) Coverage is US tickers, sourced primarily from Benzinga; the full release
spans roughly 1999–2023, though the HuggingFace preview only exposes a
2019–2020 slice — confirm the actual min/max `Date` after download.

Schema (one table, `train` split):

| Column | Type | Notes |
|--------|------|-------|
| `Date` | string | publication timestamp; cast to DATE/TIMESTAMP |
| `Article_title` | string | headline |
| `Stock_symbol` | string | ticker — the partition key |
| `Url`, `Publisher`, `Author` | string | source metadata |
| `Article` | string | full body text (nullable) |
| `Lsa_summary`, `Luhn_summary`, `Textrank_summary`, `Lexrank_summary` | string | precomputed summaries (nullable) |

Because it is already parquet, ingestion is just a re-partition, not a format
conversion:

1. Download the parquet from HuggingFace (`huggingface-cli download` or the hub
   API).
2. Re-partition by ticker/year with DuckDB.
3. Upload to `s3://<bucket>/fnspid/news/`.

```sql
COPY (
  SELECT *, year(TRY_CAST(Date AS TIMESTAMP)) AS year
  FROM read_parquet('fnspid_download/*.parquet')
)
TO 'fnspid/news' (FORMAT parquet, PARTITION_BY (Stock_symbol, year), OVERWRITE_OR_IGNORE);
```

Note the known data-quality wrinkle: the HuggingFace viewer reports a schema
error on some non-English text (e.g. a Russian `Publisher` value). `TRY_CAST`
and tolerant reads handle most of this; spot-check after loading.

## Dataset 2: StockTwits 2008–2022

550M+ social-media posts about stocks. The repo holds only analysis notebooks;
the data itself is a public, no-credentials S3 bucket as CSV, split across six
subdirectories joinable on `message_id`:

- `symbol_sentiments/` — ticker + bullish/bearish (highest value for the course)
- `sentiments/` — sentiment-labeled messages
- `symbols/` — messages with ticker tags
- `messages/` — raw post bodies (the bulk of the size)
- `msg_info/`, `feature_wo_messages/` — derived / non-content features

The access doc does not publish per-column schemas or a total size — confirm
both by listing the bucket and reading a sample file before partitioning.

Ingestion (one time):

1. Pull from the public source bucket (no AWS credentials needed):
   ```bash
   aws s3 sync --no-sign-request \
     s3://stocktwits-nyu/dataset/v1/data/csv/symbol_sentiments/ ./symbol_sentiments/
   ```
2. Convert each subdirectory to parquet, partitioned by `symbol`/`year`.
3. Upload to `s3://<bucket>/stocktwits/<subdir>/`.

What to include vs. omit: `messages/` (raw text) is the largest component. Host
it only if students will run their own NLP on post text. If the course only
needs ticker-level sentiment, host `symbol_sentiments/` and `sentiments/` and
omit raw bodies — this cuts storage and egress dramatically.

## Cost and load notes

- Storage: DO Spaces is $5/mo for 250 GB. Both static corpora plus live data fit,
  though StockTwits with raw `messages/` could approach the limit — another
  reason to omit raw bodies unless needed.
- Egress: 1 TB/mo included. The risk is 40+ students each scanning a large
  corpus from their containers. Partition-by-ticker pruning is what keeps this
  in bounds; without it, repeated full scans of StockTwits would blow the
  allowance. (This is the "heavy concurrent scans" case `mgmt638-setup.md`
  flags as the one scenario where server-side compute would earn its cost.)
- In-region droplet → Spaces egress is free and fast.

## Open items

- Confirm FNSPID's actual `Date` min/max after download (HuggingFace preview
  only showed 2019–2020; the full release is reportedly broader).
- Confirm StockTwits per-column schemas and total size by listing the bucket and
  sampling a file from each subdirectory.
- Decide whether StockTwits raw post bodies (`messages/`) are hosted, since that
  drives whether storage stays well under the 250 GB Spaces tier.
- Decide whether the live `prices`/`fundamentals` data should also be partitioned
  by ticker for consistency, or left flat (it is small and refreshed daily).
