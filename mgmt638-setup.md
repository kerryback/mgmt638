# Data Hosting Plan: MotherDuck → Digital Ocean

## Context

- Data currently lives at MotherDuck (DuckDB-as-a-service).
- Daily workflow: download from another source, delete all tables, re-upload the
  data as parquet files.
- More data sources will be added over time.
- Considering whether Digital Ocean is a better home for the data.
- Likely to build a student lab (similar to the existing nspawn lab) for a
  different course that uses this data.

## What we're really doing

MotherDuck is just DuckDB-as-a-service. The current workflow — "drop everything,
re-upload parquet daily, read-only queries afterward" — is the canonical
DuckDB-over-object-storage pattern. There are no concurrent writers, no
transactions, and no need for an always-on database engine.

That means we don't need a "database server" at all; we need a place to park
parquet files and a query engine that reads them. The cheapest option is also
the best-fit option.

## Recommended setup: DO Spaces + DuckDB

DO Spaces is S3-compatible object storage. Pair it with DuckDB as the query
engine.

- Store the parquet files in a Spaces bucket. The daily refresh becomes "delete
  the old parquet objects, upload the new ones" — essentially identical to the
  current process, minus MotherDuck.
- Anyone (a script, an instructor, or a student) queries with plain DuckDB
  pointed at the bucket via `httpfs`:

  ```sql
  SELECT * FROM read_parquet('s3://your-bucket/prices/*.parquet');
  ```

- Cost: Spaces is $5/mo for 250 GB storage + 1 TB egress. MotherDuck's paid
  tiers cost meaningfully more once the free tier is outgrown.

This keeps the entire mental model (parquet files, wipe-and-replace) and removes
the vendor dependency.

## Why this fits the student-lab plan

The new course's lab would be built the same way as the existing one (nspawn
containers on a DO droplet). Co-locating the data on DO Spaces means:

- Students query the bucket from inside their containers with zero per-student
  database accounts or API keys to manage (unlike MotherDuck tokens).
- Egress from a DO droplet to DO Spaces in the same region is free and fast.
- Read-only Spaces keys can be issued, or the parquet can be baked into the base
  container template if the dataset is small.

## Tradeoffs

- DuckDB-on-Spaces is single-engine: each query spins up DuckDB in the
  client/container. With 40+ students each scanning large parquet, that's a lot
  of repeated S3 reads. Fine for typical datasets; if files are large, partition
  them (by date/ticker) so queries can prune. MotherDuck does server-side
  compute, so it offloads that — but you pay for it.
- Lose MotherDuck's "shared cloud database" niceties (persistent attached DB,
  sharing, web UI). For a course, that's rarely missed.
- If genuine concurrent writes or a long-lived relational store are ever needed
  for "other data," DO Managed Postgres ($15/mo) is the fallback — but not the
  starting point.

## Recommendation

Move to DO Spaces + DuckDB. It matches the current workflow almost exactly, is
cheaper, and slots cleanly into the lab architecture already in use. Keep
MotherDuck only if server-side query compute is specifically wanted so student
containers don't each do the scanning.

## Open questions that could sharpen (or change) the plan

- How big is the dataset, and how fast is it growing? Under ~a few GB makes
  everything trivial and even local-disk-on-droplet viable.
- Will students query concurrently, and how heavy are the queries? Heavy
  concurrent scans are the one case where MotherDuck's server-side compute earns
  its cost.
- Is the "other data" to be added also batch/read-only, or does any of it need
  live writes?
