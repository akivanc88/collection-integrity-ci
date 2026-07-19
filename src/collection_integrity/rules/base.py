"""Rule base class and evaluation context (BUILD_BRIEF.md Section 11).

A rule is a deterministic check over the canonical entities loaded for a scan. Each rule declares
a stable `RuleRef` (id, name, version) and a default severity, and returns a list of `Finding`s.
The engine can enable/disable a rule and override its severity per run without the rule needing to
know about that machinery — see `registry.py`.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from collection_integrity.canonical.models import (
    AgentOrMaker,
    CollectionObject,
    LocationRecord,
    MediaAsset,
    RightsRecord,
)
from collection_integrity.engine.findings import (
    EntityRef,
    EvidenceItem,
    Finding,
    RuleRef,
    Severity,
    compute_fingerprint,
)


@dataclass(frozen=True)
class RuleContext:
    """Everything a rule needs to evaluate a scan.

    An agent/maker collection will be added here as the entities and the rules that consume them
    land (Phase 2).
    """

    objects: list[CollectionObject]
    media: list[MediaAsset] = field(default_factory=list)
    rights: list[RightsRecord] = field(default_factory=list)
    locations: list[LocationRecord] = field(default_factory=list)
    agents: list[AgentOrMaker] = field(default_factory=list)
    required_fields: list[str] = field(default_factory=list)
    # object field name -> allowed values (VOCAB001). Empty means the check is inactive.
    controlled_vocabularies: dict[str, list[str]] = field(default_factory=dict)
    # object canonical field -> source column, for reporting the raw value in SCHEMA001.
    object_field_sources: dict[str, str] = field(default_factory=dict)
    # Media-file checks (MEDIA001-004). Inactive unless check_media_files is True and a root is set.
    check_media_files: bool = False
    media_root: Path | None = None
    min_image_width: int = 0
    min_image_height: int = 0


class Rule(ABC):
    """Base class for all deterministic rules."""

    rule: RuleRef
    default_severity: Severity

    @abstractmethod
    def evaluate(self, ctx: RuleContext, severity: Severity) -> list[Finding]:
        """Return findings for this rule.

        `severity` is the effective (possibly registry-overridden) level for this run.
        """

    def make_finding(
        self,
        *,
        severity: Severity,
        entity: EntityRef,
        entity_id_for_fingerprint: str,
        evidence_keys: list[str],
        summary: str,
        explanation: str,
        recommendation: str,
        evidence: list[EvidenceItem],
        confidence: float = 1.0,
    ) -> Finding:
        """Construct a Finding, filling in run-specific id/timestamp and a stable fingerprint."""
        return Finding(
            finding_id=str(uuid.uuid4()),
            fingerprint=compute_fingerprint(
                rule_id=self.rule.id,
                entity_type=entity.type,
                entity_id=entity_id_for_fingerprint,
                field=entity.field,
                evidence_keys=evidence_keys,
            ),
            rule=self.rule,
            severity=severity,
            verification_type="deterministic",
            entity=entity,
            summary=summary,
            explanation=explanation,
            evidence=evidence,
            recommendation=recommendation,
            confidence=confidence,
            created_at=datetime.now(UTC),
        )
