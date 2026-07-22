# How this was built

This project was also an experiment in building software with an AI coding agent
([Claude Code](https://claude.com/claude-code)) under a disciplined working method, rather than
ad-hoc prompting. This page ties that method to actual artifacts in the repository, so none of it
has to be taken on faith.

## The working method

Every change went through the same loop:

> look at the current state, pick the smallest useful slice, implement it, run the focused tests,
> run the broader checks, look at the real output, update the progress log, then commit.

One reviewable slice per commit. Nothing was called done until a command or test had been run and its
output looked at. The build log records more than 40 of these loop iterations, each with the commands
that ran and what came back.

!!! quote "From the project's own guardrails (`CLAUDE.md`)"
    "Never claim a feature works without having run the relevant command/test and inspected the
    output. Never weaken or delete a test to make a build pass. Diagnose failures instead."

## Validation has its own loops

On top of the ordinary tests, the project defines ten validation loops
(`docs/VALIDATION_LOOPS.md`), each with a done-condition a machine can check. They exist to keep the
build honest as it grows:

| Loop | What it guarantees | How |
|------|--------------------|-----|
| VL-02 | Finding identity is stable | Fingerprints stay identical across runs and input orderings |
| VL-04 | Robustness to hostile input | Adversarial fixtures for every threat-model item |
| VL-05 | The CLI never crashes | Hypothesis fuzzing against the exit-code contract |
| VL-06 | The tests themselves are strong | Mutation testing: introduce a defect, a test has to fail |
| VL-07 | Coverage doesn't erode | A ratchet in CI that only moves up |
| VL-08 | The docs don't lie | Every README command run word for word |
| VL-10 | Release readiness | The Definition of Done, run top to bottom |

## Three times the loops caught something

None of these are hypothetical. Each was a real bug or gap, with a commit that fixed it.

**A fuzzer found a crash the tests missed (VL-05).** Hypothesis fed arbitrary bytes to the `scan`
command and shrank a failing case down to `b'\xff\xfe\x00bad'`. Undecodable input was raising an
unhandled `UnicodeDecodeError` instead of the documented "invalid input" exit code. The fix moved
error handling to the ingestion boundary, and the shrunk counterexample became a permanent
regression test.

**Building an attack fixture exposed a spreadsheet-injection hole (VL-04).** While writing
threat-model fixtures, the CSV report writer turned out to echo source values straight into cells, so
a cell like `=cmd|'/c calc'!A1` would run when someone opened `findings.csv` in Excel. The fix
neutralizes formula-leading cells, and a test checks that no output cell can start with a formula
trigger.

**Mutation testing proved the new tests actually work (VL-06).** After each fix, the defect was put
back on purpose to confirm the new test fails. Both the fuzzing and injection fixes were checked this
way before they were committed.

## The Definition of Done is run, not asserted

The release gate is a script, `scripts/check_dod.sh`, that walks all eighteen checks from the build
specification against a fresh clone: sync, lint, format, types, tests with the coverage ratchet, a
wheel build, a clean scan, a dirty scan, the benchmark hitting its target, a self-contained HTML
report, SARIF validation, secret-free CI workflows, the README quick start, the offline-manifest
flags, source data left untouched, and the demo script. It passed all of them across two separate
fresh-clone runs before this site was built.

## Where to find the evidence

- `docs/PROGRESS.md` is the append-only loop log, one entry per iteration with commands and results.
- `docs/VALIDATION_LOOPS.md` lists the ten loops and their current status.
- `docs/THREAT_MODEL.md` maps every threat-model item to a test or a written rationale.
- `docs/adr/ADR-007-web-viewer.md` is the architecture decision record for the web viewer.
- `scripts/check_dod.sh` is the executable Definition of Done.
- The git history is one vertical slice per commit.

A documented working method like this leaves a trail. This page is really just an index to it.
