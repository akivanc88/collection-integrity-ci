# Collection Integrity CI

> GitHub Actions and data-quality CI for museum collection records.

A portable, local-first quality-assurance layer that checks whether collection object, media,
rights, location, and people records agree with one another before data is migrated, published,
imported, shared, or released. It does not replace a collection management system — it ingests
exports, runs transparent deterministic rules, and produces evidence-backed findings for a human
to resolve.

Full specification: [`BUILD_BRIEF.md`](./BUILD_BRIEF.md). Build status and what actually works
right now: [`docs/PROGRESS.md`](./docs/PROGRESS.md).

**Status: early Phase 1 (Foundation).** The CLI, rule engine, and full report set described below
are not all implemented yet. This section will be replaced with a real quick start once the
Definition of Done in `BUILD_BRIEF.md` Section 25 is met.

## Quick start (target, not yet fully implemented)

```bash
uv sync
uv run collection-ci scan --mapping examples/mappings/clean.yaml --rules rulesets/core.yaml \
  --output-dir build/scan
```

## License

Apache-2.0. See `BUILD_BRIEF.md` Section 19 for the rationale (permissive, patent-grant clause
suitable for an open-source tool that institutions may adopt and extend).
