"""Persistent run history (BUILD_BRIEF.md Section 8: engine/run_store.py).

A minimal, dependency-free store: each scan run is written as one JSON file under a runs directory,
recording the run id, timestamp, severity counts, and the finding fingerprints. Fingerprints are
the stable cross-run identity used for baselines and "what changed since last time" (Phase 3), so
storing them now is what makes that comparison possible later.

DuckDB-backed analytical history (per the recommended stack) is deferred until run volumes justify
it; see docs/BUILD_PLAN.md. The JSON layout here is intentionally simple and forward-compatible.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from collection_integrity.engine.findings import Finding

RUN_RECORD_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    created_at: str
    total_findings: int
    severity_counts: dict[str, int]
    fingerprints: list[str]
    schema_version: str = RUN_RECORD_SCHEMA_VERSION


def summarize(findings: list[Finding], run_id: str | None = None) -> RunSummary:
    """Build a RunSummary from findings. Fingerprints are sorted for a stable, comparable record."""
    counts = Counter(f.severity for f in findings)
    return RunSummary(
        run_id=run_id or uuid.uuid4().hex,
        created_at=datetime.now(UTC).isoformat(),
        total_findings=len(findings),
        severity_counts=dict(sorted(counts.items())),
        fingerprints=sorted(f.fingerprint for f in findings),
    )


@dataclass
class RunStore:
    """A directory of run records."""

    root: Path

    @property
    def runs_dir(self) -> Path:
        return self.root / "runs"

    def save(self, summary: RunSummary) -> Path:
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        path = self.runs_dir / f"{summary.created_at.replace(':', '-')}_{summary.run_id}.json"
        path.write_text(
            json.dumps(asdict(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return path

    def list_runs(self) -> list[RunSummary]:
        """All stored runs, oldest first (by created_at, then run_id for a total order)."""
        if not self.runs_dir.is_dir():
            return []
        summaries: list[RunSummary] = []
        for path in self.runs_dir.glob("*.json"):
            summaries.append(_from_json(path.read_text(encoding="utf-8")))
        summaries.sort(key=lambda s: (s.created_at, s.run_id))
        return summaries

    def latest(self) -> RunSummary | None:
        runs = self.list_runs()
        return runs[-1] if runs else None


def _from_json(text: str) -> RunSummary:
    data: dict[str, object] = json.loads(text)
    severity_counts = data["severity_counts"]
    fingerprints = data["fingerprints"]
    assert isinstance(severity_counts, dict)
    assert isinstance(fingerprints, list)
    return RunSummary(
        run_id=str(data["run_id"]),
        created_at=str(data["created_at"]),
        total_findings=int(str(data["total_findings"])),
        severity_counts={str(k): int(v) for k, v in severity_counts.items()},
        fingerprints=[str(fp) for fp in fingerprints],
        schema_version=str(data.get("schema_version", RUN_RECORD_SCHEMA_VERSION)),
    )
