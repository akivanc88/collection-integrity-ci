# Data sources and attribution

Collection Integrity CI ships built-in adapters for three museum open-data programs. This document
records their provenance, licenses, what each adapter maps, and the honest limitations. It also
describes the bounded sampling tool. The core product is offline and never contacts the network;
sampling is separate, opt-in tooling.

## Safety and licensing summary

- **Bounded by design.** Sampling never downloads a whole dataset. Every path is capped by
  `--limit` through `collection_integrity.ingestion.sampling.take_bounded_lines`, which stops after a
  bounded number of records even on an arbitrarily large or streaming input. There is no default
  remote — you must pass an explicit `--from` (local) or `--url`. See `scripts/fetch_sample.py`.
- **Metadata licenses.** All three programs release their *metadata* under CC0 (public domain
  dedication). You may redistribute the synthetic fixtures in this repo freely; before
  redistributing real downloaded data, re-check the current license at the source.
- **No images.** The sampling tool fetches tabular metadata only. Image files often carry separate
  terms; do not fetch or redistribute images with this tool.
- **Read-only.** Adapters and sampling never modify a source file.

## Sources

### Metropolitan Museum of Art — Open Access

- Source: <https://github.com/metmuseum/openaccess> (`MetObjects.csv`)
- License: CC0 (metadata)
- Adapter: `--source met --input MetObjects.csv`
- Maps object identity/cataloging fields (`Object ID`, `Object Number`, `Title`, `Object Name`,
  `Department`, `Culture`, `Object Begin Date`, `Object End Date`) to canonical objects.

### Cleveland Museum of Art — Open Access

- Source: <https://github.com/ClevelandMuseumArt/openaccess> (`openaccess.csv` / `openaccess.json`)
- License: CC0 (metadata)
- Adapter: `--source cleveland --input openaccess.csv` (or `.json` — the format is chosen from the
  file extension; the same field map serves both).
- Maps `id`, `accession_number`, `title`, `type`, `department`, `culture`,
  `creation_date_earliest`, `creation_date_latest`.

### National Gallery of Art — Open Data

- Source: <https://github.com/NationalGalleryOfArt/opendata> (`objects.csv`,
  `objects_constituents.csv`, `constituents.csv`)
- License: CC0
- Adapter: `--source nga --input <directory>`
- This is the relational source: the adapter joins the many-to-many `objects_constituents` link
  table to stamp each object's makers and loads constituents as agents (with birth/death years),
  which enables **DATE002** (production date vs. maker lifespan) — a check a flat mapping cannot
  express. Maps object fields (`objectid`, `accessionnum`, `title`, `classification`,
  `departmentabbr`, `beginyear`, `endyear`) plus makers from constituents.

## Bounded sampling

```bash
# Bound a local export you already downloaded.
python scripts/fetch_sample.py --source met --from MetObjects.csv --limit 500 \
    --output samples/met_sample.csv

# Relational NGA sample: keeps N objects plus only the links/constituents they reference,
# so the subset ingests with no dangling references.
python scripts/fetch_sample.py --source nga --from nga_opendata/ --limit 300 --output samples/nga/
```

An explicit `--url` streams a bounded sample instead of reading a local file; it uses the same bound.

## Limitations (honest scope)

- **Ancient / BCE dates.** Met/Cleveland/NGA year fields are integers that occasionally denote BCE
  or sub-year-1 dates. The shared date parser represents dates as calendar dates (year 1..9999 CE),
  so BCE (negative) and year-0 values are left unset rather than fabricated. Short CE years
  (1-3 digits, e.g. year 185) *are* parsed — encyclopedic collections record many ancient works this
  way, and rejecting them produced large numbers of false SCHEMA001 findings on real data until this
  was fixed. Broadening the model to represent BCE dates is a backlog item, not a silent behavior.
- **Byte-order marks.** Several real exports (the Met and Cleveland CSVs, and Excel exports
  generally) begin with a UTF-8 BOM. Readers decode with `utf-8-sig` so the BOM does not bind to the
  first column name and silently break a mapping keyed on it.
- **Deferred entities.** The Met and Cleveland adapters map object-level fields only; their
  multi-valued artist/creator columns are not yet exploded into agents. Maker/agent extraction is
  demonstrated by the relational NGA adapter. Media/rights/location entities for these sources are
  future work.
- **CSV-oriented sampling.** The sampling tool bounds CSV (and CSV-shaped) exports; Cleveland JSON is
  ingested by the adapter but not sampled by this tool.

## Validation

Each adapter is validated on AI-generated datasets built in the institution's real published schema,
scored at precision = recall = 1.0 against a labeled injection ground truth, plus a VL-06 mutation
pass. See `docs/PROGRESS.md` (Loops 25–28) for the per-slice evidence.
