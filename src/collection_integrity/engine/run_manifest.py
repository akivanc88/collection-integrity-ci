"""Run manifest (BUILD_BRIEF.md Section 14).

Records what was scanned and how, so a run is reproducible and auditable: software version, command,
run id, timestamps, input-file and config hashes, the enabled rules and versions, environment info
that is safe to record, counts, elapsed time, and explicit flags stating that no network access or
AI providers were used (the engine is deterministic and offline by design).
"""

from __future__ import annotations

import platform
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from collection_integrity import __version__
from collection_integrity.engine.findings import Finding
from collection_integrity.provenance import hash_file

MANIFEST_SCHEMA_VERSION = "1.0"


@dataclass
class RunManifest:
    schema_version: str
    software_version: str
    command: str
    run_id: str
    started_at: str
    ended_at: str
    elapsed_seconds: float
    input_hashes: dict[str, str]
    config_hashes: dict[str, str]
    enabled_rules: list[dict[str, str]]
    total_findings: int
    severity_counts: dict[str, int]
    network_access_used: bool
    ai_providers_used: bool
    environment: dict[str, str]
    warnings: list[str] = field(default_factory=list)


def build_run_manifest(
    *,
    command: str,
    run_id: str,
    started_at: str,
    ended_at: str,
    elapsed_seconds: float,
    input_files: list[Path],
    config_files: list[Path],
    enabled_rules: list[tuple[str, str]],
    findings: list[Finding],
    warnings: list[str] | None = None,
) -> RunManifest:
    counts = Counter(f.severity for f in findings)
    return RunManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        software_version=__version__,
        command=command,
        run_id=run_id,
        started_at=started_at,
        ended_at=ended_at,
        elapsed_seconds=round(elapsed_seconds, 6),
        input_hashes={str(p): hash_file(p) for p in input_files if p.is_file()},
        config_hashes={str(p): hash_file(p) for p in config_files if p.is_file()},
        enabled_rules=[{"id": rid, "version": ver} for rid, ver in enabled_rules],
        total_findings=len(findings),
        severity_counts=dict(sorted(counts.items())),
        # The deterministic engine never touches the network or an AI provider.
        network_access_used=False,
        ai_providers_used=False,
        environment={
            "python_version": platform.python_version(),
            "platform": platform.system(),
        },
        warnings=warnings or [],
    )


def manifest_to_dict(manifest: RunManifest) -> dict[str, object]:
    return asdict(manifest)
