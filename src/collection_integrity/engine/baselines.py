"""Baseline comparison (BUILD_BRIEF.md Section 15).

Compares a scan's findings against a previously saved baseline (a findings.json) by stable
fingerprint, classifying each as new, unchanged, or resolved-since-baseline. A baseline suppresses
known-issue noise for the CI failure decision (via --only-new) but never removes existing findings
from the full report — the reports still list everything.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from collection_integrity.engine.findings import Finding


class BaselineError(ValueError):
    """Raised when a baseline file cannot be read."""


def load_baseline_fingerprints(path: Path) -> set[str]:
    """Read the fingerprints recorded in a baseline findings.json."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"{path}: cannot read baseline: {exc}") from exc
    if not isinstance(data, list):
        raise BaselineError(f"{path}: baseline must be a JSON array of findings")
    fingerprints: set[str] = set()
    for item in data:
        if isinstance(item, dict) and "fingerprint" in item:
            fingerprints.add(str(item["fingerprint"]))
    return fingerprints


@dataclass(frozen=True)
class BaselineComparison:
    new: list[Finding] = field(default_factory=list)
    unchanged: list[Finding] = field(default_factory=list)
    resolved_fingerprints: set[str] = field(default_factory=set)

    @property
    def counts(self) -> dict[str, int]:
        return {
            "new": len(self.new),
            "unchanged": len(self.unchanged),
            "resolved": len(self.resolved_fingerprints),
        }


def classify(findings: list[Finding], baseline_fingerprints: set[str]) -> BaselineComparison:
    """Split findings into new vs unchanged, and report which baseline findings are now resolved."""
    current = {f.fingerprint for f in findings}
    new = [f for f in findings if f.fingerprint not in baseline_fingerprints]
    unchanged = [f for f in findings if f.fingerprint in baseline_fingerprints]
    resolved = baseline_fingerprints - current
    return BaselineComparison(new=new, unchanged=unchanged, resolved_fingerprints=resolved)
