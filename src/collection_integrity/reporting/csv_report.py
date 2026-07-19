"""CSV findings report (BUILD_BRIEF.md Section 14).

Flattens the most useful finding columns for spreadsheet triage, keeping the full evidence as a
JSON string in a dedicated column so nothing is lost. Rows are written in a stable order
(fingerprint) so two runs over the same findings produce identical CSV.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from collection_integrity.engine.findings import Finding

COLUMNS = [
    "fingerprint",
    "rule_id",
    "rule_version",
    "severity",
    "verification_type",
    "status",
    "entity_type",
    "entity_id",
    "entity_field",
    "summary",
    "recommendation",
    "evidence_json",
    "created_at",
]


def write_findings_csv(findings: list[Finding], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        for finding in sorted(findings, key=lambda f: f.fingerprint):
            writer.writerow(
                {
                    "fingerprint": finding.fingerprint,
                    "rule_id": finding.rule.id,
                    "rule_version": finding.rule.version,
                    "severity": finding.severity,
                    "verification_type": finding.verification_type,
                    "status": finding.status,
                    "entity_type": finding.entity.type,
                    "entity_id": finding.entity.id,
                    "entity_field": finding.entity.field or "",
                    "summary": finding.summary,
                    "recommendation": finding.recommendation,
                    "evidence_json": json.dumps(
                        [e.model_dump(mode="json") for e in finding.evidence], sort_keys=True
                    ),
                    "created_at": finding.created_at.isoformat(),
                }
            )
