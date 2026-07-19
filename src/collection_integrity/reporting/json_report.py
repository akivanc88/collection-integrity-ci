"""JSON findings report (BUILD_BRIEF.md Section 14)."""

from __future__ import annotations

import json
from pathlib import Path

from collection_integrity.engine.findings import Finding


def write_findings_json(findings: list[Finding], path: Path) -> None:
    """Write findings as a JSON array, deterministically (sorted keys, trailing newline)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [f.model_dump(mode="json") for f in findings]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
