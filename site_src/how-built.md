# How this was built

Collection Integrity CI is also a **case study in loop-engineering** — building software with an AI
coding agent ([Claude Code](https://claude.com/claude-code)) under a disciplined, evidence-first
working method rather than ad-hoc prompting. This page connects that method to concrete artifacts in
the repository, so nothing here is a claim you have to take on faith.

## The working method

Every change followed the same loop:

> **inspect state → pick the smallest vertical slice → implement → run focused tests → run broader
> checks → inspect real output → update the progress log → commit.**

One reviewable slice per commit. No feature is ever called "done" without a command or test having
been run and its output inspected. The build log records **40+ such loop iterations** to date, each
with the commands run and their results.

!!! quote "From the project's own guardrails (`CLAUDE.md`)"
    *"Never claim a feature works without having run the relevant command/test and inspected the
    output. Never weaken or delete a test to make a build pass. Diagnose failures instead."*

## Validation has its own loops

Beyond ordinary tests, the project defines ten **validation loops** (`docs/VALIDATION_LOOPS.md`),
each with a machine-checkable done-condition. They exist to keep the build honest as it grows:

| Loop | What it guarantees | How |
|------|--------------------|-----|
| VL-02 | Finding identity is stable | Fingerprints identical across runs and input orderings |
| VL-04 | Robustness to hostile input | Adversarial fixtures for every threat-model item |
| VL-05 | The CLI never crashes | Hypothesis fuzzing against the exit-code contract |
| VL-06 | The *tests themselves* are strong | Mutation testing — inject a defect, a test must fail |
| VL-07 | Coverage never erodes | A ratchet in CI that only ever rises |
| VL-08 | The docs don't lie | Every README command executed verbatim |
| VL-10 | Release readiness | The Definition of Done, executed top-to-bottom |

## The loops earn their keep — three real examples

These are not hypothetical. Each was a bug or gap the loops caught, with a commit that fixed it.

### A fuzzer found a crash the tests missed (VL-05)

Hypothesis fed arbitrary bytes to the `scan` command and shrank a failing case to
`b'\xff\xfe\x00bad'`: undecodable input raised an **unhandled `UnicodeDecodeError`** instead of the
documented "invalid input" exit code. The fix translated decode/parse errors into a clean error at
the ingestion boundary, and the shrunk counterexample became a permanent regression test.

### Building an attack fixture exposed a spreadsheet-injection vector (VL-04)

While writing threat-model fixtures, the CSV report writer was found to echo source-controlled
values straight into cells — so a malicious cell like `=cmd|'/c calc'!A1` would **execute when
`findings.csv` was opened in Excel.** The fix neutralizes formula-leading cells per OWASP guidance;
a test asserts no output cell can begin with a formula trigger.

### Mutation testing proved the new tests actually bite (VL-06)

After each fix, the defect was deliberately re-introduced to confirm the new test *fails* — proving
the test earns its place rather than passing vacuously. Both the fuzzing and injection fixes were
verified this way before being committed.

## The Definition of Done, executed not asserted

The release gate (`docs/PROGRESS.md`, VL-10) is a script — `scripts/check_dod.sh` — that walks all
eighteen checks from the build specification **in a fresh clone**: sync, lint, format, types, tests
with the coverage ratchet, a wheel build, a clean scan, a dirty scan, the benchmark meeting its
precision/recall target, a self-contained HTML report, SARIF validation, secret-free CI workflows,
the README quick start, offline-manifest flags, source data left unmodified, and the demo script.
It passed all eighteen across two independent fresh-clone runs before this site was built.

## The evidence trail

Everything above is traceable in the repository:

- **`docs/PROGRESS.md`** — the append-only loop log (40+ iterations, each with commands + results).
- **`docs/VALIDATION_LOOPS.md`** — the ten loops and their live status.
- **`docs/THREAT_MODEL.md`** — every threat-model item mapped to a test or a documented rationale.
- **`docs/adr/ADR-007-web-viewer.md`** — an architecture decision record for the web viewer.
- **`scripts/check_dod.sh`** — the executable Definition of Done.
- **The git history** — one vertical slice per commit.

The point of loop-engineering is that *the process leaves receipts.* This page is just an index to
them.
