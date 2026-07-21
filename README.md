# Collection Integrity CI

> GitHub Actions and data-quality CI for museum collection records.

A portable, local-first quality-assurance layer that checks whether collection object, media,
rights, location, and people records agree with one another before data is migrated, published,
imported, shared, or released. It does not replace a collection management system — it ingests
exports, runs transparent deterministic rules, and produces evidence-backed findings for a human
to resolve.

Full specification: [`BUILD_BRIEF.md`](./BUILD_BRIEF.md). Build status and what actually works
right now: [`docs/PROGRESS.md`](./docs/PROGRESS.md).

**Showcase site:** a dual-story MkDocs site (product overview + a "How this was built"
loop-engineering case study) lives in [`site_src/`](./site_src); build it locally with
`uv run --group docs mkdocs build`. It is published to GitHub Pages via
[`.github/workflows/pages.yml`](./.github/workflows/pages.yml) once Pages is enabled for the
repository. This project was built with [Claude Code](https://claude.com/claude-code) using a
documented loop-engineering working method (see the case study and `docs/PROGRESS.md`).

**Status: Phases 0–5 complete.** The deterministic engine (15 rules), the JSON/CSV/HTML/SARIF
report set, baselines, the benchmark, the Met/Cleveland/NGA source adapters, and the local web
viewer all work offline with no API keys. See [`docs/PROGRESS.md`](./docs/PROGRESS.md) for the
loop-by-loop build log.

## Quick start

Requires [`uv`](https://docs.astral.sh/uv/). Everything below runs offline — no network, no API
keys.

```bash
uv sync

# Scan a clean example export — passes every check, exits 0, writes the full report set.
uv run collection-ci scan --mapping examples/mappings/clean.yaml --output-dir build/scan

# Scan a deliberately dirty export — surfaces findings and exits 1 (the CI-failure signal).
uv run collection-ci scan --mapping examples/mappings/dirty.yaml --output-dir build/scan-dirty

# Open build/scan-dirty/report.html in a browser, or explore it in the local web viewer:
uv run collection-ci serve --run-dir build/scan-dirty   # http://127.0.0.1:8000

# Score rule precision/recall/F1 against the labeled synthetic benchmark.
uv run collection-ci benchmark --output-dir build/benchmark
```

Each `scan` writes `findings.json`, `findings.csv`, `report.html`, `results.sarif`,
`run_manifest.json`, and `summary.json` to the output directory. Exit codes: `0` (no failures),
`1` (failure threshold reached), `2` (invalid input/config), `3` (internal error).

## License

Apache-2.0. See `BUILD_BRIEF.md` Section 19 for the rationale (permissive, patent-grant clause
suitable for an open-source tool that institutions may adopt and extend).
