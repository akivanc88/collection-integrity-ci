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

---

## 2026-07-18 — Loop 7: VL-06 mutation on Slice B found and closed two real test gaps

**Slice:** Run the VL-06 mutation loop against the Slice B ingestion code (mapper + readers) — the
loop that validates the *tests*, not just the code.

**Mutations tried and initial result:**

1. `split_pipe` no longer splits — killed
2. empty mapped object_id no longer rejected — **SURVIVED**
3. raw fields dropped from provenance — killed
4. CSV header row offset wrong (`start=2` -> `start=1`) — killed
5. JSON non-array not rejected (`isinstance(data, list)` guard bypassed) — **SURVIVED**

Two survivors were genuine test gaps: (2) had no test asserting an empty mapped object_id raises;
(5) my existing `test_invalid_json_array_raises` passed a top-level object, which was still caught
by the *per-record* "not a JSON object" check, so the array guard itself was untested (the mutant
survived because a different check masked it).

**Fix (strengthened tests, code unchanged):** added `test_empty_mapped_object_id_raises` and
tightened `test_invalid_json_array_raises` to assert the specific "expected a JSON array" message
so the array guard is isolated. Re-ran the mutation loop: **5/5 killed, zero survivors.**

```bash
uv run pytest tests/unit/test_mapper.py -q   # 8 passed
# mutation loop (scratchpad, reverted via git checkout): all 5 mutants killed
uv run pytest -q                              # 45 passed
```

This is VL-06 behaving exactly as designed — it caught weaknesses in the suite that green tests
had hidden, and the loop closed them. Slice B now has both accuracy (Loop 6) and mutation (this
loop) validation approved.

**Next slice:** REF001 (orphan media -> object reference), which requires adding the `MediaAsset`
canonical model, multi-entity ingestion (a second mapped entity), and a matching injector so its
accuracy can be measured on the synthetic dataset.

---

## 2026-07-18 — Loop 8: Slice C — multi-entity ingestion + MediaAsset + REF001

**Slice:** New `/goal` — complete all remaining Phase 2 slices, validated on AI-generated data,
>=2 iterations each. Slice C is first: multi-entity ingestion + `MediaAsset` model + REF001
(orphan media -> object).

**Files created/changed:**

- `canonical/models.py` — added `MediaAsset`.
- `ingestion/mapper.py` — extracted generic `_load_entity_records` (per-entity primary-key
  emptiness check); added `load_media`, `has_entity`, int/scalar coercion (`_int` leaves a
  non-integer unset for a future SCHEMA001 to report).
- `rules/base.py` — `RuleContext` gained `media`.
- `rules/reference_rules.py` (new) — `REF001_ORPHAN_MEDIA_OBJECT` (high). Media with no object_id
  at all is deliberately not an orphan (required-field concern); only a present-but-unknown target
  is flagged.
- `rules/registry.py` — registered REF001.
- `cli.py` — `_load_entities` returns objects + media; media loaded when the mapping defines it.
- `benchmark/synthetic.py` — `generate_clean_media`; `benchmark/injectors.py` —
  `inject_orphan_media` + `expected_ref001_media()`; `benchmark/metrics.py` — REF001 scoring.
- Tests: `test_reference_rules.py`, `test_reference_accuracy.py`, extended `test_mapper.py`;
  fixtures `mapping_media.csv`, `mapping_with_media.yaml`.

**Commands run and results:**

```bash
uv run pytest -q     # 55 passed
uv run ruff check .  # clean
uv run mypy src      # clean (23 source files)
```

**Iteration 1 (accuracy on AI data):** clean object+media pair yields no REF001; injecting 5
orphan references and scoring against the manifest gives **precision = recall = 1.0** (TP 5).
Orphan injection verified non-mutating.

**Iteration 2 (VL-02):** extended the fingerprint-determinism harness to carry media (seeded with
4 orphans) so REF001 is genuinely exercised; all three rules pass stable + shuffled (objects and
media shuffled independently), plus a guard test asserting REF001 produces 4 findings so its
cases can't pass trivially.

**Next:** commit, then VL-06 mutation on the new ingestion/rule code (needs committed files for the
git-checkout revert), recorded in the next loop.

---

## 2026-07-18 — Loop 9: VL-06 mutation on Slice C found and closed one gap

**Slice:** Mutation-test the Slice C code (REF001 + media ingestion) — Slice C's second validation.

**Mutations tried:** REF001 treat-all-refs-valid (killed), REF001 flag-missing-object_id-too
(killed), REF001 weaken-severity high->low (**SURVIVED**), media skip-empty-primary-key (killed).

The survivor was a real gap: nothing asserted REF001's severity. Added
`test_ref001_default_severity_is_high` (checks the registry's effective severity and a
registry-run finding). Re-ran: **4/4 killed, zero survivors.**

