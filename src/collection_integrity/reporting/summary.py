"""Scan summary report (BUILD_BRIEF.md Section 14)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from collection_integrity.engine.findings import Finding


def build_summary(findings: list[Finding], input_counts: dict[str, int]) -> dict[str, object]:
    """A compact, machine-readable summary of a scan's outcome."""
    severity = Counter(f.severity for f in findings)
    by_rule = Counter(f.rule.id for f in findings)
    return {
        "total_findings": len(findings),
        "severity_counts": dict(sorted(severity.items())),
        "findings_by_rule": dict(sorted(by_rule.items())),
        "input_counts": dict(sorted(input_counts.items())),
    }


def write_summary_json(findings: list[Finding], input_counts: dict[str, int], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_summary(findings, input_counts)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
