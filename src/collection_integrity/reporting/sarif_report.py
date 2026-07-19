"""SARIF 2.1.0 report (BUILD_BRIEF.md Section 14).

Emits findings as SARIF so a GitHub code-scanning upload annotates the offending source files.
Severity maps to SARIF levels (critical/high -> error, medium -> warning, low -> note). Each result
carries the stable fingerprint as a partialFingerprint so GitHub can track a finding across runs,
and a physical location (source file + row) when the evidence provides one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from collection_integrity import __version__
from collection_integrity.engine.findings import Finding

SARIF_VERSION = "2.1.0"
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
TOOL_NAME = "collection-integrity-ci"
INFORMATION_URI = "https://github.com/collection-integrity-ci/collection-integrity-ci"

_LEVEL = {"critical": "error", "high": "error", "medium": "warning", "low": "note"}


def severity_to_level(severity: str) -> str:
    return _LEVEL.get(severity, "warning")


def build_sarif(
    findings: list[Finding], rules_metadata: list[tuple[str, str, str]]
) -> dict[str, Any]:
    """Build a SARIF 2.1.0 document. `rules_metadata` is (id, name, version) for enabled rules."""
    # Rule id -> index, so results can reference ruleIndex. Include every finding's rule even if it
    # is not in rules_metadata (defensive), so no result references a missing rule.
    ordered_ids: list[str] = []
    meta_by_id: dict[str, tuple[str, str, str]] = {}
    for rid, name, version in rules_metadata:
        if rid not in meta_by_id:
            meta_by_id[rid] = (rid, name, version)
            ordered_ids.append(rid)
    for f in findings:
        if f.rule.id not in meta_by_id:
            meta_by_id[f.rule.id] = (f.rule.id, f.rule.name, f.rule.version)
            ordered_ids.append(f.rule.id)

    rule_index = {rid: i for i, rid in enumerate(ordered_ids)}
    rules = [
        {
            "id": rid,
            "name": meta_by_id[rid][1],
            "version": meta_by_id[rid][2],
            "shortDescription": {"text": meta_by_id[rid][1]},
        }
        for rid in ordered_ids
    ]

    results = [_result(f, rule_index[f.rule.id]) for f in findings]

    return {
        "$schema": SARIF_SCHEMA,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": TOOL_NAME,
                        "version": __version__,
                        "informationUri": INFORMATION_URI,
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }


def _result(finding: Finding, rule_index: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ruleId": finding.rule.id,
        "ruleIndex": rule_index,
        "level": severity_to_level(finding.severity),
        "message": {"text": finding.summary},
        "partialFingerprints": {"collectionIntegrity/v1": finding.fingerprint},
    }
    location = _location(finding)
    if location is not None:
        result["locations"] = [location]
    return result


def _location(finding: Finding) -> dict[str, Any] | None:
    for ev in finding.evidence:
        if ev.source_file:
            region = {"startLine": ev.source_row} if ev.source_row else {}
            physical: dict[str, Any] = {"artifactLocation": {"uri": ev.source_file}}
            if region:
                physical["region"] = region
            return {"physicalLocation": physical}
    return None


def write_sarif_report(
    findings: list[Finding], rules_metadata: list[tuple[str, str, str]], path: Path
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = build_sarif(findings, rules_metadata)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
