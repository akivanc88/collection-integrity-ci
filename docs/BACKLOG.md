# Backlog

TODOs and deferred work, with rationale and rough priority, per `BUILD_BRIEF.md` Section 26
("TODOs are acceptable only when recorded here with rationale and priority").

## High priority (needed to finish Phase 1/2)

- **Remaining canonical models** (`MediaAsset`, `RightsRecord`, `LocationRecord`, `AgentOrMaker`).
  Rationale: only `SourceRef` + `CollectionObject` are needed for the CORE001 slice; the rest are
  needed as soon as REF/RIGHTS/LOC/MEDIA rules are implemented in Phase 2.
- **JSON ingestion adapter.** Rationale: Phase 1 slice only needs CSV; JSON adapter is explicit
  MVP scope (Section 5, item 2) and belongs in Phase 2 with the mapping engine generalization.
- **Rule registry + base class.** Rationale: CORE001 is currently a direct function call in the
  slice, not yet plugged into a registry, to keep the first slice minimal. Needed before a second
  rule is added (Phase 2), so it doesn't get skipped.
- **JSON Schema files for mapping/ruleset/finding/manifest** (`schemas/*.schema.json`). Rationale:
  deferred from Phase 1 to Phase 3 per BUILD_PLAN.md deviation note, once shapes stabilize across
  more than one rule.

## Medium priority (Phase 3+)

- Polars/DuckDB adoption once fixture sizes and run-history requirements justify the dependency
  weight (see BUILD_PLAN.md deviation note).
- SARIF, HTML, CSV report writers.
- Baseline comparison and `--only-new`.
- Deterministic error injector + benchmark evaluator.
- **Remaining CI steps from `BUILD_BRIEF.md` Section 20**: coverage measurement (coverage.py with
  a threshold), dependency audit (pip-audit or equivalent), SARIF validation, upload of the
  sample HTML report as a workflow artifact, and the second demonstration workflow that scans
  `examples/dirty` and uploads SARIF without failing software CI on expected findings. Deferred
  because coverage/audit tooling isn't wired up yet and SARIF/HTML reports don't exist yet
  (Phase 1 `ci.yml` only does install, lint, format, type check, tests, build, and a sample scan
  against `examples/clean`). Add these as each underlying feature lands in Phase 3.

## Validation tooling upgrades

- **Graduate VL-06 from a manual mutation set to `mutmut` (or `cosmic-ray`).** Rationale: the
  current mutation loop uses a curated, hand-written list of defects (see `docs/PROGRESS.md`
  Loop 5); a mutation-testing tool would explore the full mutation space automatically. Deferred
  until the rule set is larger and worth the CI runtime.
- **Wire coverage.py with a threshold (VL-07).** Rationale: coverage is in the brief's stack but
  not yet configured; belongs with the other Section 20 CI steps.

## Low priority / explicitly deferred

- Source adapters (Met, Cleveland, NGA) — Phase 4.
- Local web viewer — Phase 5, gated.
- ArtiFact adapter and any probabilistic rule — Phase 6, opt-in, disabled by default.
- GitHub Pages showcase site (MkDocs) — Phase 7, gated on Definition of Done and explicit
  approval to publish.

## Explicitly out of scope for MVP

See `BUILD_BRIEF.md` Section 6 (non-goals) — not tracked here as backlog items since they are not
planned for this release at all; see `docs/FUTURE_SCOPE.md` (to be created in Phase 3) for
post-MVP ideas.
