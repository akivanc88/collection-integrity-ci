# PRD: Collection Integrity CI

## Target users

Primary: museum registrar, collections data manager, digital collections manager, CMS
administrator, archivist/historical society staff preparing a migration, technical consultant
cleaning or validating collection exports.

Secondary: developers maintaining public collection data, researchers using open museum datasets,
data governance/rights staff, museum leadership reviewing collection-data readiness.

## Problem

Collection management systems store object, media, rights, location, people, and publication
records that are edited independently over years by different staff. These records routinely
disagree with each other — an object with two "current" locations, media marked public while its
rights record forbids publication, a media file referencing an object that no longer exists. These
disagreements are usually discovered manually, late, and expensively (during a migration or public
release), rather than caught continuously.

## Evidence

- MoMA's public collection repository issue tracker documents real data-quality issues in
  production museum data (referenced in `BUILD_BRIEF.md`, Section "Primary resources").
- The Met Open Access project has a public issue about image-availability inconsistency between
  metadata and actual media files (same source).
- These are exactly the class of problem this project targets: reference integrity, rights/
  publication conflicts, and media/metadata mismatches — not hypothetical.

## Goals (MVP)

1. Ingest CSV/JSON exports via a configurable mapping into a canonical model that preserves
   provenance (source file, row, hash).
2. Run a deterministic, versioned rule engine (>=10 rules) covering schema, reference integrity,
   rights/publication conflicts, location consistency, dates, controlled vocabulary, and media
   files.
3. Emit evidence-backed findings (rule id/version, severity, entity, evidence, remediation,
   stable fingerprint) in JSON, CSV, HTML, and SARIF.
4. Support baselines so CI can fail only on new findings.
5. Ship a synthetic clean+dirty benchmark with a deterministic error injector and measure
   precision/recall.
6. Work fully offline with no paid API keys required in the core path.

## Non-goals

See `BUILD_BRIEF.md` Section 6 verbatim: no CMS replacement, no automatic editing of source
records, no legal conclusions about rights, no authentication/valuation/attribution, no facial
recognition, no live shelf scanning, no full-text semantic search, no cloud multi-tenancy, no
enterprise identity/billing, no full ArtiFact download, no new vision model training, no required
paid model key, no Kubernetes.

## User journeys

1. **Pre-migration check.** A registrar exports objects/media/rights/locations to CSV, writes a
   mapping once, runs `collection-ci scan`, opens `report.html`, and triages critical findings
   before a CMS migration.
2. **CI gate for an open-data pipeline.** A developer publishing open collection data runs
   `collection-ci scan --fail-on high` in GitHub Actions on every export regeneration; SARIF
   annotates the PR.
3. **Baseline-driven cleanup.** A data manager records today's findings as a baseline, then uses
   `--only-new` in CI so existing (already known, being worked on) issues don't block merges while
   new regressions do.
4. **Rule authoring.** A technical consultant adds an institution-specific rule (e.g., a stricter
   vocabulary) by editing a ruleset YAML file, validated against a JSON Schema.

## Requirements

Enumerated in full in `BUILD_BRIEF.md` Sections 5, 11, 13, 14. Summary: CLI (`collection-ci`)
with `init`, `profile`, `scan`, `explain`, `inject-errors`, `benchmark`, `serve`; 15 initial rule
IDs; finding schema with stable fingerprints; run manifest with input hashes and env info; HTML
report with no externally-hosted assets; valid SARIF 2.1.0.

## Success metrics

Records/sec, scan duration, findings by severity/rule, % findings with exact source location,
benchmark precision/recall/F1, clean-dataset false-positive count, fingerprint stability across
identical runs, report-generation time. No invented time-savings claims (`BUILD_BRIEF.md` Section
22).

## Risks

- Over-claiming what a "policy conflict" or "visual mismatch" proves (mitigated by explicit
  language: policy warning vs. deterministic fact vs. probabilistic suggestion, and by keeping
  probabilistic rules out of the MVP entirely).
- Synthetic benchmark results being read as claims about real institutional error rates
  (mitigated by `docs/DATA_CARD.md` / `docs/BENCHMARK.md` disclaimers).
- Museum data often has messy real-world encodings (mixed date formats, free-text locations) that
  synthetic fixtures under-represent — tracked as a limitation, revisited when a real open dataset
  adapter (Phase 4) is added.

## Open questions

- Which controlled vocabularies should ship as sane defaults vs. be left fully institution-defined?
  Deferred until more real ruleset examples exist.
- Whether DuckDB-backed run history is needed before Phase 3, or whether flat JSON run stores are
  sufficient for the MVP — currently deferring DuckDB until baseline/history features need it.
