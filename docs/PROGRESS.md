# Progress Log

Source of truth for what actually works. Each entry is one loop iteration from
`BUILD_BRIEF.md` Section 26 (inspect -> smallest slice -> implement -> test -> broader checks ->
inspect output -> document -> commit). Entries are append-only; do not rewrite history, add a new
entry to correct or supersede an earlier one.

---

## 2026-07-18 — Loop 1: Repository setup and Phase 0 planning docs

**Slice:** Inspect repo, create `CLAUDE.md`, create Phase 0 planning docs
(`PRD.md`, `BUILD_PLAN.md`, `BACKLOG.md`, `PROGRESS.md`), save the kickoff prompt for provenance.

**Commands run:**

```bash
pwd && git status
find . -not -path './.git*' | sort
which uv python3 git
uv --version; python3 --version; git --version
```

**Results:**

- Repo contained only `BUILD_BRIEF.md` (untracked), no commits yet, branch `master`.
- `uv 0.10.4`, system `python3.14.3` (will pin project to 3.12 via `uv`/`pyproject.toml` in the
  next loop), `git 2.43.0` all present.

**Limitations / deferrals:** Deep reading of the external primary-resource links (Claude Code
docs, museum open-data sources, ArtiFact paper) deferred — see `docs/BUILD_PLAN.md` Phase 0 note.
No code written yet in this loop; nothing to test.

**Next slice:** Scaffold the Python package with `uv` (pyproject.toml, ruff/mypy/pytest config,
`collection-ci` entry point via Typer), confirm `uv sync` succeeds.

---

## 2026-07-18 — Loop 2: Foundation scaffold + first vertical slice (CSV -> CORE001 -> console/JSON)

**Slice:** Everything from the Kickoff Prompt's "Start now by" list: scaffold the Python project,
implement canonical models/provenance, implement the smallest end-to-end path (objects CSV ->
canonical `CollectionObject` records -> `CORE001_DUPLICATE_ACCESSION_NUMBER` detection -> console
table + `findings.json`), add tests, add CI, run all checks.

**Files created:**

- `pyproject.toml`, `.python-version` (pins 3.12.3, available locally at `/usr/bin/python3.12`,
  no download needed), `.gitignore`, `LICENSE` (Apache-2.0), `README.md` (status: early Phase 1,
  quick start marked as target/not-yet-fully-implemented)
- `src/collection_integrity/__init__.py`, `provenance.py`, `cli.py`
- `src/collection_integrity/canonical/models.py` — `SourceRef`, `CollectionObject` (Pydantic v2,
  frozen models)
- `src/collection_integrity/ingestion/csv_adapter.py` — minimal CSV objects loader (direct column
  names, no configurable mapping yet — see Limitations)
- `src/collection_integrity/rules/core_rules.py` — `CORE001_DUPLICATE_ACCESSION_NUMBER` v1.0.0
- `src/collection_integrity/engine/findings.py` — `Finding`/`RuleRef`/`EntityRef`/`EvidenceItem`
  models matching the schema in `BUILD_BRIEF.md` Section 12, plus `compute_fingerprint`
- `tests/unit/test_csv_adapter.py`, `tests/unit/test_core_rules.py`,
  `tests/integration/test_scan_cli.py`
- `tests/fixtures/objects_clean.csv`, `tests/fixtures/objects_duplicate_accession.csv`
- `examples/clean/objects.csv` (5 objects, unique accession numbers)
- `.github/workflows/ci.yml` (install from lockfile, ruff check, ruff format check, mypy, pytest,
  `uv build`, sample scan against `examples/clean`)
- `docs/prompts/kickoff-prompt.md` (saved per Section 26A)

**Commands run and results:**

```bash
uv sync                                  # OK — resolved 26 packages, Python 3.12.3
uv run pytest -v                         # 13 passed (after two fixes, see below)
uv run ruff check .                      # All checks passed! (after one line-length fix)
uv run ruff format --check .             # 17 files already formatted (after one auto-format)
uv run mypy src                          # Success: no issues found in 12 source files
uv run collection-ci scan --objects-csv examples/clean/objects.csv --output-dir build/scan
  # -> "Scanned 5 object record(s). No findings." findings.json == []  exit 0
uv run collection-ci scan --objects-csv tests/fixtures/objects_duplicate_accession.csv \
  --output-dir build/scan-dirty
  # -> console table shows CORE001_DUPLICATE_ACCESSION_NUMBER, critical, 2 objects
  #    findings.json has 1 finding matching the Section 12 schema shape
  #    exit code 1 (fail-on default "critical" reached)
uv build                                 # OK — built sdist + wheel
```

**Issues hit and fixed (not weakened):**

