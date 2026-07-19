# Validation Loops

This project is built and validated with explicit, self-verifying loops. Each loop below is a
narrow goal with a machine-checkable **done condition**: the loop can verify itself from evidence
(test output, diffs, metrics), without a human judging the result. This file is the specification
for those loops; execution evidence lands in `docs/PROGRESS.md` and, where noted, in CI.

Format for every loop:

- **Validates** — the part of the system under test
- **Available** — the earliest phase (see `BUILD_BRIEF.md` Section 24) at which the loop can run
- **Loop body** — the repeated steps
- **Done condition** — the objective check that terminates the loop
- **Evidence artifact** — where proof of the outcome lives
- **Mechanics** — how the loop is driven (interactive session goal vs. recurring automation)

Status legend: `active` (runs now), `partial` (a narrower version runs now), `pending` (blocked
on a later phase's features).

| ID | Loop | Validates | Status |
| --- | --- | --- | --- |
| VL-01 | Benchmark closure | Rule-engine correctness | partial (CORE001/CORE002/REF001 at P=R=1.0) |
| VL-02 | Fingerprint determinism | Finding identity/baselines | active (all rules, incl. shuffled input) |
| VL-03 | Baseline round-trip | Regression behavior | pending (Phase 3) |
| VL-04 | Threat-model adversarial | Robustness to hostile input | pending (Phase 2–3) |
| VL-05 | Fuzz/property contract | Crash-freedom, exit-code contract | pending (Phase 2) |
| VL-06 | Test-strength (mutation) | The test suite itself | active (found+closed 3 real gaps to date) |
| VL-07 | Coverage ratchet | Test breadth over time | pending (CI wiring) |
| VL-08 | README-executes | Honest documentation | partial |
| VL-09 | Progress audit | Recorded claims vs. reality | active |
| VL-10 | Definition-of-Done closure | Release readiness | pending (endgame) |

---

## Correctness loops

### VL-01: Benchmark closure

- **Validates:** that every deterministic rule detects exactly what it claims to detect, and
  nothing else.
- **Available:** Phase 3 (needs the error injector and labeled manifest from
  `BUILD_BRIEF.md` Section 16).
- **Loop body:**
  1. Inject errors into a copy of the clean fixture with a fixed seed
     (`collection-ci inject-errors --seed 42`).
  2. Scan the injected dataset.
  3. Compare findings against the injection manifest, per rule.
  4. For every missed injection or false positive: fix the rule implementation. Never edit the
     label to match the output — unless the label is proven wrong, in which case document why in
     `docs/BENCHMARK.md` before changing it.
  5. Re-run from step 1.
- **Done condition:** precision = 1.0 and recall = 1.0 on the injected set, **and** zero findings
  on the clean golden dataset (excluding explicitly documented warnings).
- **Evidence artifact:** `benchmarks/reports/latest/` metrics output, summarized in
  `docs/BENCHMARK.md` and the relevant `docs/PROGRESS.md` entry.
- **Mechanics:** interactive session goal per new rule; the full benchmark also runs as a CI step
  once `collection-ci benchmark` exists.

### VL-02: Fingerprint determinism

- **Validates:** that finding fingerprints are stable across identical runs and insensitive to
  input row order — the property baselines and deduplication depend on.
- **Available:** now (partial: a stability test for CORE001 exists in
  `tests/unit/test_core_rules.py::test_fingerprint_is_stable_across_runs`).
- **Loop body:**
  1. Scan a fixture; record the fingerprint set.
  2. Scan again unchanged; scan again with input rows shuffled.
  3. Diff the three fingerprint sets.
  4. If any fingerprint differs, fix `compute_fingerprint` inputs (never sort-order-dependent or
     timestamp-dependent values) and re-run.
- **Done condition:** fingerprint sets are identical across all three runs for **every**
  implemented rule; only `finding_id` and timestamps may differ.
- **Evidence artifact:** parametrized test over the rule registry (one case per rule), green in
  CI.
- **Scaling rule:** when a new rule is added, this loop fails until the new rule has its
  determinism case — that is the mechanism that keeps the loop honest as the rule set grows.
- **Mechanics:** enforced continuously in the test suite; revisited explicitly whenever a rule's
  evidence shape changes.

### VL-03: Baseline round-trip

- **Validates:** the new / unchanged / resolved classification and `--only-new` threshold
  behavior (`BUILD_BRIEF.md` Section 15).
- **Available:** Phase 3 (needs `--baseline` and `--only-new`).
- **Loop body:**
  1. Scan the dirty fixture; save the findings as a baseline.
  2. Re-scan the same input with `--baseline` and `--only-new`; expect zero new findings and
     exit 0.
  3. Inject exactly one fresh error; re-scan; expect exactly one new finding and a threshold
     exit code.
  4. Remove one pre-existing error from the input; re-scan; expect exactly one finding classified
     as resolved.
  5. Any deviation: fix the baseline matcher, not the expectations.
- **Done condition:** all three assertions (zero-new, one-new, one-resolved) hold for every rule
  that has an injector.
- **Evidence artifact:** end-to-end test in `tests/e2e/`, green in CI.
- **Mechanics:** interactive session goal when baselines are implemented; regression-guarded by
  the e2e test afterward.

## Robustness loops

### VL-04: Threat-model adversarial

- **Validates:** that hostile or pathological input fails cleanly — a controlled error (exit 2)
  or a finding, never a crash, never execution of source content, never a path escape.
- **Available:** items 1–4 and 10–12 of `BUILD_BRIEF.md` Section 18 from Phase 2; image-related
  items (5, and media rules generally) from Phase 3 when Pillow-based checks land.
- **Loop body:**
  1. Take the next unaddressed item from the Section 18 threat list.
  2. Build a minimal adversarial fixture for it (formula-injection cell, `../../` media path,
     symlinked input, multi-megabyte single cell, decompression-bomb image, script tag in a
     title, ...).
  3. Run a scan against the fixture and observe behavior.
  4. If behavior is unsafe or a crash: fix, add a permanent test, re-run.
  5. Record the item as covered in `docs/THREAT_MODEL.md` with a pointer to its fixture and test.
- **Done condition:** every item in Section 18 has (a) an adversarial fixture, (b) a passing
  test, and (c) an entry in `docs/THREAT_MODEL.md` — or a documented rationale for why it is not
  applicable to the current feature set.
- **Evidence artifact:** `tests/fixtures/adversarial/` + `docs/THREAT_MODEL.md` coverage table.
- **Mechanics:** interactive session goal, one threat item per iteration; fixtures stay in the
  suite permanently.

### VL-05: Fuzz/property contract

- **Validates:** the CLI's external contract under arbitrary input: no unhandled exceptions, and
  exit codes always match the documented semantics (0/1/2/3, `BUILD_BRIEF.md` Section 13).
- **Available:** Phase 2 (meaningful once the mapping layer accepts varied schemas; Hypothesis is
  already mandated by the brief's quality stack).
- **Loop body:**
  1. Hypothesis generates arbitrary CSV content (random headers, encodings, quoting, empty
     files, giant cells).
  2. Invoke `scan` on each generated input.
  3. Any unhandled traceback or undocumented exit code is a failure: fix the ingestion/CLI error
     handling, add the shrunken counterexample as a permanent regression test, re-run.
- **Done condition:** a fixed fuzzing budget (e.g., 10 minutes or N examples in CI) completes
  with zero contract violations.
- **Evidence artifact:** property tests in `tests/property/`, plus regression tests named after
  the counterexamples they came from.
- **Mechanics:** short budget on every CI run; longer budget as an occasional recurring
  automation.

## Quality-gate loops

### VL-06: Test-strength (mutation)

- **Validates:** the test suite itself — whether tests would actually catch a broken rule. This
  is the enforcement mechanism behind "never claim a feature works without evidence."
- **Available:** now.
- **Loop body:**
  1. For each rule, introduce one deliberate defect (flip a comparison, drop the non-empty
     filter, skip the last record) in a scratch working copy.
  2. Run the test suite; it must fail.
  3. If a mutant survives, a test gap exists: add the missing test (against the *unmutated*
     code), verify it now kills the mutant, revert the mutant.
- **Done condition:** zero surviving mutants across `src/collection_integrity/rules/` for the
  mutation set exercised.
- **Evidence artifact:** the added tests, plus a note of the mutation session's result in
  `docs/PROGRESS.md`. If this graduates to a tool (e.g., mutmut) rather than manual mutations,
  its report is the artifact.
- **Mechanics:** interactive session goal after each new rule lands; mutations are never
  committed.

### VL-07: Coverage ratchet

- **Validates:** that test breadth never silently erodes as code grows.
- **Available:** pending CI wiring (coverage.py is in the brief's stack but not yet configured —
  tracked in `docs/BACKLOG.md`).
- **Loop body:** each CI run measures coverage and compares against the committed threshold; a
  drop fails the build; the threshold is raised (never lowered) when coverage durably improves.
- **Done condition:** none — this is a ratchet, an ongoing automation with a monotonic invariant,
  not a goal with a finish line.
- **Evidence artifact:** coverage step in `.github/workflows/ci.yml` and the threshold value in
  `pyproject.toml`.
- **Mechanics:** pure automation; humans only touch it to raise the threshold.

## Consistency loops

### VL-08: README-executes

- **Validates:** that documentation makes no claim the software doesn't keep — every README
  command runs verbatim with the documented result.
- **Available:** now (partial: the README currently, deliberately, labels its quick start as
  "target, not yet fully implemented" — the loop's job is to make that caveat deletable).
- **Loop body:**
  1. From a clean checkout (fresh clone or `git stash`-clean tree), execute the README quick
     start exactly as written, copy-paste, no substitutions.
  2. On any divergence, fix whichever side is wrong — the code or the README.
  3. Re-run from a clean state.
- **Done condition:** every command in the README executes verbatim with the documented outcome,
  and the "not yet fully implemented" caveat has been removed because it is no longer true.
- **Evidence artifact:** the transcript recorded in `docs/PROGRESS.md`; `BUILD_BRIEF.md` Section
  25 makes this loop's done condition an explicit release requirement.
- **Mechanics:** interactive loop before any release-like milestone; candidates for a scripted CI
  smoke job once the quick start stabilizes.

### VL-09: Progress audit

- **Validates:** that `docs/PROGRESS.md` — the project's source of truth — records only
  reproducible facts.
- **Available:** now.
- **Loop body:**
  1. An auditor who did **not** write the entry (a second session, or a reviewer) takes the
     latest `docs/PROGRESS.md` entry.
  2. Re-runs every command listed in it, from the commit the entry describes.
  3. Compares actual output against recorded results.
  4. Any discrepancy gets a correcting follow-up entry (entries are append-only; history is
     never rewritten).
- **Done condition:** all recorded commands reproduce their recorded outcomes for the audited
  entry.
- **Evidence artifact:** an "audited" note appended to the entry, naming what was re-run and the
  result.
- **Mechanics:** separate audit pass after significant loops; the separation between author and
  auditor is the point — the writer of a claim never grades it.

### VL-10: Definition-of-Done closure

- **Validates:** release readiness — `BUILD_BRIEF.md` Section 25, executed rather than asserted.
- **Available:** endgame (after Phase 3 at the earliest; it will fail trivially before then).
- **Loop body:**
  1. Walk Section 25's checklist top to bottom, executing each bullet as a real check
     (`uv sync` from a clean checkout, lint, format, types, tests, build, clean scan, dirty
     scan, benchmark, HTML report offline-open, SARIF validation, README quick start, demo
     script, docs accuracy).
  2. Stop at the first failure; fix it; restart the checklist **from the top**.
- **Done condition:** the entire checklist passes in one uninterrupted run.
- **Evidence artifact:** the full transcript in `docs/PROGRESS.md`; this is the gate for calling
  the first release done and the precondition for the Phase 7 showcase.
- **Mechanics:** interactive session goal; restarting from the top after any fix is what makes
  the final pass trustworthy.

---

## Sequencing

- **Now (Phase 1–2):** VL-06 after each new rule; VL-02 scales with the rule registry; VL-09
  after significant loops.
- **Phase 2:** VL-05 comes online with the mapping layer; VL-04 begins with the non-image threat
  items.
- **Phase 3:** VL-01 (the flagship), VL-03, VL-08 in earnest, VL-04 image items, VL-07 wiring.
- **Endgame:** VL-10, exactly once, from the top, until it passes clean.
