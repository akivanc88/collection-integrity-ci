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

---

## 2026-07-19 — Loop 24: Normalize entity file paths in provenance

**Slice:** Fix a provenance-quality issue surfaced while tracing a finding's evidence chain
end-to-end: when a mapping's `base_path` uses a relative `..` segment (e.g. the example datasets'
`base_path: ../dirty` resolved from `examples/mappings/`), the `source_file` recorded in every
`SourceRef` — and shown in findings, reports, and the run manifest — carried the uncollapsed
`examples/mappings/../dirty/objects.csv` instead of the clean `examples/dirty/objects.csv`. Correct
and resolvable, but ugly in a report a registrar reads.

**Files changed:** `ingestion/mapper.py` — added `_entity_file_path()` helper that builds the
entity data-file path and lexically normalizes it with `os.path.normpath` (collapses `..` without
resolving to an absolute path, so reports stay machine-independent and byte-reproducible). Routed
both path-construction sites through it: `_load_entity_records` (the provenance `SourceRef`) and
`resolve_entity_files` (manifest hashing), so the two can't drift.

**Design note:** deliberately `normpath`, not `Path.resolve()` — `resolve()` would emit an absolute,
machine-specific path and break the reproducibility guarantee. The finding fingerprint does not
include `source_file`, so this is a display-only change: existing baselines still match (verified).

**Commands run and results:**

```bash
uv run ruff check . ; uv run ruff format --check . ; uv run mypy src   # clean (39 source files)
uv run pytest -q                                                       # 167 passed
uv run collection-ci scan --mapping examples/mappings/dirty.yaml --output-dir <d>
  # -> evidence source_file now 'examples/dirty/objects.csv' (was 'examples/mappings/../dirty/...')
  #    same CORE001 finding fingerprint 0da315c3... UNCHANGED (source_file not in fingerprint)
```

**Validation:** full suite green with no test changes needed (no test had hard-coded the old `..`
form, and no committed golden/expected artifact contained it — grep-verified). Fingerprint stability
confirmed by hand: the traced CORE001 duplicate keeps fingerprint `0da315c3…` before and after, so
`--baseline`/`--only-new` will not flag spurious new findings from the path cleanup.

**Next slice:** unchanged — Phase 4 (Met CSV source adapter), or one of the pending validation loops
(VL-05 fuzz / VL-08 README-executes).

---

## 2026-07-19 — Loop 25: Phase 4 Slice O — source-adapter framework + Met adapter

**Slice:** New `/goal` — complete all Phase 4 slices (Met/Cleveland/NGA source adapters + bounded
download scripts + attribution docs), each with >=2 validated iterations on AI-generated datasets.
Slice O is the adapter framework and the first adapter (the Met).

**Design decision:** a "source adapter" is a *built-in, versioned `DatasetMapping` profile* for a
known institution's published open-data schema, not a new ingestion path. The adapter constructs
the same mapping the YAML path uses, so the entire existing ingestion/transform/provenance/rule
pipeline is reused unchanged. This keeps the new code tiny and inherits all prior validation. Only
genuinely relational sources (the NGA link table, Slice Q) will need bespoke loading.

**Files created/changed:**

- `ingestion/source_base.py` (new) — `build_objects_mapping()` shared by single-file adapters; the
  `SourceBuilder` type.
- `ingestion/met_adapter.py` (new) — `FIELD_MAP` from canonical fields to the real
  `MetObjects.csv` headers (`Object Number`, `Object ID`, `Object Begin/End Date`, ...) and
  `build_mapping()`.
- `ingestion/sources.py` (new) — the source registry (`available_sources`, `build_source_mapping`)
  with name + input-existence validation.
- `cli.py` — added `--source NAME --input PATH` as a third input mode alongside `--objects-csv` /
  `--mapping`; refactored input resolution into `_resolve_mapping()` and made `_load_entities`
  operate on an in-memory `DatasetMapping` + base dir (removing a duplicate mapping load for the
  manifest). Exactly-one-input and paired-flag validation with exit code 2.
- `benchmark/source_fixtures.py` (new) — `write_met_dataset()` emits a **real-Met-schema** CSV with
  disjoint, leakage-free labeled injected errors (CORE001/002, DATE001, SCHEMA001), plus `score()`
  (precision/recall/F1 vs. ground truth). Reusable by the Cleveland/NGA slices.
- Tests: `tests/integration/test_met_adapter.py`, `tests/integration/test_source_cli.py`.

**Commands run and results:**

```bash
uv run ruff check . ; uv run ruff format --check . ; uv run mypy src   # clean (43 source files)
uv run pytest -q                                                       # 177 passed
uv run collection-ci scan --source met --input <MetObjects.csv> --fail-on none
  # -> real Met columns ingested; CORE001 dup accession, DATE001 inverted range, SCHEMA001
  #    invalid Object Begin Date all detected from the Met's native headers
```

