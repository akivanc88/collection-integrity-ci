# Future scope

Ideas deliberately **out of scope for the first release** (BUILD_BRIEF.md Section 6), recorded here
so the MVP stays focused. Nothing in this file is a commitment.

## Web viewer (beyond the Phase 5 MVP)

The Phase 5 viewer shows a read-only snapshot of a single scan run. Possible later additions:

- Multi-run history browsing and run-to-run diffs, backed by the run store (`engine/run_store.py`)
  and baseline comparison already in the engine.
- Live re-scan from the browser (would require careful sandboxing to preserve the read-only,
  offline guarantees).
- Sort/paginate/full-text filter within the findings table for very large runs.
- Export the current filtered view (CSV/SARIF) from the UI.

## Ingestion and adapters

- Explode the Met/Cleveland multi-valued artist columns into agents (maker extraction), enabling
  DATE002 on those sources as it already works for the NGA relational adapter.
- Media/rights/location entities for the museum source adapters.
- Broaden the date model to represent BCE / ancient / partial dates rather than leaving them unset
  (documented limitation in `docs/DATA_SOURCES.md`).
- Additional source adapters (Art Institute of Chicago API, Rijksmuseum) using the same
  built-in-mapping-profile pattern.
- JSON sampling in `scripts/fetch_sample.py` (currently CSV-oriented).

## Rules and analysis

- Configurable rulesets via a YAML file (per-rule enable/disable and severity overrides beyond the
  current CLI flags).
- Probabilistic / multimodal experimental rules (Phase 6, opt-in and disabled by default).

## Explicit non-goals (unchanged from Section 6)

Not a CMS replacement; no automatic editing of source records; no legal/authentication/valuation
conclusions; no artist attribution, facial recognition, or semantic search; no cloud
multi-tenancy, enterprise identity/billing, or heavy infrastructure; no required paid model key;
no full ArtiFact dataset download or model training.