```bash
uv run pytest tests/unit/test_reference_rules.py -q   # 4 passed
# mutation loop (scratchpad, reverted via git checkout): all 4 killed
```

Slice C validation approved (accuracy + VL-02 + VL-06). Phase 2 rule count: 3 of ~15
(CORE001, CORE002, REF001).

**Next slice:** Slice D — `RightsRecord` entity + REF002 (orphan rights reference) + RIGHTS001
(publication-rights policy conflict), with injectors and two validated iterations.

---

## 2026-07-18 — Loop 10: Slice D — RightsRecord + REF002 + RIGHTS001

**Slice:** RightsRecord entity + REF002 (orphan rights reference from object or media) + RIGHTS001
(publication-rights policy conflict), with injectors and two validated iterations.

**Files created/changed:**

- `canonical/models.py` — `RightsRecord`.
- `ingestion/mapper.py` — `SCALAR_RIGHTS_FIELDS`, `load_rights`, `_build_rights`, `_bool` parser
  (true/false/yes/no/1/0).
- `rules/base.py` — `RuleContext.rights`.
- `rules/reference_rules.py` — `REF002_ORPHAN_RIGHTS_REFERENCE` (checks object + media rights_id).
- `rules/rights_rules.py` (new) — `RIGHTS001_PUBLICATION_CONFLICT` (critical). Policy: an entity
  whose publication_status is "public" but whose linked rights record does not clearly permit
  publication (publication_allowed must be True, review_required not True, rights_status not in
  restricted/unknown/review_required). Deliberately skips entities whose rights reference is
  missing — that's REF002's job — so no entity is double-reported. Documented as policy
  consistency, not legal advice.
- `rules/registry.py` — registered REF002 + RIGHTS001.
- `cli.py` — `_load_entities` now returns objects + media + rights.
- `benchmark/synthetic.py` — `generate_clean_rights`, `rights_permits_publication`,
  `link_objects_to_rights` (clean invariant: public only when rights permit).
- `benchmark/injectors.py` — `inject_orphan_rights` (REF002), `inject_publication_conflict`
  (RIGHTS001, flips a non-public object linked to restricted rights to public); manifest
  accessors; `benchmark/metrics.py` scores both.
- Tests: `test_rights_rules.py`, `test_rights_accuracy.py`; fixtures `mapping_rights.csv/.yaml`,
  `objects_with_rights.csv`; extended the VL-02 harness to carry rights.

**Commands run and results:**

```bash
uv run pytest -q     # 68 passed
uv run ruff check .  # clean
uv run mypy src      # clean (24 source files)
```

**Iteration 1 (accuracy on AI data):** clean rights-linked dataset yields no REF002/RIGHTS001;
injecting 5 orphan rights references + 5 publication conflicts and scoring gives
**precision = recall = 1.0** for both rules (TP 5 each). The RIGHTS001 policy is mirrored in the
generator so clean data stays clean, and injection is disjoint (orphaned objects can't also be
conflict targets).

**Iteration 2 (VL-02):** the determinism harness now builds objects+media+rights seeded with all
five error types; all 5 rules pass stable + shuffled (three entity lists shuffled independently),
with guard tests asserting REF001/REF002/RIGHTS001 each produce their expected finding counts.

**Next:** commit, then VL-06 mutation on REF002 + RIGHTS001 (recorded next loop). Phase 2 rule
count after this slice: 5 of ~15.

---

## 2026-07-18 — Loop 11: VL-06 mutation on Slice D found and closed two RIGHTS001 gaps

