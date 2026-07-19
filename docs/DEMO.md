# Five-minute demo

A reproducible walkthrough of Collection Integrity CI. Every command runs offline with no API keys.
Run from the repo root after `uv sync`.

The example datasets are generated deterministically by `examples/generate.py` (250 synthetic
objects). The dirty set has 20 labeled injected errors across four rules — see
`examples/expected/dirty_expected.json`.

## 1. Scan the clean dataset — expect no findings

```bash
uv run collection-ci scan --mapping examples/mappings/clean.yaml --output-dir build/clean
```

Exit code 0, `build/clean/summary.json` reports `total_findings: 0`.

## 2. Scan the dirty dataset — expect the injected findings

```bash
uv run collection-ci scan --mapping examples/mappings/dirty.yaml --output-dir build/dirty
```

Exit code 1 (findings reached the failure threshold). `build/dirty/summary.json` shows five each of
`CORE001_DUPLICATE_ACCESSION_NUMBER`, `CORE002_REQUIRED_FIELD_MISSING`, `DATE001_INVERTED_DATE_RANGE`,
and `SCHEMA001_INVALID_FIELD_TYPE`.

## 3. Open the HTML report

```bash
open build/dirty/report.html    # or: xdg-open build/dirty/report.html
```

A standalone page (no network needed): severity distribution, a severity-filterable findings table
with expandable evidence and remediation, input provenance, and a disclaimer that the checks are
policy consistency, not legal advice.

## 4. Inspect a finding

Open `build/dirty/findings.json` and pick a `CORE001` finding: it names the duplicated accession
number, both offending objects, the source rows, a remediation, and a stable `fingerprint`.

## 5. Baseline and `--only-new`

```bash
cp build/dirty/findings.json build/baseline.json
uv run collection-ci scan --mapping examples/mappings/dirty.yaml --output-dir build/rescan \
  --baseline build/baseline.json --only-new
```

Reports `0 new, 20 unchanged, 0 resolved` and exits 0 — a CI gate configured with `--only-new`
passes because there are no new regressions, even though the known issues remain in the full report.

## 6. SARIF for GitHub code scanning

`build/dirty/results.sarif` is valid SARIF 2.1.0. In CI, upload it with
`github/codeql-action/upload-sarif` to annotate the offending source files on a pull request.

## 7. Run the benchmark

```bash
uv run collection-ci benchmark --output-dir build/benchmark
```

Generates a labeled synthetic dataset, scans it, and reports precision, recall, and F1 per rule.
On the default seed every benchmarked rule scores 1.0 and the command exits 0.
