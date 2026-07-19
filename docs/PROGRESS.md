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

## 2026-07-18 — Loop 4: Slice A iteration 1 (rule registry + CORE002) + AI-generated benchmark

**Slice:** Goal set via `/goal`: complete the defined slices, validate accuracy on AI-generated
datasets, ≥2 iterations each with validation approved. This is Slice A iteration 1 plus the
synthetic dataset the accuracy validation runs against.

**Files created/changed:**

- `rules/base.py` — `Rule` ABC, `RuleContext`, and a `make_finding` factory (fills run-specific
  id/timestamp + stable fingerprint).
- `rules/registry.py` — `RuleRegistry` (enable/disable, severity override, stable-order dispatch).
- `rules/core_rules.py` — ported CORE001 to a `Rule` subclass, added
  `CORE002_REQUIRED_FIELD_MISSING` (configurable required fields; unknown fields ignored, not
  fatal).
- `cli.py` — `scan` now dispatches through the registry; added repeatable `--required-field`
  (defaults to accession_number + object_name) with validation (exit 2 on unknown field).
- `benchmark/synthetic.py` — deterministic clean synthetic-object generator (fabricated data,
  redistributable).
- `benchmark/injectors.py` — deterministic, non-mutating, disjoint, leakage-free error injector
  for CORE001/CORE002 with a labeled `InjectionManifest`.
- `benchmark/metrics.py` — precision/recall/F1 scoring of findings vs. manifest.
- `benchmark/dataset.py` — CSV writer for object tables.
- `benchmarks/generate.py` — regenerates committed artifacts.
- `benchmarks/mini/objects_clean.csv`, `benchmarks/mini/objects_dirty.csv`,
  `benchmarks/manifests/mini.json` — 60-object dataset, 8 labeled injected errors.
- Tests: `tests/unit/test_registry.py` (new), rewrote `tests/unit/test_core_rules.py` for the
  class API + CORE002, extended `tests/integration/test_scan_cli.py`, added
  `tests/integration/test_benchmark_accuracy.py`.

**Commands run and results:**

```bash
uv run pytest -q            # 30 passed
uv run ruff check .         # All checks passed!
uv run ruff format --check .  # 28 files already formatted (after auto-format)
uv run mypy src             # Success: no issues found in 19 source files
uv run python benchmarks/generate.py
  # -> Wrote clean/dirty CSVs + manifest, 8 injected errors
uv run collection-ci scan --objects-csv benchmarks/mini/objects_dirty.csv --fail-on none
  # -> 8 findings (4 CORE001 + 4 CORE002), matching the 8 injected errors
```

**Accuracy validation (VL-01, partial — implemented rules):** on the AI-generated dataset,
`test_injected_errors_are_detected_with_perfect_precision_and_recall` asserts precision = recall =
F1 = 1.0 for both CORE001 and CORE002, and `test_clean_dataset_has_zero_findings` asserts zero
false positives on the clean 60-object dataset. Both pass. Injection is verified non-mutating and
seed-deterministic by dedicated tests.

**Issue hit and fixed (not weakened):** adding CORE002 to the default registry changed the dirty
CLI fixture's expected output (blank-accession rows now also trigger CORE002). Updated the
integration test to assert both rule types appear, and added a `--required-field object_name` case
proving CORE002 can be scoped — behavior change reflected in tests, not suppressed.

**Limitations:** VL-01 is still partial (only CORE001/CORE002 have injectors); the other Section
11 rules and their injectors are not built. No `collection-ci benchmark` CLI command yet — scoring
runs via the test + library, not a user-facing command. This is iteration 1 of Slice A; iteration
2 (VL-02 shuffled-input parametrized over the registry, and VL-06 mutation testing) is the next
loop.

