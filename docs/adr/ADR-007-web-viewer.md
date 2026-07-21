# ADR 007: Local web-viewer architecture

- Status: Accepted
- Date: 2026-07-21
- Phase: 5 (local viewer)

## Context

BUILD_BRIEF.md Section 24 (Phase 5) calls for "a polished local findings viewer only after the
engine and reports are stable," gated behind Phases 1–3 (now complete). Section 7 recommends
FastAPI and explicitly permits a server-rendered FastAPI + Jinja + HTMX implementation "if it
produces a polished accessible interface with less complexity." The product is local-first, offline,
and self-contained (no external assets, no network calls, no source-data mutation).

## Decision

Build the viewer as a **server-rendered FastAPI application** that serves a **read-only snapshot of a
completed scan run directory**, not a live re-run of the engine.

1. **FastAPI, server-rendered.** No React/TypeScript build toolchain. Pages are rendered with Jinja2
   (already a dependency for the standalone HTML report). Filtering is done with plain query-param
   forms that work without JavaScript (progressive enhancement), so no HTMX/JS bundle needs to be
   vendored — this keeps the "no external assets" guarantee trivially true and the interface
   accessible by default.
2. **Read-only run view.** `api/run_view.py` loads the artifacts a scan already produced
   (findings.json, summary.json, run_manifest.json, report.html) into an immutable `RunView`. The
   viewer consumes the *report format*, not the engine's Pydantic models, so it stays decoupled from
   the engine; the report files are the stable contract. Nothing writes to the run directory or any
   source file.
3. **Load once, fail fast.** `create_app(run_dir)` loads and validates the run at construction time,
   so an invalid directory errors before the server binds a port.
4. **JSON API + HTML pages.** A small JSON API (`/api/health`, `/api/summary`, `/api/manifest`,
   `/api/findings`, `/api/findings/{fingerprint}`) backs the same data the HTML pages render, so the
   viewer is scriptable and testable via `TestClient` without a browser.
5. **Localhost by default.** `collection-ci serve --run-dir` binds `127.0.0.1`, consistent with the
   local-first, no-network posture. `uvicorn` is the ASGI server.

## Consequences

- **Simplicity and safety:** no frontend build, no CDN assets, no data mutation; the viewer cannot
  change findings, only display them.
- **Testability:** every endpoint is exercised via FastAPI's `TestClient` against a real run
  directory generated from AI-synthesised data, scored the same way as the rest of the project.
- **Trade-off:** the viewer shows a static snapshot of one run; live re-scanning or multi-run history
  browsing is out of scope for the MVP (see `docs/FUTURE_SCOPE.md`).
- **New dependencies:** `fastapi`, `uvicorn` (runtime), `httpx` (dev, for `TestClient`).

## Alternatives considered

- **React + TypeScript SPA:** rejected for the MVP — a build toolchain and bundled assets add
  complexity and risk violating the self-contained/offline constraints without a clear benefit for a
  single-run findings viewer.
- **Serve only the existing report.html statically:** too limited; it gives no filtering or API. The
  viewer still links to the standalone report, but adds a filterable, scriptable layer on top.
