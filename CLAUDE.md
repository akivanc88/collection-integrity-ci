# CLAUDE.md

Guidance for Claude Code (or any contributor) working in this repository.

## Project purpose

Collection Integrity CI is a local-first, portable quality-assurance layer for museum and
cultural-heritage collection data. It ingests exported CSV/JSON records, runs a deterministic
rule engine against them, and produces evidence-backed findings (JSON, CSV, HTML, SARIF) that a
registrar or collections data manager can act on before a migration, publication, or export.

It is *not* a CMS, not a rights/legal authority, and does not edit source records. See
`BUILD_BRIEF.md` for the full specification — treat it as authoritative.

## Current phase

Phases 0–5 are complete (see `BUILD_BRIEF.md` Section 24 and `docs/PROGRESS.md`): foundation, the
deterministic engine with all 15 rules, reports/baselines/benchmark, the Met/Cleveland/NGA source
adapters with bounded sampling, and the local web viewer (`collection-ci serve` — a read-only,
offline, server-rendered FastAPI app; see `docs/adr/ADR-007-web-viewer.md`). The endgame validation
loops (VL-04/05/07/08/10) are green and the Definition of Done (Section 25) passes
(`scripts/check_dod.sh`). The Phase 7 GitHub Pages showcase has been **built and verified locally**
(`site_src/`, `mkdocs.yml`, `.github/workflows/pages.yml`); **publishing remains approval-gated** —
do not push or enable GitHub Pages without explicit user approval. Phase 6 (optional
ArtiFact/probabilistic experiment, opt-in and disabled by default) has not started.

Track detailed status in `docs/PROGRESS.md` (source of truth for what actually works).

## Architecture boundaries

- `src/collection_integrity/canonical/` — Pydantic domain models and provenance (`SourceRef`,
  `CollectionObject`, etc.). No I/O here.
- `src/collection_integrity/ingestion/` — format adapters (CSV, JSON, later museum-specific).
  Adapters only read; they never write back to source files.
- `src/collection_integrity/rules/` — deterministic rule implementations. One rule = one
  documented, versioned check. No network calls, no LLM calls.
- `src/collection_integrity/engine/` — orchestration: scanning, fingerprinting, baselines, run
  storage. This is where rules get applied to canonical entities.
- `src/collection_integrity/reporting/` — output formatters (console, JSON, CSV, HTML, SARIF).
  Formatters must not mutate findings.
- `src/collection_integrity/benchmark/` — deterministic error injection and metrics, used to
  validate rule precision/recall against a labeled synthetic dataset.
- `src/collection_integrity/api/` — FastAPI web viewer. Do not build or start this before the CLI,
  engine, reports, benchmark, and tests all work (Phase 5 gate).

## Safety constraints (do not violate)

- Never modify source collection data. Ingestion is read-only.
- Never push to GitHub, deploy infrastructure, or enable GitHub Pages without explicit user
  approval. Publishing (BUILD_BRIEF.md Phase 7) is an approval-gated, end-of-build step.
- No paid AI services in the core execution path. The core product works offline, without API
  keys. Any future AI-assisted rule is an optional, disabled-by-default adapter.
- No downloads larger than 1 GB. Never fetch the full ArtiFact dataset automatically.
- Never claim a feature works without having run the relevant command/test and inspected the
  output.
- Never weaken or delete a test to make a build pass. Diagnose failures instead.
- Local commits only, after the relevant checks pass. Commit messages should be small and
  reviewable, one vertical slice per commit where practical.

## Commands

Environment is managed with `uv`.

```bash
uv sync                          # install/sync dependencies
uv run ruff check .              # lint
uv run ruff format --check .     # format check
uv run mypy src                  # type check
uv run pytest                    # tests
uv run collection-ci --help      # CLI entry point
```

## Working method

Follow the loop in `BUILD_BRIEF.md` Section 26: inspect state, pick the smallest vertical slice,
implement, run focused tests, run broader checks, inspect real output, update
`docs/PROGRESS.md`, commit. Repeat.

Validation has its own dedicated loops with machine-checkable done conditions — see
`docs/VALIDATION_LOOPS.md` (VL-01..VL-10). When a new rule lands, run VL-06 (mutation) against
it and extend VL-02 (fingerprint determinism); execution evidence goes in `docs/PROGRESS.md`. Section 26A additionally asks for loop-by-loop evidence
(commands + results) in `docs/PROGRESS.md`, since this repository is also intended as a
loop-engineering case study (see `BUILD_BRIEF.md` Phase 7 and Section 26A) — do not fabricate
that evidence; only record loops that actually happened.
