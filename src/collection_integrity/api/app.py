"""FastAPI application for the local findings viewer (BUILD_BRIEF.md Section 24, Phase 5).

`create_app(run_dir)` loads a completed scan run once (a read-only snapshot) and exposes it over a
small JSON API plus server-rendered HTML pages. The app binds to localhost by default, makes no
network calls, and serves only self-contained assets — consistent with the offline, local-first
product. The HTML routes live in `views.py`; this module owns app construction and the JSON API.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from collection_integrity.api.run_view import RunView


def create_app(run_dir: Path) -> FastAPI:
    """Build the viewer app for a completed scan run directory.

    Loading happens here so an invalid run directory fails fast (before the server starts) rather
    than on the first request.
    """
    run = RunView.load(run_dir)
    app = FastAPI(title="Collection Integrity CI — findings viewer", docs_url=None, redoc_url=None)
    app.state.run = run

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "run_dir": str(run.run_dir),
            "total_findings": run.total_findings,
        }

    @app.get("/api/summary")
    def summary() -> dict[str, Any]:
        return run.summary

    @app.get("/api/manifest")
    def manifest() -> dict[str, Any]:
        if run.manifest is None:
            raise HTTPException(status_code=404, detail="no run manifest in this run directory")
        return run.manifest

    @app.get("/api/findings")
    def findings(
        severity: str | None = Query(default=None),
        rule: str | None = Query(default=None),
    ) -> dict[str, Any]:
        matched = run.filter_findings(severity=severity, rule=rule)
        return {"count": len(matched), "findings": matched}

    @app.get("/api/findings/{fingerprint}")
    def finding(fingerprint: str) -> JSONResponse:
        found = run.get_finding(fingerprint)
        if found is None:
            raise HTTPException(status_code=404, detail="finding not found")
        return JSONResponse(found)

    return app
