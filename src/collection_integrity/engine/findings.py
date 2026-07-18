"""Finding model (BUILD_BRIEF.md Section 12) and stable fingerprinting.

Only the fields needed by the first rule (CORE001) are exercised so far, but the model itself
follows the full schema from the brief so later rules do not need a breaking migration.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Severity = Literal["critical", "high", "medium", "low"]
VerificationType = Literal["deterministic", "probabilistic"]
FindingStatus = Literal[
    "open",
    "acknowledged",
    "accepted_risk",
    "false_positive",
    "resolved",
    "suppressed",
]

FINDING_SCHEMA_VERSION = "1.0"


class RuleRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    version: str


class EntityRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: str
    id: str
    field: str | None = None


class EvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_file: str
    source_row: int | None = None
    field: str
    value: str | int | float | bool | None = None


class Finding(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = FINDING_SCHEMA_VERSION
    finding_id: str
    fingerprint: str
    rule: RuleRef
    severity: Severity
    verification_type: VerificationType
    status: FindingStatus = "open"
    entity: EntityRef
    summary: str
    explanation: str
    evidence: list[EvidenceItem]
    recommendation: str
    confidence: float
    created_at: datetime


def compute_fingerprint(
    rule_id: str,
    entity_type: str,
    entity_id: str,
    field: str | None,
    evidence_keys: list[str],
) -> str:
    """Stable, cross-run fingerprint for deduplication and baselines.

    Deliberately excludes run timestamp and finding_id: two runs over the same input must
    produce the same fingerprint for the same underlying issue.
    """
    digest = hashlib.sha256()
    parts = [rule_id.strip().upper(), entity_type.strip().lower(), entity_id.strip(), field or ""]
    parts.extend(sorted(evidence_keys))
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()