**Slice:** Mutation-test REF002 + RIGHTS001 (Slice D's second validation).

**Mutations tried (8):** REF002 treat-all-valid (killed), REF002 weaken-severity (killed),
RIGHTS001 ignore-public-filter (killed), RIGHTS001 flag-even-when-permitted (killed), RIGHTS001
ignore-review_required (**SURVIVED**), RIGHTS001 ignore-publication_allowed (**SURVIVED**),
RIGHTS001 double-report-missing-rights (killed), RIGHTS001 weaken-severity (killed).

The two survivors were real gaps: the existing tests' conflict fixture (R-2) had
publication_allowed=false AND rights_status=restricted, so either condition alone still produced
the finding — neither the `review_required` nor the `publication_allowed` clause was independently
tested. Added three in-memory tests that isolate each clause: publication_allowed=false with a
permissive status/no review; review_required=true with publication allowed and permissive status;
and a fully-permissive control. Re-ran: **8/8 killed, zero survivors.**

Slice D validation approved (accuracy + VL-02 + VL-06). Phase 2 rule count: 5 of ~15
(CORE001, CORE002, REF001, REF002, RIGHTS001).

**Next slice:** Slice E — `LocationRecord` entity + LOC001 (multiple current locations) + LOC002
(missing parents / cycles in the location hierarchy), with injectors and two validated iterations.

---

## 2026-07-18 — Loop 12: Slice E — LocationRecord + LOC001 + LOC002 (iteration 1 + VL-02)

**Slice:** LocationRecord entity + LOC001 (object with >1 current location) + LOC002 (missing
parent / cycle in the hierarchy). LocationRecord rows are dual-purpose: an assignment
(object_id + is_current) feeds LOC001, a hierarchy node (location_id + parent_location_id) feeds
LOC002; a row may be both (documented in the model + rule docstrings).

**Files created/changed:** `canonical/models.py` (`LocationRecord`); `ingestion/mapper.py`
(`load_locations`, `_build_location`, `SCALAR_LOCATION_FIELDS`); `rules/base.py`
(`RuleContext.locations`); `rules/location_rules.py` (new — LOC001 high, LOC002 medium with
missing-parent + cycle detection via a parent-chain walk that flags only nodes actually on the
cycle); `rules/registry.py`; `cli.py` (`_load_entities` now 4-tuple); `benchmark/synthetic.py`
(`generate_clean_locations` — valid tree + one current assignment/object);
`benchmark/injectors.py` (`inject_extra_current_location`, `inject_location_hierarchy_errors`);
`benchmark/metrics.py` (LOC001/LOC002 scoring). Tests: `test_location_rules.py`,
`test_location_accuracy.py`; fixtures `locations.csv`, `mapping_locations.yaml`; VL-02 harness
extended to carry locations.

**Commands run and results:**

```bash
uv run pytest -q     # 84 passed
uv run ruff check .  # clean
uv run mypy src      # clean (25 source files)
```

**Iteration 1 (accuracy on AI data):** clean hierarchy + assignments yield no LOC001/LOC002;
injecting 4 extra current assignments + (2 missing parents + 2 cycles) and scoring gives
**precision = recall = 1.0** — LOC001 TP 4, LOC002 TP 6 (2 missing-parent nodes + 2 cycles × 2
nodes). Cycle detection verified to flag only the two nodes on each 2-cycle, not their descendants.

**Iteration 2 (VL-02):** determinism harness now builds all four entity types seeded with every
error class; all 7 rules pass stable + shuffled (four lists shuffled independently); guard tests
assert the expected finding counts for REF001/REF002/RIGHTS001/LOC001/LOC002.

**Next:** commit, then VL-06 mutation on LOC001/LOC002 (next loop). Phase 2 rule count: 7 of ~15.

---

## 2026-07-18 — Loop 13: VL-06 mutation on Slice E found and closed one LOC001 gap

**Slice:** Mutation-test LOC001 + LOC002 (Slice E's second validation).

**Mutations tried (7):** LOC001 off-by-one (killed), LOC001 ignore-is_current-filter
(**SURVIVED**), LOC001 weaken-severity (killed), LOC002 treat-all-parents-present (killed), LOC002
skip-cycle-detection (killed), LOC002 cycle-check-any-chain (killed), LOC002 weaken-severity
(killed).

The survivor was a real gap: the location fixture's assignments were all `is_current=true`, so
dropping the is_current filter didn't change the result. Added an in-memory test where an object
has one current and one non-current assignment (must not be flagged). Re-ran: **7/7 killed.**

Slice E validation approved (accuracy + VL-02 + VL-06). Phase 2 rule count: 7 of ~15
(CORE001/002, REF001/002, RIGHTS001, LOC001/002).

**Next slice:** Slice F — object-only rules DATE001 (inverted production date range), VOCAB001
(value outside a configured controlled vocabulary), SCHEMA001 (value not parseable to its declared
type). These need only the objects entity, so no new model or multi-entity work.

---

## 2026-07-18 — Loop 14: Slice F — object-only rules DATE001 + VOCAB001 + SCHEMA001

**Slice:** Three rules over the objects entity, no new model. Added production-date parsing to
ingestion.

**Files created/changed:** `ingestion/mapper.py` — `parse_date` (ISO + bare-year), `_date`,
production dates added to `SCALAR_OBJECT_FIELDS` + parsed in `_build_object`, `TYPED_OBJECT_FIELDS`
map, `object_field_sources` helper; `rules/base.py` — `RuleContext.controlled_vocabularies` +
`object_field_sources`; new `rules/date_rules.py` (DATE001 medium), `rules/vocabulary_rules.py`
(VOCAB001 medium, inactive without a configured vocabulary), `rules/schema_rules.py` (SCHEMA001
high — reuses the ingestion parser and reads the raw value back from provenance so the finding
shows the offending text); `rules/registry.py`; `cli.py` (`_load_entities` returns the field-source
map). Benchmark: `add_dates_and_status`, `OBJECT_WITH_DATES_COLUMNS`, `PUBLICATION_VOCABULARY`,
`inject_object_field_errors`, generic `expected_ids_for` + scoring. Tests:
`test_object_field_rules.py`, `test_object_field_accuracy.py`; fixtures
`objects_dates_vocab.csv`, `mapping_dates_vocab.yaml`; VL-02 harness extended.

**Commands run and results:**

```bash
uv run pytest -q     # 101 passed
uv run ruff check .  # clean
uv run mypy src      # clean (28 source files)
```

**Iteration 1 (accuracy on AI data):** clean objects (valid dates, in-vocab statuses) yield no
DATE001/VOCAB001/SCHEMA001; injecting 4 inverted ranges + 4 out-of-vocab values + 4 unparseable
dates and scoring gives **precision = recall = 1.0** for all three (TP 4 each). SCHEMA001 and
DATE001 share the same date parser so "valid date" is defined once. VOCAB001 and SCHEMA001 are
inactive without config (no vocabulary / no field-source map), verified by tests.

**Iteration 2 (VL-02):** harness extended so objects carry production dates + status + raw_fields;
DATE001 and SCHEMA001 exercised (2 each; guard tests assert the counts); all 10 rules pass stable +
shuffled. Fixed a compose-order bug where `add_dates_and_status` had overwritten the injected
RIGHTS001 statuses — it now preserves an existing publication_status.

**Next:** commit, then VL-06 mutation on DATE001/VOCAB001/SCHEMA001. Phase 2 rule count: 10 of ~15.

---

## 2026-07-18 — Loop 15: VL-06 mutation on Slice F found and closed one SCHEMA001 gap

**Slice:** Mutation-test DATE001 + VOCAB001 + SCHEMA001 (Slice F's second validation).

**Mutations tried (7):** DATE001 flip-comparison (killed), DATE001 weaken-severity (killed),
VOCAB001 accept-everything (killed), VOCAB001 weaken-severity (killed), SCHEMA001 never-flag
(killed), SCHEMA001 ignore-empty-guard (**SURVIVED**), SCHEMA001 weaken-severity (killed).

The survivor was a real gap: no test asserted that an *empty* typed field is treated as missing
rather than a type error. Dropping the `not raw` guard would flag empty dates. Added an in-memory
test with empty production dates that must produce no SCHEMA001. Re-ran: **7/7 killed.**

Slice F validation approved (accuracy + VL-02 + VL-06). Phase 2 rule count: 10 of ~15
(CORE001/002, REF001/002, RIGHTS001, LOC001/002, DATE001, VOCAB001, SCHEMA001).

**Next slice:** Slice G — media-file rules MEDIA001 (local file missing), MEDIA002 (duplicate file
hash), MEDIA003 (below minimum dimensions), MEDIA004 (unreadable image), plus DATE002 (agent
lifespan conflict). MEDIA00x need real local image files and Pillow (a new dependency, allowed by
the brief); DATE002 needs the AgentOrMaker entity.

---

## 2026-07-18 — Loop 16: Slice G — MEDIA001-004 (Pillow) + DATE002 (all 15 rules now implemented)

**Slice:** The four media-file rules plus DATE002, completing the initial 15-rule set. Added
Pillow as a dependency.

**Files created/changed:** `pyproject.toml` (pillow); `engine/media_files.py` (new — path
resolution with a traversal guard, image size + readability via Pillow); `rules/media_rules.py`
(new — MEDIA001 high, MEDIA002 medium, MEDIA003 medium, MEDIA004 high; inactive unless
`check_media_files` + `media_root` set); `canonical/models.py` (`AgentOrMaker`); `ingestion/mapper.py`
(`load_agents`, `_build_agent`, `SCALAR_AGENT_FIELDS`); `rules/date_rules.py`
(`AgentLifespanConflictRule` — DATE002 medium, conservative: only clear impossibilities, only when
object production dates AND maker birth/death dates are all present); `rules/base.py`
(`RuleContext.agents` + media-file config fields); `rules/registry.py`; `cli.py` (`--media-root`,
`--min-image-width/height`; 6-tuple `_load_entities`). Tests: `test_media_rules.py` (real PNGs via
Pillow, incl. path-traversal refusal), `test_media_accuracy.py`, `test_date002_rule.py`;
`benchmark/metrics.py` scores MEDIA001-004.

**Commands run and results:**

```bash
uv sync              # + pillow 12.3.0
uv run pytest -q     # 127 passed
uv run ruff check .  # clean
uv run mypy src      # clean (30 source files)
```

**Iteration 1 (accuracy on AI data):** MEDIA rules — generated valid PNGs + a media table (clean =
no findings), injected missing files, byte-identical duplicates, undersized images, and corrupt
files → **precision = recall = 1.0** for all four (a nice moment: MEDIA002 caught that two corrupt
files were byte-identical, an unlabelled true duplicate, which surfaced a test-data bug I then
fixed). DATE002 — unit tests cover production-before-birth, production-after-death, within-lifespan
(no finding), and imprecise-dates (inactive). Path-traversal refusal is tested
(`../../etc/passwd` is never followed).

**Iteration 2 (VL-06 mutation):** ran a mutation loop on MEDIA001-004, the path-resolution guard,
and DATE002 (7 mutations): never-flag-missing, MEDIA002 off-by-one, MEDIA003 flipped dimension
check, never-flag-unreadable, allow-path-traversal, DATE002 ignore-before-birth,
ignore-after-death. **7/7 killed on the first pass, zero survivors** — notably the
allow-path-traversal mutant was caught by the traversal-refusal test. VL-06 met for Slice G with no
new gaps.

Slice G validation approved (accuracy + VL-06). Phase 2 rule count: **15 of 15** — the full initial
rule set from Section 11 is implemented (CORE001/002, SCHEMA001, REF001/002, LOC001/002,
RIGHTS001, DATE001/002, VOCAB001, MEDIA001/002/003/004).

**Next slice:** Slice H — the run store (persist scan records/findings for history), the last
remaining Phase 2 checklist item.

---

## 2026-07-18 — Loop 17: Slice H — run store (last Phase 2 item)

**Slice:** Persist scan history so baselines / "what changed" become possible in Phase 3.

**Files created/changed:** `engine/run_store.py` (new — `RunSummary`, `summarize` (severity counts
+ sorted fingerprints), `RunStore` with `save`/`list_runs`/`latest`; one JSON file per run;
DuckDB deferred per BUILD_PLAN); `cli.py` (`--run-store` option persists the run after a scan).
Tests: `test_run_store.py` (summarize counts, save/list roundtrip, reload-equal, empty store,
fingerprint stability for identical findings), plus a CLI integration test that `--run-store`
writes a record.

**Commands run and results:**

```bash
uv run pytest -q     # 133 passed
uv run ruff check .  # clean
uv run mypy src      # clean (31 source files)
uv run collection-ci scan --objects-csv benchmarks/mini/objects_dirty.csv \
  --run-store <dir> --fail-on none
  # -> Recorded run: total 8, severity {critical:4, high:4}, 8 fingerprints
```

**Iteration 1 (build + unit validation):** roundtrip save/list/reload verified equal; the persisted
record for the dirty benchmark has the expected 8 findings and severity split; a stability test
confirms identical findings persist identical fingerprint sets (the property baselines will rely
on).

**Iteration 2 (VL-06):** ran a mutation loop on the run store (5 mutations): wrong total, drop
fingerprint sort, reverse list order, latest-returns-first, empty severity counts. First pass had
**3 survivors** — the sort/ordering guarantees were untested. Added tests pinning ascending
fingerprint order (feeding findings in reverse), oldest-first `list_runs`, and `latest` = most
recent. Re-ran: **5/5 killed.**

Slice H validation approved (unit + VL-06).

---

## 2026-07-18 — Phase 2 complete

All Phase 2 slices are done, each with >=2 validated iterations (accuracy on AI-generated data
and/or VL-02 determinism, plus VL-06 mutation):

- Slice C: multi-entity ingestion + MediaAsset + REF001
- Slice D: RightsRecord + REF002 + RIGHTS001
- Slice E: LocationRecord + LOC001 + LOC002
- Slice F: DATE001 + VOCAB001 + SCHEMA001
- Slice G: MEDIA001-004 + DATE002 (all 15 Section-11 rules now implemented)
- Slice H: run store

**Phase 2 checklist (BUILD_BRIEF.md Section 24) status:** CSV + JSON adapters (done), mapping
engine (done), rule base class + registry (done), initial rules (15/15 done), finding model +
fingerprints (done), run store (done), console + JSON output (done), comprehensive tests (133
passing). Validation: VL-01 partial-pass at P=R=1.0 for the 14 injectable rules (DATE002
unit-tested), VL-02 active over all rules, VL-06 run per slice (found and closed 10 real test gaps
across the phase).

**Aggregate:** 133 tests passing, ruff + mypy clean, 15 deterministic rules across 6 entity types,
a synthetic benchmark scoring every injectable rule at precision = recall = 1.0. Commits
af6034f..(this loop), none pushed (no git remote).

**Next (Phase 3):** reports (CSV/HTML/SARIF/run-manifest), baseline comparison + `--only-new`
(VL-03), the `collection-ci benchmark` CLI command, full clean/dirty example datasets, and the
adversarial (VL-04) and fuzz (VL-05) robustness loops.

---

## 2026-07-19 — Loop 18: Slice I — structured report outputs (CSV + summary + run manifest)

**Slice:** Phase 3 goal (complete all Phase 3 slices, validate on AI-generated data, >=2 iterations
each). Slice I adds the non-visual report outputs beside findings.json.

**Files created/changed:** `reporting/json_report.py` (refactored out of the CLI),
`reporting/csv_report.py` (flattened columns + a JSON evidence column, rows sorted by fingerprint),
`reporting/summary.py` (counts by severity/rule + input counts), `engine/run_manifest.py`
(software version, command, run id, timestamps, elapsed, input + config file sha256 hashes, enabled
rules + versions, severity counts, network/AI = False, environment); `ingestion/mapper.py`
(`resolve_entity_files` for manifest hashing); `cli.py` now times the run and writes findings.json,
findings.csv, summary.json, run_manifest.json. Tests: `test_reports_structured.py`,
`test_report_fidelity.py`, extended `test_scan_cli.py`.

**Commands run and results:**

```bash
uv run pytest -q     # 143 passed
uv run ruff check .  # clean
uv run mypy src      # clean (35 source files)
uv run collection-ci scan --objects-csv benchmarks/mini/objects_dirty.csv --output-dir <d>
  # -> findings.json/.csv, summary.json, run_manifest.json; manifest has input hash,
  #    15 enabled rules, severity {critical:4, high:4}, network/ai = False
```

**Iteration 1 (fidelity + determinism on AI data):** on the synthetic dirty dataset, JSON and CSV
reports capture exactly the finding fingerprint set with no loss; summary counts match; and writing
each report twice is byte-identical (the property CSV/JSON baselines depend on). Manifest records
the input file hash and the network/AI=False flags.

**Iteration 2 (VL-06):** mutation loop on the report writers + manifest (6 mutations): csv
drop-fingerprint-sort, summary wrong-total, summary drop-rule-counts, manifest claim-network-used,
manifest claim-ai-used, manifest wrong-total. First pass had **1 survivor** — the CSV sort test's
sample was already sorted. Fixed by feeding findings in reverse order so the sort is exercised.
Re-ran: **6/6 killed.** The claim-network-used / claim-ai-used mutants being caught is meaningful:
the suite would notice if the manifest ever falsely claimed the offline engine used the network or
an AI provider.

Slice I validation approved (fidelity + determinism + VL-06).

**Next slice:** Slice J — standalone HTML report (Jinja2, no external assets, accessible).

---

## 2026-07-19 — Loop 19: Slice J — standalone HTML report

**Slice:** A self-contained, accessible HTML report (added Jinja2).

**Files created/changed:** `reporting/html_report.py` (inline CSS + JS, no external assets;
Jinja2 autoescape on; severity shown as text label + color; severity filter via inline vanilla JS;
run summary, severity distribution, rules-evaluated table, findings with expandable evidence +
recommendation + fingerprint, provenance with input hashes, disclaimer; light/dark via
prefers-color-scheme; empty state); `cli.py` writes `report.html`. Tests: `test_html_report.py`
(self-contained, lists all findings, **escapes an injected `<script>` payload**, empty state,
disclaimer + provenance), extended `test_report_fidelity.py` and `test_scan_cli.py`.

**Commands run and results:**

```bash
uv sync              # + jinja2 3.1.6
uv run pytest -q     # 149 passed
uv run ruff check .; uv run mypy src   # clean (36 source files)
uv run collection-ci scan --objects-csv benchmarks/mini/objects_dirty.csv --output-dir <d>
  # -> report.html (16 KB); grep for external asset refs (http/https/cdn) = none; disclaimer present
```

**Iteration 1 (fidelity + safety on AI data):** every finding's entity id appears in the rendered
report for the synthetic dataset; the report contains no externally hosted assets (asserted no
`src="http`, `href="http`, `@import`, `cdn`); a `<script>alert('xss')</script>` payload in a
finding summary is escaped to `&lt;script&gt;` rather than rendered live (threat-model
sanitization). Severity is conveyed as text, not color alone (accessibility).

**Iteration 2 (VL-06):** mutation loop on the HTML report (4 mutations): disable autoescape,
drop findings, blank enabled rules, reverse severity order. First pass **2 survivors** (the
rules-evaluated table and severity ordering were unasserted). Added a test that an enabled rule
with zero findings still appears (rules-evaluated table) and a test that critical renders before
high. Re-ran: **4/4 killed.** The disable-autoescape mutant being caught confirms the XSS-escaping
test genuinely guards the sanitization.

Slice J validation approved (fidelity + safety + VL-06).

**Next slice:** Slice K — SARIF 2.1.0 output with a structural validation test.

---

## 2026-07-19 — Loop 20: Slice K — SARIF 2.1.0 output

**Slice:** Emit findings as SARIF 2.1.0 so a GitHub code-scanning upload annotates source files.

**Files created/changed:** `reporting/sarif_report.py` (severity->level map: critical/high=error,
medium=warning, low=note; driver with tool name/version + declared rules; results with ruleId +
ruleIndex, level, message, physicalLocation from evidence source_file/row, and the stable
fingerprint as a partialFingerprint; any finding whose rule wasn't in the passed metadata is still
declared so no result dangles); `cli.py` writes `results.sarif`. Tests: `test_sarif_report.py`
(level mapping, top-level structure, every result well-formed + references a declared rule +
ruleIndex matches, location maps file/row, unknown-rule-still-declared), CLI integration assertion.

**Commands run and results:**

```bash
uv run pytest -q     # 156 passed
uv run ruff check .; uv run mypy src   # clean (37 source files)
uv run collection-ci scan --objects-csv benchmarks/mini/objects_dirty.csv --output-dir <d>
  # -> results.sarif: version 2.1.0, 15 declared rules, 8 results, level=error,
  #    location objects_dirty.csv row 10, partialFingerprint present
```

**Iteration 1 (structural validation):** the SARIF validates structurally — version 2.1.0, one
run, a driver with declared rules, and every result carries a valid level, a message, a
partialFingerprint, and a ruleId/ruleIndex that resolves to a declared rule. Source locations map
the evidence file + row.

**Iteration 2 (VL-06):** mutation loop on the SARIF writer (6 mutations: wrong version,
critical->note, medium->error, drop partial fingerprints, skip declaring finding rules, drop
startLine). **6/6 killed on the first pass, zero survivors.**

Slice K validation approved (structural validation + VL-06).

**Next slice:** Slice L — baseline comparison (new/unchanged/resolved) + `--only-new`, implementing
the VL-03 baseline round-trip loop.

---

## 2026-07-19 — Loop 21: Slice L — baselines + --only-new (VL-03 now active)

**Slice:** Compare a scan against a prior findings.json by fingerprint (new/unchanged/resolved),
with `--only-new` making the failure threshold consider only new findings.

**Files created/changed:** `engine/baselines.py` (`load_baseline_fingerprints`, `classify` ->
`BaselineComparison` with counts); `cli.py` (`--baseline`, `--only-new`; prints the comparison,
writes `baseline_comparison.json`, and restricts the threshold to new findings under --only-new;
the full reports still list every finding, per the brief). Tests: `test_baselines.py` (unit) and
`tests/e2e/test_baseline_roundtrip.py` (the VL-03 loop end-to-end).

**Commands run and results:**

```bash
uv run pytest -q     # 161 passed
uv run ruff check .; uv run mypy src   # clean (38 source files)
# manual round-trip: rescan identical input with --baseline --only-new -> "0 new, 8 unchanged,
#   0 resolved", exit 0
```

**Iteration 1 = VL-03 done:** the end-to-end round-trip passes on AI-generated data: (1) rescan of
identical input with `--only-new` reports zero new and exits 0 even at `--fail-on critical`;
(2) adding one fresh duplicate accession yields >=1 new and exit 1; (3) repairing a pre-existing
missing field yields >=1 resolved vs the baseline. This is exactly the VL-03 loop's done condition.

**Iteration 2 (VL-06):** mutation loop on the baseline classifier (4 mutations: invert new
membership, invert unchanged membership, resolved wrong direction, accept non-array baseline).
**4/4 killed on the first pass.**

Slice L validation approved (VL-03 e2e + VL-06). VL-03 is now `active`.

**Next slice:** Slice M — the `collection-ci benchmark` CLI command (inject errors, scan, score
precision/recall/F1 per rule, write a report).

---

## 2026-07-19 — Loop 22: Slice M — `collection-ci benchmark` command

**Slice:** A reproducible benchmark command that generates data, injects labeled errors, scans,
and scores precision/recall/F1 per rule.

**Files created/changed:** `benchmark/runner.py` (`run_benchmark` -> `BenchmarkResult` with
per-rule precision/recall/F1/TP/FP/FN, runtime, `meets_target`; covers the 5 object-level rules —
CORE001/002, DATE001, VOCAB001, SCHEMA001 — multi-entity coverage is backlog); `cli.py`
`benchmark` command (writes `benchmark_report.json`, prints a rich table, exits 0 iff every rule
meets P=R=1.0). Tests: `test_benchmark_runner.py` (perfect P/R, determinism by seed, CLI writes
report + exits 0).

**Commands run and results:**

```bash
uv run pytest -q     # 164 passed
uv run ruff check .; uv run mypy src   # clean (39 source files)
uv run collection-ci benchmark --output-dir <d>
  # -> table: all 5 rules precision/recall/F1 = 1.00; 20 findings; runtime ~0.002s;
  #    meets target: yes; exit 0
```

**Iteration 1 (accuracy + determinism):** the benchmark scores all five object-level rules at
**precision = recall = F1 = 1.0** (20 findings = 5 rules x 4 injected errors), and `run_benchmark`
is deterministic by seed (identical per-rule metrics and finding count across two runs). The CLI
command writes `benchmark_report.json` and exits 0 only when the target is met (1 otherwise).

**Iteration 2 (VL-06):** mutation loop on the benchmark runner (4 mutations: meets_target
always-true, skip field-error injection, drop raw_fields, don't parse start date). First pass
**1 survivor** (meets_target only tested on the happy path). Added a negative test with an
underperforming rule -> meets_target False. Re-ran: **4/4 killed.**

Slice M validation approved (accuracy + determinism + VL-06).

**Next slice:** Slice N — full clean/dirty example datasets, end-to-end tests, a demo workflow
(docs/DEMO.md), and the Phase 3 CI steps (SARIF validation, HTML artifact upload, benchmark).

---

## 2026-07-19 — Loop 23: Slice N — full examples + e2e + demo + Phase 3 CI

**Slice:** Committed clean/dirty example datasets (250 objects), end-to-end tests, the demo guide,
and Phase 3 CI steps.

**Files created/changed:** `examples/generate.py` (deterministic; writes clean + dirty
objects.csv with dates/status, two mappings with correct base_path, and
`examples/expected/dirty_expected.json`); `examples/clean/objects.csv` (now 250 objects),
`examples/dirty/objects.csv`, `examples/mappings/clean.yaml`, `dirty.yaml`; `docs/DEMO.md`
(reproducible 7-step 5-minute demo); `.github/workflows/ci.yml` (sample scan now uses the clean
mapping, added a benchmark step and an HTML-report artifact upload);
`.github/workflows/collection-integrity-demo.yml` (new — scans the dirty example with
`--fail-on none` so expected data findings don't fail software CI, uploads findings + SARIF).
Tests: `tests/e2e/test_examples.py`.

**Commands run and results:**

```bash
uv run python examples/generate.py   # clean(250) + dirty; expected 5 each of CORE001/002/DATE001/SCHEMA001
uv run pytest -q                     # 167 passed
uv run ruff check .; uv run mypy src # clean
uv run collection-ci scan --mapping examples/mappings/clean.yaml ...  # 0 findings, exit 0
uv run collection-ci scan --mapping examples/mappings/dirty.yaml ...  # 20 findings, exit 1
```

**Iteration 1 (e2e behavior):** the clean example scans to zero findings (exit 0); the dirty
example scans to exactly the findings recorded in `dirty_expected.json` — 5 each of CORE001,
CORE002, DATE001, SCHEMA001 over 250 objects — and exits 1. The e2e test asserts the dirty summary
equals the expected manifest, so drift in either the data or the engine breaks CI.

**Iteration 2 (determinism):** re-ran `examples/generate.py` and confirmed the committed clean +
dirty CSVs, mappings, and expected manifest are reproduced **byte-identically** (empty `git diff`).

Slice N validation approved (e2e behavior + determinism).

---

## 2026-07-19 — Phase 3 complete

All Phase 3 slices done, each with two validated iterations:

- Slice I: CSV + summary + run-manifest outputs
- Slice J: standalone HTML report (self-contained, accessible, XSS-safe)
- Slice K: SARIF 2.1.0
- Slice L: baselines + `--only-new` (VL-03 now active)
- Slice M: `collection-ci benchmark` command
- Slice N: full example datasets + e2e + demo + Phase 3 CI

**Phase 3 checklist (BUILD_BRIEF.md Section 24) status:** CSV/HTML/SARIF/manifest outputs (done),
baseline comparison (done), full clean/dirty examples (done — 250 objects), deterministic error
injection (done, Phase 2), benchmark metrics + report + command (done), e2e tests (done, `tests/e2e/`),
demo workflow (done, `docs/DEMO.md` + `collection-integrity-demo.yml`).

**Validation loop status:** VL-01 partial (14 rules P=R=1.0; benchmark command scores 5 at 1.0),
VL-02 active, VL-03 active (e2e round-trip), VL-06 active (found+closed 15 real gaps across Phases
2-3). VL-04 partial (path traversal + XSS escaping tested), VL-05 (fuzz) still pending.

**Aggregate:** 167 tests passing, ruff + mypy clean, package builds. A scan now emits findings.json,
findings.csv, summary.json, run_manifest.json, report.html, and results.sarif; baselines + benchmark
+ run store are wired; CI runs lint/format/types/tests/build/benchmark/sample-scan and a separate
demo workflow. Commits af6034f..(this loop), none pushed (no git remote).

**Next (Phase 4+):** museum-data source adapters (Met/Cleveland/NGA), the local web viewer (Phase 5),
optional ArtiFact/probabilistic experiment (Phase 6), and the GitHub Pages showcase (Phase 7).
Remaining validation loops: VL-04 (broaden the adversarial fixture set), VL-05 (Hypothesis fuzz),
VL-07 (coverage ratchet in CI), VL-08 (execute the README quick start verbatim), VL-10 (final
Definition-of-Done pass).
