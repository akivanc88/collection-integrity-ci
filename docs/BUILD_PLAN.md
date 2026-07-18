# Build Plan

Authoritative sequencing lives in `BUILD_BRIEF.md` Section 24. This document tracks the concrete
implementation plan for the phases in progress and records deviations as they happen.

## Phase 0: Research and planning — in progress

- [x] Inspect repository and git status
- [x] Create `CLAUDE.md`
- [x] Create `docs/PRD.md`, `docs/BUILD_PLAN.md` (this file), `docs/BACKLOG.md`,
      `docs/PROGRESS.md`
- [ ] Record assumptions and open questions (see PRD "Open questions" and Assumptions below)
- [~] Read linked primary resources — deferred deep reading of the full external resource list
      (Claude Code docs, museum data sources, ArtiFact paper) to keep momentum on the build; the
      two problem-evidence links (MoMA issues, Met Open Access image issue) were used to write the
      PRD's Evidence section from their known content. Full source-adapter-specific reading is
      scheduled for Phase 4 when those adapters are built.

## Phase 1: Foundation — in progress

1. Python package via `uv`, `pyproject.toml`, console entry point `collection-ci`.
2. Ruff (lint + format), mypy (type check), pytest, structured logging.
3. Configuration schemas: dataset mapping YAML + ruleset YAML, validated with Pydantic v2 (JSON
   Schema export deferred to Phase 3 alongside the other schema files, to avoid building schema
   plumbing before the shapes stabilize).
4. Canonical models: `SourceRef` and `CollectionObject` implemented first (needed for the first
   slice); `MediaAsset`, `RightsRecord`, `LocationRecord`, `AgentOrMaker` follow in Phase 2 as
   rules that need them are implemented.
5. Minimal clean fixture: a small `objects.csv` under `examples/clean/` sufficient to exercise
   ingestion + one rule end-to-end. The full-size clean/dirty benchmark fixtures (250+ objects
   etc., Section 16) are Phase 3 work.
6. CI: `.github/workflows/ci.yml` running install, lint, format check, type check, tests.
7. Run all checks locally before considering Phase 1 done.

### Deviation from the recommended stack (recorded per Section 7 instruction)

- Deferring Polars and DuckDB until Phase 2/3 when data volumes and run-history needs justify
  them. Phase 1's single small CSV fixture does not need either; introducing them now would add
  dependency weight without a corresponding test. Will use the standard library `csv` module for
  the first ingestion slice and revisit before Phase 2 rule breadth makes performance relevant.
- Python 3.12 requested by the brief; the local `uv`-managed environment pins 3.12 explicitly via
  `requires-python` even though the system Python is 3.14, so behavior is reproducible regardless
  of the host's system interpreter.

## Phase 2: Ingestion and deterministic engine — not started

CSV/JSON adapters, mapping engine, rule base class + registry, initial 15 rules, finding model +
fingerprints, run store, console/JSON output, comprehensive tests. The first slice (Phase 1 tail)
implements a minimal version of the CSV adapter, mapping, and `CORE001` only; Phase 2 generalizes
this to the full adapter/rule set.

## Phase 3: Reports, baselines, and benchmark — not started

## Phase 4: Source adapters — not started

## Phase 5: Local viewer — not started (gated on Phase 3 passing)

## Phase 6: Optional ArtiFact and multimodal experiment — not started

## Phase 7: Public showcase (GitHub Pages) — not started (gated on Definition of Done + explicit
approval to publish)

## Assumptions

- "Portable" and "local-first" are interpreted strictly: no network calls anywhere in the default
  CLI path, verified by running tests with network access disabled once the test suite exists.
- `accession_number` is treated as case-sensitive and whitespace-trimmed for duplicate detection
  (CORE001) unless a ruleset later configures otherwise; this will be documented in
  `docs/RULE_AUTHORING.md` when that rule is finalized.
- Empty/whitespace-only accession numbers are excluded from duplicate detection (per
  `BUILD_BRIEF.md` Section 11, item 1: "duplicate *non-empty* accession numbers").