**Next slice:** Slice A iteration 2 — run VL-02 (fingerprint determinism incl. shuffled input,
parametrized over the registry) and VL-06 (mutation testing of each rule's tests); record
evidence. Then Slice B (mapping layer + JSON adapter).

---

## 2026-07-18 — Loop 5: Slice A iteration 2 (validation loops VL-02 + VL-06 approved)

**Slice:** Second iteration of Slice A — execute the two validation loops that are runnable now,
satisfying the goal's "≥2 iterations with validation approved" for the rule-engine slice.

**VL-02 (fingerprint determinism) — now `active`:** added
`tests/property/test_fingerprint_determinism.py`, parametrized over `ALL_RULE_CLASSES`, asserting
each rule's fingerprint set is (a) identical across two identical runs and (b) invariant to input
row order (shuffled with a fixed seed). Because it iterates the registry, adding a new rule with
an order-dependent fingerprint fails this test automatically.

```bash
uv run pytest tests/property/test_fingerprint_determinism.py -v   # 4 passed (2 rules x 2 checks)
```

**VL-06 (test-strength / mutation) — executed, `active`:** ran a mutation loop (script kept in the
session scratchpad, never committed) applying one deliberate defect at a time to
`rules/core_rules.py` and `rules/registry.py`, running the suite after each, and reverting via
`git checkout`. Mutations tried and all **killed** (suite failed as required):

1. CORE001 off-by-one (`len(group) < 2` -> `< 3`) — pairs no longer flagged — killed
2. CORE001 drop the non-empty accession filter — killed
3. CORE001 weaken default severity critical -> low — killed
4. CORE002 invert the missing check (`is not None` -> `is None`) — killed
5. CORE002 ignore configured required fields (`checked_fields = []`) — killed
6. Registry ignore the disabled flag — killed
7. Registry ignore severity override — killed

Result: 7/7 mutants killed, zero survivors — VL-06 done condition met for this mutation set.
Working tree confirmed clean after reverts; full suite green (34 passed).

**Commands run and results:**

```bash
uv run pytest -q            # 34 passed
uv run ruff check .         # clean
uv run mypy src             # clean
python <scratchpad>/mutation_run.py   # All mutants killed
```

**Validation approved for Slice A:** two iterations complete — iteration 1 (build + accuracy
P=R=1.0 on the AI-generated dataset, Loop 4) and iteration 2 (VL-02 + VL-06, this loop). Updated
the status column in `docs/VALIDATION_LOOPS.md` (VL-01 partial-pass, VL-02 and VL-06 active).

**Limitations:** VL-06 is a curated manual mutation set, not an exhaustive tool run; graduating to
`mutmut` is noted in `docs/BACKLOG.md` as a future upgrade. VL-01 remains partial pending injectors
for the other Section 11 rules.

**Next slice:** Slice B — configurable dataset-mapping layer (`BUILD_BRIEF.md` Section 10) +
JSON adapter, ported behind the existing CSV path, then two validation iterations for it.

---

## 2026-07-18 — Loop 6: Slice B (configurable mapping layer + JSON adapter), both iterations

**Slice:** The Section 10 mapping layer plus a JSON adapter, so arbitrary CSV/JSON exports with
non-canonical column names can be ingested via a validated YAML mapping.

**Files created/changed:**

- `canonical/mappings.py` — Pydantic models (`DatasetMapping`, `EntityMapping`, `FieldMapping`)
  with a `split_pipe`/`strip` transform set; `coerce_field_mapping` accepts either a bare source
  column string or a `{source, transform}` form.
- `ingestion/readers.py` — raw CSV and JSON readers returning `(row_number, raw_fields)`; JSON row
  numbers are 1-based array positions, CSV counts the header as row 1.
- `ingestion/mapper.py` — `load_mapping` (YAML -> validated model) and `load_objects` (applies the
  mapping + transforms to build canonical `CollectionObject`s, preserving raw fields + provenance).
- `cli.py` — `scan` now takes `--objects-csv` OR `--mapping` (exactly one; exit 2 otherwise);
  updated module docstring.
- `benchmark/dataset.py` — added `write_objects_json`.
- `examples/mappings/clean-objects.yaml` — worked example mapping for the bundled clean dataset.
- Fixtures: `mapping_objects.csv`, `mapping_objects.json`, `mapping_csv.yaml`, `mapping_json.yaml`.
- Tests: `tests/unit/test_mapper.py`, `tests/integration/test_mapping_accuracy.py`, extended
  `tests/integration/test_scan_cli.py` (mapping path + exactly-one-input).

**Commands run and results:**

```bash
uv run pytest -q            # 44 passed
uv run ruff check .         # clean
uv run mypy src             # clean (22 source files)
uv run collection-ci scan --mapping examples/mappings/clean-objects.yaml --fail-on none
  # -> Scanned 5 object record(s). No findings.
```

**Iteration 1 (build + unit validation):** `test_mapper.py` proves column renaming, `split_pipe`
transform, JSON/CSV equivalence (identical canonical records from both formats), row-number and
raw-field provenance, and error handling (no objects entity; non-array JSON).

**Iteration 2 (accuracy validation on AI-generated data):** `test_mapping_accuracy.py` writes the
synthetic dataset through a *renamed-column* schema in both CSV and JSON, ingests via a dataset
mapping, and scores against the injection manifest — precision = recall = 1.0 for CORE001 and
CORE002 on both formats. This confirms the mapping path is as accurate as the direct CSV path.

**VL-06 (mutation) for Slice B:** run after commit (needs committed files for `git checkout`
revert); results recorded in the next loop entry.

**Issue fixed (not weakened):** mypy flagged `FieldMapping(**raw)` in `coerce_field_mapping`
(the `transform` literal); switched to `FieldMapping.model_validate(raw)` so Pydantic validates the
transform value against the allowed set.

**Limitations:** mapping covers the `objects` entity only (media/rights/locations entities await
their rules); transforms are limited to `split_pipe` and `strip`; JSON Schema files for the mapping
(vs. Pydantic validation) are still deferred to Phase 3. Both validation iterations for Slice B are
complete and approved.

**Next slice:** run VL-06 mutation on the mapper/readers (post-commit), then continue the rule set
(REF001 orphan media -> object) which will require the `MediaAsset` model and multi-entity
ingestion.
