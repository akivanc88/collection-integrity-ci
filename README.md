# Collection Integrity CI

> Data-quality CI for museum collection records.

Museum records drift apart over time. Different people edit objects, media, rights, and location
data in different years, and the records stop agreeing with each other. Collection Integrity CI
reads an export and checks those records against a set of rules before the data gets migrated,
published, or shared. It doesn't replace a collection management system. It reads exports (never
writing back), runs deterministic checks, and hands a person a list of evidence-backed findings to
look at.

Full specification is in [`BUILD_BRIEF.md`](./BUILD_BRIEF.md). What actually works today is tracked
in [`docs/PROGRESS.md`](./docs/PROGRESS.md).

## Showcase site

https://akivanc88.github.io/collection-integrity-ci/

The site has a product overview, a page on how the project was built, and a page validating the tool
against real Met and Cleveland open data. Source is in [`site_src/`](./site_src); build it locally
with `uv run --group docs mkdocs build`, or read it live at the link above. It's published to GitHub
Pages by [`.github/workflows/pages.yml`](./.github/workflows/pages.yml). The project was built with
[Claude Code](https://claude.com/claude-code) using a documented working method (see
`docs/PROGRESS.md`).

## Status

Phases 0 through 5 are done. The rule engine (15 rules), the JSON/CSV/HTML/SARIF reports, baselines,
the benchmark, the Met/Cleveland/NGA adapters, and the local web viewer all run offline with no API
keys. `docs/PROGRESS.md` has the full build log.

## Quick start

You'll need [`uv`](https://docs.astral.sh/uv/). None of this touches the network or needs an API
key.

```bash
uv sync

# Scan a clean example export. It passes every check, exits 0, and writes the full report set.
uv run collection-ci scan --mapping examples/mappings/clean.yaml --output-dir build/scan

# Scan a dirty export. It reports findings and exits 1, which is the signal a CI job fails on.
uv run collection-ci scan --mapping examples/mappings/dirty.yaml --output-dir build/scan-dirty

# Open build/scan-dirty/report.html in a browser, or read it in the local web viewer:
uv run collection-ci serve --run-dir build/scan-dirty   # http://127.0.0.1:8000

# Score each rule's precision, recall, and F1 against the labeled synthetic benchmark.
uv run collection-ci benchmark --output-dir build/benchmark
```

Every `scan` writes `findings.json`, `findings.csv`, `report.html`, `results.sarif`,
`run_manifest.json`, and `summary.json` to the output directory. The exit codes are `0` (no
failures), `1` (failure threshold reached), `2` (invalid input or config), and `3` (internal error).

## License

Apache-2.0. `BUILD_BRIEF.md` Section 19 explains why: a permissive license with a patent-grant
clause that institutions can adopt and build on.