1. Typer collapses a single `@app.command()` into a no-subcommand-name CLI by default, so
   `scan --objects-csv ...` failed with "unexpected extra argument (scan)". Fixed by adding an
   `@app.callback()`, which forces Typer to keep subcommand mode — the correct long-term shape
   since more subcommands (`init`, `profile`, `explain`, ...) are coming in later phases.
2. One integration test asserted the full rule ID string appeared in the rich console table
   output; the table truncates long IDs to fit terminal width. Fixed the test assertion (checks
   the stable "CORE001" prefix in console output, and the full ID in `findings.json`) rather than
   changing the rule ID or disabling table truncation.
3. One ruff `E501` (line too long) in `cli.py`, fixed by shortening the help string; one file
   needed `ruff format` applied.

**Test, lint, and type-check results:** 13/13 tests pass, ruff check clean, ruff format clean,
mypy clean (strict mode), package builds, manual CLI runs against both a clean and a dirty fixture
produce the expected exit codes and finding shape.

**Known limitations:**

- CSV ingestion has no configurable mapping yet — it reads fixed column names (`object_id`,
  `accession_number`, `title`, `object_name`) directly. The `BUILD_BRIEF.md` Section 10 mapping
  layer is Phase 2 work (`docs/BACKLOG.md`).
- Only 1 of the 15 rules in `BUILD_BRIEF.md` Section 11 is implemented (`CORE001`). No rule
  registry yet — the CLI calls `check_duplicate_accession_numbers` directly.
- Only `SourceRef` and `CollectionObject` canonical models exist; `MediaAsset`, `RightsRecord`,
  `LocationRecord`, `AgentOrMaker` are not implemented.
- The `scan` CLI command's flags (`--objects-csv`, `--output-dir`, `--fail-on`) are a minimal
  subset of the full Section 13 specification (no `--mapping`, `--rules`, `--baseline`,
  `--only-new`, `--rule`, `--entity`, `--no-media-files`, `--format`, and only `findings.json` is
  written — no CSV/HTML/SARIF/run-manifest/summary yet).
- `docs/DOMAIN_MODEL.md`, `RULE_AUTHORING.md`, `DATA_SOURCES.md`, `BENCHMARK.md`,
  `THREAT_MODEL.md`, `DATA_CARD.md`, `MODEL_CARD.md`, `DEMO.md`, `FUTURE_SCOPE.md`, and any ADRs
  do not exist yet — Section 21 documentation deliverables are Phase 3+ work.
- CI (`ci.yml`) covers install/lint/format/type-check/tests/build/sample-scan only; coverage
  measurement, dependency audit, SARIF validation, HTML report upload, and the dirty-example demo
  workflow are not implemented yet (tracked in `docs/BACKLOG.md`).
- No commit has been made to git yet as of the start of this loop; this loop ends with the first
  local commit once this entry is written.

**Next slice:** Generalize CSV ingestion behind the configurable dataset-mapping layer
(`BUILD_BRIEF.md` Section 10) and add a JSON adapter, so Phase 2's rule expansion doesn't have to
keep changing the ingestion signature; then add `CORE002_REQUIRED_FIELD_MISSING` and a minimal
rule registry so a second rule doesn't require another CLI rewrite.

---

## 2026-07-18 — Loop 3: Validation-loop specifications

**Slice:** Specify the project's validation loops as first-class, self-verifying goals in
`docs/VALIDATION_LOOPS.md` — ten loops (VL-01..VL-10) covering rule-engine correctness
(benchmark closure, fingerprint determinism, baseline round-trip), robustness (threat-model
adversarial fixtures, fuzz/property contract), quality gates (mutation testing of the test
suite, coverage ratchet), and consistency (README-executes, progress audit,
Definition-of-Done closure). Each loop declares what it validates, the earliest phase it can
run, its loop body, a machine-checkable done condition, its evidence artifact, and how it is
driven.

**Files created/changed:** `docs/VALIDATION_LOOPS.md` (new), this entry, a pointer in
`CLAUDE.md`.

**Commands run:** documentation-only slice; full check suite re-run before commit to keep the
commit-after-checks rule:

```bash
uv run ruff check .        # All checks passed!
uv run ruff format --check .  # already formatted
uv run mypy src            # Success: no issues found
uv run pytest -q           # 13 passed
```

**Limitations:** These are specifications, not executions — the status column marks most loops
`pending` on Phase 2/3 features (injector, mapping layer, baselines, coverage wiring). VL-02 is
`partial` (single-rule stability test exists; the shuffled-input case and per-rule
parametrization do not). VL-06 and VL-09 are runnable now but have not yet been run; their first
executions should land as their own PROGRESS entries.

**Next slice:** unchanged from Loop 2 (mapping layer + JSON adapter + CORE002 + rule registry).
First loop executions to schedule after that lands: VL-06 against CORE001/CORE002, and VL-02's
shuffled-input case.

---
