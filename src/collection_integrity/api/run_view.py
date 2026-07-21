"""Read-only view over a completed scan run directory (BUILD_BRIEF.md Section 24, Phase 5).

The local web viewer never re-runs the engine and never writes to a source file or the run
directory — it loads the artifacts a `collection-ci scan` already produced (findings.json,
summary.json, run_manifest.json, and the standalone report.html if present) and serves them. Loading
the report format rather than the engine's models keeps the viewer decoupled from the engine: the
report files are the stable contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Severity order for stable, meaningful sorting in the API and UI (most severe first).
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class RunViewError(ValueError):
    """Raised when a run directory cannot be loaded into a view."""


@dataclass(frozen=True)
class RunView:
    """An immutable snapshot of one scan run's artifacts."""

    run_dir: Path
    findings: list[dict[str, Any]]
    summary: dict[str, Any]
    manifest: dict[str, Any] | None
    has_html_report: bool

    @classmethod
    def load(cls, run_dir: Path) -> RunView:
        if not run_dir.exists() or not run_dir.is_dir():
            raise RunViewError(f"run directory not found: {run_dir}")

        findings = _load_json(run_dir / "findings.json", required=True)
        if not isinstance(findings, list):
            raise RunViewError("findings.json must be a JSON array")

        summary = _load_json(run_dir / "summary.json", required=True)
        if not isinstance(summary, dict):
            raise RunViewError("summary.json must be a JSON object")

        manifest = _load_json(run_dir / "run_manifest.json", required=False)
        if manifest is not None and not isinstance(manifest, dict):
            raise RunViewError("run_manifest.json must be a JSON object")

        return cls(
            run_dir=run_dir,
            findings=findings,
            summary=summary,
            manifest=manifest,
            has_html_report=(run_dir / "report.html").is_file(),
        )

    def filter_findings(
        self, severity: str | None = None, rule: str | None = None
    ) -> list[dict[str, Any]]:
        """Findings matching the given severity and/or rule id, most-severe first then by rule.

        A None filter matches everything; an unrecognized value simply matches nothing.
        """
        result = [
            f
            for f in self.findings
            if (severity is None or f.get("severity") == severity)
            and (rule is None or _rule_id(f) == rule)
        ]
        result.sort(key=lambda f: (SEVERITY_ORDER.get(f.get("severity", ""), 99), _rule_id(f)))
        return result

    def get_finding(self, fingerprint: str) -> dict[str, Any] | None:
        for f in self.findings:
            if f.get("fingerprint") == fingerprint:
                return f
        return None

    def rule_ids(self) -> list[str]:
        """Distinct rule ids present in the findings, sorted."""
        return sorted({_rule_id(f) for f in self.findings if _rule_id(f)})

    def severities(self) -> list[str]:
        """Distinct severities present, ordered most severe first."""
        present = {f.get("severity", "") for f in self.findings if f.get("severity")}
        return sorted(present, key=lambda s: SEVERITY_ORDER.get(s, 99))

    @property
    def total_findings(self) -> int:
        return len(self.findings)


def _rule_id(finding: dict[str, Any]) -> str:
    rule = finding.get("rule")
    return rule.get("id", "") if isinstance(rule, dict) else ""


def _load_json(path: Path, *, required: bool) -> Any:
    if not path.is_file():
        if required:
            raise RunViewError(f"missing required artifact: {path.name}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RunViewError(f"{path.name}: invalid JSON: {exc}") from exc
