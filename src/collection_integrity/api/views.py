"""Server-rendered HTML pages for the local viewer (BUILD_BRIEF.md Section 24, Phase 5, Slice T).

Accessible, self-contained pages (inline CSS, no external assets, no client JS required) rendered
with Jinja2 (autoescape on, so finding text is XSS-safe). Filtering is done with plain query-param
forms that work without JavaScript. The pages read the same read-only `RunView` the JSON API uses.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from collection_integrity.api.run_view import RunView

_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def register_views(app: FastAPI, run: RunView) -> None:
    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> HTMLResponse:
        counts = run.summary.get("severity_counts", {}) if isinstance(run.summary, dict) else {}
        return _TEMPLATES.TemplateResponse(
            request,
            "dashboard.html",
            {
                "run": run,
                "summary": run.summary,
                "manifest": run.manifest,
                "severity_counts": counts,
                "severities": run.severities(),
            },
        )

    @app.get("/findings", response_class=HTMLResponse)
    def findings_page(
        request: Request,
        severity: str | None = Query(default=None),
        rule: str | None = Query(default=None),
    ) -> HTMLResponse:
        matched = run.filter_findings(severity=severity or None, rule=rule or None)
        return _TEMPLATES.TemplateResponse(
            request,
            "findings.html",
            {
                "findings": matched,
                "severity": severity or "",
                "rule": rule or "",
                "rule_ids": run.rule_ids(),
                "severities": run.severities(),
                "total": run.total_findings,
            },
        )

    @app.get("/findings/{fingerprint}", response_class=HTMLResponse)
    def finding_detail(request: Request, fingerprint: str) -> HTMLResponse:
        found = run.get_finding(fingerprint)
        if found is None:
            raise HTTPException(status_code=404, detail="finding not found")
        return _TEMPLATES.TemplateResponse(request, "detail.html", {"f": found})

    @app.get("/report")
    def report() -> FileResponse:
        path = run.run_dir / "report.html"
        if not path.is_file():
            raise HTTPException(status_code=404, detail="no report.html in this run directory")
        return FileResponse(path, media_type="text/html")