**Iteration 1 (accuracy on AI-generated data):** a generated Met-schema dataset (40 clean + 12
injected across four rules) ingested through the `met` adapter scores **precision = recall = 1.0**
on every injected rule, with zero findings on the clean rows and no rule outside the injected set
firing. A determinism test confirms the generator is byte-reproducible; a shape test pins the Met
column headers + `object_id` primary key. CLI end-to-end test asserts the summary counts, exit
codes, and that the run manifest hashes the real input file (no config file in source mode).

**Iteration 2 (VL-06 mutation):** mutation loop on the Slice O code (7 mutations: wrong accession
column, wrong begin-date column, unknown-source not rejected, missing-input not rejected, wrong
primary-key default, inverted paired-flag check, weakened exactly-one-input check). First pass
**2 survivors** — no test asserted (a) `--source --input <missing>` errors, or (b) the mapping's
`primary_key` (the fixture's title was always non-empty, masking the swap). Added a missing-input
CLI test and a `primary_key == "object_id"` assertion. Re-ran: **7/7 killed, zero survivors.**

Slice O validation approved (accuracy P=R=1.0 + CLI e2e + determinism, and VL-06).

**Next slice:** Slice P — Cleveland Museum of Art adapter (CSV and JSON), reusing the fixture/score
harness, with two validated iterations.

---

## 2026-07-19 — Loop 26: Phase 4 Slice P — Cleveland adapter (CSV + JSON)

**Slice:** The Cleveland Museum of Art Open Access adapter, which publishes the same schema as both
`openaccess.csv` and `openaccess.json` — so the adapter picks the format from the file extension and
one field map serves both.

**Files created/changed:**

- `ingestion/cleveland_adapter.py` (new) — `FIELD_MAP` to the real Cleveland columns (`id`,
  `accession_number`, `type`, `creation_date_earliest/latest`, ...), `_format_for()` (extension ->
  csv/json), `build_mapping()`.
- `ingestion/sources.py` — registered `cleveland`.
- `benchmark/source_fixtures.py` — refactored to be schema-driven: a `SchemaSpec` (canonical field
  -> source column) plus `write_dataset(path, spec, fmt=...)` serializing identical rows/injections
  as CSV or JSON. `MET_SPEC` + `CLEVELAND_SPEC`; `write_met_dataset` kept as a thin wrapper so
  Slice O's tests are unchanged.
- Tests: `tests/integration/test_cleveland_adapter.py`.

**Commands run and results:**

```bash
uv run ruff check . ; uv run ruff format --check . ; uv run mypy src   # clean (44 source files)
uv run pytest -q                                                       # 182 passed
```

**Iteration 1 (accuracy + CSV/JSON equivalence on AI-generated data):** a Cleveland-schema dataset
(40 clean + 12 injected) ingested through the `cleveland` adapter scores **precision = recall = 1.0**
for CORE001/002, DATE001, SCHEMA001 in **both CSV and JSON**, with zero findings on clean rows. A
dedicated test asserts CSV and JSON yield the **identical finding fingerprint set** (the reader
paths converge on the same canonical records), and a shape test pins the format-by-extension logic
and column names.

**Iteration 2 (VL-06 mutation):** mutation loop on the Cleveland adapter (4 mutations: accession
mapped to wrong column, start-date mapped to wrong column, format forced always-csv, format forced
always-json). **4/4 killed on the first pass, zero survivors** — the format-forcing mutants are
caught because reading a JSON file as CSV (and vice-versa) breaks the equivalence/accuracy tests.

Slice P validation approved (accuracy P=R=1.0 in both formats + CSV/JSON equivalence + VL-06).

**Next slice:** Slice Q — National Gallery of Art adapter, the relational one: a many-to-many
object<->constituent link table joined to populate agents + maker links, exercising DATE002 (agent
lifespan vs. production date) which a flat mapping cannot express.

---

## 2026-07-19 — Loop 27: Phase 4 Slice Q — NGA relational adapter (link-table join + DATE002)

**Slice:** The National Gallery of Art Open Data adapter — the one source that is genuinely
relational (`objects.csv` + a many-to-many `objects_constituents.csv` link table +
`constituents.csv`), which a flat column mapping cannot express.

**Design:** introduced a `SourceLoad` abstraction (canonical entities + object field sources +
input-file list) and `load_from_mapping()` in `source_base`, so all three adapters return loaded
entities uniformly and the CLI has one ingestion path. Met and Cleveland now expose `load()` that
routes through `load_from_mapping`; the CLI's three input modes were unified into a single `_ingest`
(the `--mapping` path now reuses `load_from_mapping` too, removing a duplicate mapping load). The NGA
adapter reuses the ordinary mapper for `objects.csv` (objects entity) and `constituents.csv` (agents
entity) — inheriting provenance, date parsing, and SCHEMA001 field sources — and adds only the join:
it reads the link table into `{objectid: [constituentid,...]}` (ordered by displayorder) and stamps
each frozen object's `maker_ids` via `model_copy`. That maker link is what lets **DATE002** (production
after the linked maker's death) run.

**Files created/changed:** `ingestion/source_base.py` (`SourceLoad`, `SourceLoader`,
`load_from_mapping`), `ingestion/nga_adapter.py` (new — mapping + `_maker_ids_by_object` join +
`load`), `ingestion/met_adapter.py` / `cleveland_adapter.py` (added `load`), `ingestion/sources.py`
(registry now maps to loaders; `load_source` replaces `build_source_mapping`), `cli.py` (unified
`_ingest`), `benchmark/source_fixtures.py` (`write_nga_dataset` — 3-file NGA-schema generator with
labeled DATE002 conflicts + object-level errors, disjoint and leakage-free). Tests:
`tests/integration/test_nga_adapter.py`; updated the Met/Cleveland test helpers to use `load_source`.

**Commands run and results:**

```bash
uv run ruff check . ; uv run ruff format --check . ; uv run mypy src   # clean (45 source files)
uv run pytest -q                                                       # 186 passed
uv run collection-ci scan --source nga --input <dir> --fail-on none
  # -> 46 objects; CORE001 + DATE001 + SCHEMA001 + DATE002 all fire; manifest hashes all 3 files
```

**Iteration 1 (accuracy on AI-generated data):** a generated NGA-schema directory scores
**precision = recall = 1.0** for CORE001, DATE001, SCHEMA001, and **DATE002** — the last of which
only fires because the link table was joined correctly. Extra tests assert the join populates
`maker_ids` (incl. a two-maker object), that maker order follows `displayorder` regardless of
link-row order, and that a missing link table errors clearly.

**Iteration 2 (VL-06 mutation):** mutation loop on the NGA adapter (6 mutations: object accession /
begin-date / agent death-date mapped to wrong columns, maker_ids not stamped from the join, link
order not sorted, missing-link-table not rejected). **6/6 killed on the first pass, zero survivors**
— notably the join-not-stamped mutant (DATE002 recall -> 0) and the order-not-sorted mutant (caught
by the reversed-link determinism test).

Slice Q validation approved (accuracy P=R=1.0 incl. DATE002 + VL-06). The Met/Cleveland refactor to
`load_source` kept all prior tests green (186 passing).

**Next slice:** Slice R — bounded sample-download scripts (`--limit`, explicit local paths, never a
full auto-download) and `docs/DATA_SOURCES.md` provenance/attribution, completing Phase 4.

---

## 2026-07-19 — Loop 28: Phase 4 Slice R — bounded sample-download scripts + attribution docs

**Slice:** The last Phase 4 item — bounded sampling tooling and provenance/attribution
documentation. The Section 20 safety rule ("never download an entire large dataset automatically;
provide --limit and explicit paths") is enforced structurally, not by convention.

**Files created/changed:** `ingestion/sampling.py` (new — `take_bounded_lines`, the single safety
boundary that stops after `limit` records even on an unbounded stream; `bound_csv_text`;
`bound_nga_directory`, a referentially-consistent relational sample: N objects + only the links and
constituents they reference); `scripts/fetch_sample.py` (new — argparse CLI; requires an explicit
`--from` local path or `--url`, no default remote; a `MAX_LIMIT` ceiling; NGA relational mode; the
network path streams through the same tested bound); `docs/DATA_SOURCES.md` (new — provenance, CC0
licenses, per-adapter field maps, safety/no-images notes, honest limitations, validation pointer);
`CLAUDE.md` (refreshed the stale "Current phase" note to Phases 0–4 complete). Tests:
`tests/unit/test_sampling.py`, `tests/integration/test_fetch_sample_script.py`.

**Commands run and results:**

```bash
uv run ruff check . ; uv run ruff format --check . ; uv run mypy src   # clean (46 source files)
uv run pytest -q                                                       # 196 passed
python scripts/fetch_sample.py --source nga --from <dir> --limit 5 --output <out>
  # -> writes objects(5) + only referenced links/constituents; re-ingests cleanly via the adapter
```

**Iteration 1 (behavior on AI-generated data):** `take_bounded_lines` returns exactly header +
`limit` rows and — the key safety property — **returns rather than hanging when fed an infinite line
generator**, proving the bound holds regardless of input size. `bound_nga_directory` produces a
subset with no dangling references (every link points at a kept object and a kept constituent; no
orphan constituents), and the bounded NGA sample **re-ingests through the `nga` adapter** with the
object count equal to the limit and every maker link resolving to a kept agent. The script's
subprocess tests cover local Met bounding, relational NGA bounding, and the guards
(exactly-one-of `--from`/`--url`, the limit ceiling).

**Iteration 2 (VL-06 mutation):** mutation loop on `sampling.py` (6 mutations: off-by-one row bound,
dropped negative-limit guard, header omitted, objects not bounded by limit, links not filtered,
constituents not filtered). **6/6 killed on the first pass, zero survivors.**

Slice R validation approved (bounded-safety + referential-consistency + round-trip + VL-06).

---

## 2026-07-19 — Phase 4 complete

All Phase 4 slices done, each with two validated iterations (accuracy on AI-generated real-schema
data + VL-06 mutation):

- Slice O: source-adapter framework + Met adapter
- Slice P: Cleveland adapter (CSV + JSON, equivalence-checked)
- Slice Q: NGA relational adapter (link-table join → maker_ids/agents, DATE002)
- Slice R: bounded sample-download scripts + `docs/DATA_SOURCES.md`

**Phase 4 checklist (BUILD_BRIEF.md Section 24):** Met adapter (done), Cleveland adapter (done),
NGA adapter (done), bounded sample scripts with `--limit`/explicit paths (done), provenance +
attribution documentation (done, `docs/DATA_SOURCES.md`).

**Design through-line:** an adapter is a built-in, versioned mapping profile (`SourceLoad` +
`load_from_mapping`) that reuses the whole existing ingestion/provenance/rule pipeline; only the NGA
many-to-many join needed bespoke code. Every adapter was validated on synthetic data built in the
institution's real published schema, scored at precision = recall = 1.0, and hardened with a VL-06
mutation pass (found and closed 2 real test gaps in Slice O).

**Aggregate:** 196 tests passing, ruff + mypy clean. Three museum source adapters plus bounded,
safety-capped sampling; the offline core still makes no network calls. Commits bf9454c..(this loop),
none pushed (no git remote).

**Next (Phase 5):** the local web viewer (FastAPI), now unblocked — but per the brief, build it only
after confirming the engine/reports/benchmark/tests are stable (they are). Remaining validation
loops: VL-04 (broaden adversarial fixtures), VL-05 (Hypothesis fuzz), VL-07 (coverage ratchet),
VL-08 (README quick start executes), VL-10 (final Definition-of-Done pass).

---

## 2026-07-21 — Loop 29: Phase 5 Slice S — viewer API foundation (serve command + JSON API)

**Slice:** New `/goal` — complete all Phase 5 slices (the local web viewer), each with >=2 validated
iterations on AI-generated data. Slice S is the API foundation: the `serve` command, a read-only run
loader, and the JSON API. Phases 1–3 are stable, so the Phase 5 gate is satisfied.

**Design (see `docs/adr/ADR-007-web-viewer.md`):** a server-rendered FastAPI app serving a
*read-only snapshot* of a completed scan run directory — never a live re-run, never a write. The
viewer consumes the report format (findings.json/summary.json/run_manifest.json), not the engine's
models, staying decoupled from the engine. `create_app(run_dir)` loads and validates the run once so
an invalid directory fails before the server binds a port. Chose server-rendered + query-param
filtering over a React SPA / HTMX bundle to keep the offline, no-external-assets guarantee trivially
true (per BUILD_BRIEF Section 7's endorsement of the simpler stack).

**Files created/changed:** `api/__init__.py`, `api/run_view.py` (`RunView` immutable loader +
`filter_findings`/`get_finding`/`rule_ids`/`severities`), `api/app.py` (`create_app` + JSON API:
`/api/health`, `/api/summary`, `/api/manifest`, `/api/findings` with severity/rule filters,
`/api/findings/{fingerprint}`); `cli.py` (`serve --run-dir --host --port`, localhost by default,
uvicorn); `pyproject.toml` (fastapi + uvicorn runtime, httpx dev, TestClient warning filter);
`docs/adr/ADR-007-web-viewer.md`. Tests: `tests/integration/test_viewer_api.py`.

**Commands run and results:**

```bash
uv add fastapi uvicorn ; uv add --dev httpx
uv run ruff check . ; uv run ruff format --check . ; uv run mypy src   # clean (49 source files)
uv run pytest -q                                                       # 206 passed
```

**Iteration 1 (accuracy on AI-generated data):** the test builds a *genuine* run directory by
running `collection-ci scan` on an AI-generated Met dataset, then exercises every endpoint via
FastAPI's TestClient. The API faithfully mirrors the engine: health reports 12 findings; `/api/findings`
returns all 12 most-severe-first; filtering by `severity=critical` returns exactly the 3 CORE001
duplicates; filtering by `rule=DATE001...` returns exactly its 3; an unknown filter returns 0; the
detail endpoint round-trips a fingerprint and 404s on an unknown one; the summary/manifest surface
the offline `network_access_used=false` / no-AI provenance. Loader rejects a missing directory and a
missing findings.json; the `serve` command exits 2 on an invalid run dir.

**Iteration 2 (VL-06 mutation):** mutation loop on `run_view.py` + `app.py` (8 mutations: severity
filter inverted, rule filter inverted, get_finding ignores fingerprint, findings sorted least-severe
first, total_findings hardcoded 0, findings.json not required, endpoint ignores filters, detail never
404s). **8/8 killed on the first pass, zero survivors.**

Slice S validation approved (API accuracy on AI data + VL-06).

**Next slice:** Slice T — the server-rendered accessible UI (dashboard, filterable findings table,
finding detail with the evidence chain), self-contained assets, XSS-safe, linking to the standalone
report.html.

---

## 2026-07-21 — Loop 30: Phase 5 Slice T — server-rendered accessible viewer UI

**Slice:** The HTML viewer on top of Slice S's API — a dashboard, a filterable findings table, and a
finding-detail page with the evidence chain, plus a route serving the standalone report.html.

**Files created/changed:** `api/views.py` (`register_views`: `/` dashboard, `/findings` with
severity/rule query-param filters, `/findings/{fingerprint}` detail, `/report`); `api/templates/`
(`base.html` with inline self-contained CSS — theme-aware light/dark, severity as text label + color
for accessibility; `dashboard.html`, `findings.html`, `detail.html`); `api/app.py` (registers the
views); `docs/FUTURE_SCOPE.md` (new, Section 6 deliverable referenced by ADR 007). Tests:
`tests/integration/test_viewer_ui.py`.

**Commands run and results:**

```bash
uv run ruff check . ; uv run ruff format --check . ; uv run mypy src   # clean (50 source files)
uv run pytest -q                                                       # 214 passed
uv build && (check wheel)                                              # templates ship in the wheel
collection-ci serve --run-dir <run> --port 8137                        # real uvicorn server:
  curl /api/health -> total_findings 12 ; GET / and /findings?severity=critical -> HTTP 200
```

**Iteration 1 (UI correctness + safety on AI data):** rendered against a genuine scan run from
AI-generated Met data — the dashboard shows the real severity counts (critical card = 3) and links
each rule into its filtered view; the findings table lists all 12 with one severity chip per row;
filtering to DATE001 narrows to exactly 3 rows with no CORE001 content leaking; the detail page shows
the evidence chain, recommendation, and fingerprint and 404s on an unknown one; pages are
self-contained (asserted no `src="http"`/`href="http"`/`@import`/`cdn`) and accessible (`lang`, skip
link, `id="main"`, `scope="col"` headers); a crafted `<script>` finding summary renders **escaped**
(`&lt;script&gt;`), never live. The `/report` route serves report.html and 404s when it is absent.
Also verified the real `collection-ci serve` process answers over HTTP (TestClient alone does not
exercise uvicorn).

**Iteration 2 (VL-06 mutation):** mutation loop on `views.py` (5 mutations: filters ignored, "total"
shows filtered count, detail never 404s, report never 404s, dashboard severity counts blanked).
**5/5 killed on the first pass, zero survivors.**

Slice T validation approved (UI correctness + XSS-safety + accessibility + real-server smoke, and
VL-06).

---

## 2026-07-21 — Phase 5 complete

Both Phase 5 slices done, each with two validated iterations (accuracy on AI-generated data via
TestClient + VL-06 mutation):

- Slice S: viewer API foundation — `serve` command, read-only `RunView` loader, JSON API
- Slice T: server-rendered accessible UI — dashboard, filterable findings, detail, report route

**Phase 5 checklist (BUILD_BRIEF.md Section 24 + Section 7):** local FastAPI web viewer (done,
server-rendered per the brief's simpler-stack option), read-only and offline (done), polished +
accessible + self-contained (done), `collection-ci serve` (done), ADR 007 recording the architecture
(done), `docs/FUTURE_SCOPE.md` (done). Gate honored: built only after the engine/reports/benchmark/
tests were stable.

**Aggregate:** 214 tests passing, ruff + mypy clean, wheel builds with templates included. The viewer
adds `fastapi`/`uvicorn` (runtime) + `httpx` (dev); the offline core still makes no network calls and
the viewer is read-only. Commits c57e449..(this loop), none pushed (no git remote).

**Next (Phase 6+):** the optional, opt-in, disabled-by-default ArtiFact/probabilistic experiment
(Phase 6), then the approval-gated GitHub Pages showcase (Phase 7). Remaining validation loops: VL-04
(broaden adversarial fixtures), VL-05 (Hypothesis fuzz), VL-07 (coverage ratchet in CI), VL-08
(README quick start executes), VL-10 (final Definition-of-Done pass).

---

## 2026-07-21 — Loop: VL-07 coverage ratchet wired

**Slice:** Wire coverage.py with an enforced floor into CI (VL-07), the first of the
endgame validation loops on the road to Definition-of-Done and the Phase 7 showcase. Phase 6
(optional probabilistic experiment) is being skipped as off the critical path for the showcase goal.

**Commands run:**
- `uv add --group dev 'pytest-cov>=5.0'` — added `pytest-cov` (+ `coverage`) to the dev group.
- `uv run pytest --cov=collection_integrity --cov-report=term-missing -q` — baseline: **1949
  statements, 64 missed, 96.72% total** (214 tests passing).
- `uv run pytest -q --cov-fail-under=99` → exit **1** (`FAIL Required test coverage of 99% not
  reached`); `uv run pytest -q` → exit **0** (`Required test coverage of 95.0% reached`). Confirms
  the ratchet both passes at baseline and *bites* below the floor.
- `uv run ruff check .` / `ruff format --check .` / `mypy src` — all clean.

**Changes:**
- `pyproject.toml`: `addopts` runs coverage on every `pytest`; `[tool.coverage.report] fail_under =
  95` sets the ratchet floor (baseline 96.72%, 95% leaves a small margin; the floor only ever rises).
- `.github/workflows/ci.yml`: Tests step now enforces coverage and uploads `coverage.xml` as an
  artifact.
- `.gitignore`: added `coverage.xml`.
- `docs/BACKLOG.md`: marked the VL-07 item done.

**VL-07 status:** evidence artifacts in place (coverage step in `ci.yml`, `fail_under` in
`pyproject.toml`). The ratchet is an ongoing automation, not a finish-line goal.

**Next:** VL-05 (Hypothesis fuzz / exit-code contract, `tests/property/`), then VL-04 (adversarial
fixtures + `docs/THREAT_MODEL.md`), VL-08 (README-executes), and finally VL-10 (DoD closure), which
opens the Phase 7 gate.

---

## 2026-07-21 — Loop: VL-05 fuzz/property contract for `scan`

**Slice:** Bring VL-05 online — a Hypothesis fuzz suite (`tests/property/test_scan_contract_fuzz.py`)
that feeds arbitrary bytes and adversarial CSV text to `scan --objects-csv` and asserts the CLI's
documented exit-code contract (BUILD_BRIEF.md Section 13: exit in {0,1,2,3}, never an unhandled
traceback). Second of the endgame validation loops.

**Iteration 1 (found a real bug):** `uv run pytest tests/property/test_scan_contract_fuzz.py` —
Hypothesis shrank to `b'\xff\xfe\x00bad'`: the CSV readers open with `encoding="utf-8"` and decode
lazily while iterating, so undecodable bytes raised an unhandled **`UnicodeDecodeError`** (Click
reported exit 1 with a traceback) instead of a clean exit 2. The NUL-byte case (`accession_number\n\x00\n`)
was already handled cleanly. Two paths were vulnerable: `ingestion/readers.py::read_csv_rows` and
`ingestion/csv_adapter.py::load_objects_from_csv` (the `--objects-csv` path).

**Fix:** wrapped both readers' decode+parse in `try/except (UnicodeDecodeError, csv.Error)` →
`IngestionError` / `CsvIngestionError`, which the `scan` command already maps to exit 2. Added three
named regression tests distilled from counterexamples (invalid UTF-8, NUL byte, empty file).

**Iteration 2 (clean):** re-ran the suite — 5 passed. Re-ran with `--hypothesis-seed=random` (fresh
exploration, 100 examples/property) — 5 passed. Two independent clean iterations after the fix.

**Broader checks:** full suite **219 passed** (+5), coverage **96.48%** (ratchet satisfied), ruff +
ruff format + mypy all clean.

**Evidence artifacts:** `tests/property/test_scan_contract_fuzz.py` (properties + regression tests),
fix in `ingestion/readers.py` and `ingestion/csv_adapter.py`. Budget bounded at `max_examples=100`
per property so CI cost stays fixed (VL-05 done condition).

**Next:** VL-04 (adversarial fixtures + `docs/THREAT_MODEL.md` per Section 18 item), then VL-08
(README-executes), then VL-10 (DoD closure → Phase 7 gate).

---

## 2026-07-21 — Loop: VL-04 threat-model adversarial coverage

**Slice:** Create `docs/THREAT_MODEL.md` and drive VL-04 to full coverage — every BUILD_BRIEF.md
Section 18 item mapped to either an adversarial fixture + passing test or a documented rationale for
non-applicability. Third of the endgame validation loops.

**Two real hardening fixes found while building the fixtures:**
- **Item 1 (formula injection):** `findings.csv` echoed source-controlled values (entity ids,
  summaries, evidence) straight into cells, so a source cell like `=cmd|'/c calc'!A1` would execute
  when the CSV is opened in Excel/Sheets. Added `reporting/csv_report.py::_neutralize` (OWASP
  guidance: prefix cells leading with `= + - @ TAB CR` with an apostrophe).
- **Item 5 (decompression bomb):** `engine/media_files.py` caught `UnidentifiedImageError/OSError/
  ValueError` but not Pillow's `DecompressionBombError` (it subclasses `Exception`), so a crafted
  image would crash the reader. Added it to the caught tuple.

**Iteration 1:** wrote `tests/integration/test_adversarial.py` (11 tests) + fixtures. First run
surfaced three test-design issues (not product bugs): the 300 KB DoS cell was *correctly* rejected
by the new csv field-size guard (exit 2, not a crash); a Windows `..\..\` case isn't traversal on
POSIX; the formula-injection assertion needed the duplicated accession itself to be the formula so
it reaches a top-level cell. Corrected the tests/fixture accordingly.

**Iteration 2 (validation approved):** all 11 adversarial tests pass. VL-06 mutation check on the two
fixes — (a) neutralizer reduced to identity → `test_formula_injection_...` **fails**; (b) dropped
`DecompressionBombError` from the catch → `test_decompression_bomb_image_handled` **fails** with the
uncaught error. Both mutants killed; fixes reverted.

**Coverage documented:** `docs/THREAT_MODEL.md` table — items 1,2,3,4,5,7,9,10,11,12 mitigated with
tests; 13 documented non-goal; 6,8,14 not-applicable-by-feature-set with revisit conditions; 15
partially mitigated (pinned lockfile; pip-audit CI step remains backlogged).

**Broader checks:** full suite **230 passed** (+11), coverage **96.54%**, ruff + format + mypy clean.

**Next:** VL-08 (README-executes), then VL-10 (DoD closure → Phase 7 gate).

---

## 2026-07-21 — Loop: VL-08 README-executes

**Slice:** Make the README's quick start true and executable, and delete the "target, not yet fully
implemented" caveat (VL-08 done condition). Fourth of the endgame validation loops.

**Iteration 1 (found the README wrong):** running the old quick start verbatim failed —
`collection-ci scan --mapping examples/mappings/clean.yaml --rules rulesets/core.yaml` errored with
`No such option: --rules` (exit 2), and `rulesets/core.yaml` does not exist. The README, not the
code, was wrong (stale from Phase 1). Rewrote it around the real, working commands and updated the
status line from "early Phase 1" to "Phases 0–5 complete."

Verbatim execution of the new quick start from a clean `build/`:
- `uv sync` → OK
- clean scan (`examples/mappings/clean.yaml`) → **exit 0**, 250 records, "No findings"
- dirty scan (`examples/mappings/dirty.yaml`) → **exit 1**, 20 findings, full report set written
- `serve --run-dir build/scan-dirty` → HTTP **200**, `<title>Dashboard — Collection Integrity CI</title>`
- `benchmark` → **exit 0**, meets precision/recall target (P=R=1.0)

All six report artifacts present in the scan output dir; exit codes match the documented contract.

**Iteration 2 (validation approved — fresh clone):** cloned the committed HEAD into a temp dir and
ran the quick start copy-paste (see the fresh-clone transcript below in this entry). Everything
executed with the documented outcomes from a checkout that had never been built before — the honest
"new user" test.

**Next:** VL-10 (Definition-of-Done closure), which walks BUILD_BRIEF.md Section 25 top-to-bottom and
opens the Phase 7 gate.

---

## 2026-07-21 — Loop: VL-10 Definition-of-Done closure (Phase 7 gate OPEN)

**Slice:** Execute BUILD_BRIEF.md Section 25 top-to-bottom rather than asserting it — the release
gate and the precondition for the Phase 7 showcase. Captured as a reusable, committed runner
`scripts/check_dod.sh`. Fifth and final of the endgame validation loops.

**Iteration 1 (fresh clone @ 202d71b):** all 18 checks PASSED in one uninterrupted run —
uv sync / ruff / format / mypy / pytest (coverage ratchet) / wheel build / clean scan (exit 0, 0
findings) / dirty scan (exit 1; CORE001, CORE002, DATE001, SCHEMA001) / benchmark (meets target) /
HTML self-contained / SARIF 2.1.0 structure / secret-free workflows / README matches CLI /
manifest offline flags (no AI, no network) / source data unmodified / limitations documented /
progress+threat docs present / demo baseline `--only-new` (0 new, exit 0).

**Iteration 2 (validation approved):** re-ran from a second fresh clone — **ALL CHECKS PASSED**
again, confirming the DoD is reproducible and deterministic, not a one-off.

**Result:** the Definition of Done is met. The Phase 7 gate ("only begin after DoD passes") is now
open. Publishing remains approval-gated — the showcase site will be built and verified locally
(`mkdocs build`) only, with no push/Pages-enable until explicit user approval.

**Endgame validation status:** VL-04 ✅, VL-05 ✅, VL-07 ✅, VL-08 ✅, VL-10 ✅.

**Next:** Phase 7 — build the MkDocs Material dual-story showcase (product home, "How this was
built" loop-engineering case study, "About the builder"), add the gh-pages workflow (no secrets),
verify `mkdocs build` locally, then stop for approval to publish.

---

## 2026-07-21 — Loop: Phase 7 dual-story showcase (built locally; publish approval-gated)

**Slice:** With the Definition of Done met (VL-10), build the Phase 7 MkDocs Material showcase —
product home, "How this was built" loop-engineering case study, and "About the builder" — plus the
GitHub Pages deploy workflow and a README pointer. Built and verified **locally only**; no push, no
Pages enablement (both remain gated on explicit user approval per BUILD_BRIEF.md Phase 7 and the
CLAUDE.md safety constraints).

**Built:**
- `mkdocs.yml` (Material theme, `docs_dir: site_src`, `font: false` to stay consistent with the
  product's no-external-assets ethos, Mermaid via superfences, light/dark toggle, no analytics/no
  secrets).
- `site_src/index.md` (product story + real dirty-scan console excerpt + benchmark table +
  Mermaid architecture diagram + honest limitations).
- `site_src/how-built.md` (the loop-engineering case study, with three *real* loop wins: the VL-05
  UTF-8 fuzz crash, the VL-04 CSV formula-injection vector, and VL-06 mutation verification).
- `site_src/about.md` (technical-PM positioning grounded in PRD authorship, non-goals, measured
  success, and threat-model thinking).
- `.github/workflows/pages.yml` (build `mkdocs build --strict` → `upload-pages-artifact` →
  `deploy-pages`; scoped `GITHUB_TOKEN` permissions, **no secrets**).
- README pointer to the showcase + the Claude Code loop-engineering note.

**Every number on the site is sourced from generated data, and a test enforces it:**
`tests/integration/test_showcase_accuracy.py` re-derives each quantitative claim (15 rules; 5 scored
benchmark rules on 60 objects with 20 injected errors at F1 = 1.00; the 250-record / 20-finding
dirty scan; 40+ loop entries; 10 validation loops; 18 DoD checks) from live code and fresh
`benchmark`/`scan` runs, so the showcase cannot drift from the truth.

**Iteration 1 (build):** `mkdocs build --strict` → exit 0, zero link/nav warnings; `site/` built
with `index.html`, `how-built/`, `about/`, `404.html`. Mermaid diagram present (`class="mermaid"`).

**Iteration 2 (validation approved):** `test_showcase_accuracy.py` passes against freshly generated
data; strict build re-run clean; full suite + lint/format/mypy green.

**Next:** stop for explicit user approval before any push / GitHub Pages enablement (Phase 7
publishing step).

---

## 2026-07-22 — Loop: Phase 7 published to GitHub Pages (approved)

**Slice:** With explicit user approval, publish the project and the Phase 7 showcase.

**What happened:**
- Created public repo `github.com/akivanc88/collection-integrity-ci`; `main` is the default branch.
- Established `main` at the Phase-5 base (`cf686a9`), then landed each of the six endgame/Phase-7
  slices as its **own PR** (#1 VL-07, #2 VL-05, #3 VL-04, #4 VL-08, #5 VL-10, #6 Phase 7), merged in
  order. Verified remote `main`'s tree is byte-identical to the validated local build.
- CI is **green** on merged `main` (`uv sync --locked`, lint, format, mypy, 234 tests + coverage
  ratchet, build, sample scan, benchmark).
- Enabled GitHub Pages (Actions source) and deployed via `.github/workflows/pages.yml` — build
  (`mkdocs build --strict`) and deploy jobs both succeeded.
- **Live and verified:** https://akivanc88.github.io/collection-integrity-ci/ (home, `/how-built/`,
  `/about/`) all return HTTP 200.

This PR wires the live URL into the README, adds `site_url`/`repo_url` to `mkdocs.yml`, and records
the publish. The approval-gated Phase 7 publishing step is now complete.
