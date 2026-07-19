"""Core structural rules (BUILD_BRIEF.md Section 11, items 1-2).

CORE001 (duplicate accession number) and CORE002 (required field missing) are implemented as
`Rule` subclasses and registered in `registry.py`. More rules (REF/RIGHTS/LOC/DATE/VOCAB/MEDIA)
are tracked in docs/BACKLOG.md for later Phase 2 slices.
"""

from __future__ import annotations

from collections import defaultdict

from collection_integrity.canonical.models import CollectionObject
from collection_integrity.engine.findings import (
    EntityRef,
    EvidenceItem,
    Finding,
    RuleRef,
    Severity,
)
from collection_integrity.rules.base import Rule, RuleContext

# Canonical object fields CORE002 is allowed to check. `object_id` is guaranteed present by the
# ingestion adapter, so it is not offered as a configurable required field here.
REQUIRABLE_OBJECT_FIELDS = ("accession_number", "object_name", "title")


class DuplicateAccessionNumberRule(Rule):
    """CORE001: detect duplicate non-empty accession numbers."""

    rule = RuleRef(
        id="CORE001_DUPLICATE_ACCESSION_NUMBER",
        name="Duplicate accession number",
        version="1.0.0",
    )
    default_severity: Severity = "critical"

    def evaluate(self, ctx: RuleContext, severity: Severity) -> list[Finding]:
        by_accession: dict[str, list[CollectionObject]] = defaultdict(list)
        for obj in ctx.objects:
            if obj.accession_number:
                by_accession[obj.accession_number].append(obj)

        findings: list[Finding] = []
        for accession_number, group in by_accession.items():
            if len(group) < 2:
                continue

            ordered = sorted(group, key=lambda o: o.object_id)
            object_ids = [o.object_id for o in ordered]
            evidence = [
                EvidenceItem(
                    source_file=o.source_ref.source_file,
                    source_row=o.source_ref.source_row_number,
                    field="accession_number",
                    value=o.accession_number,
                )
                for o in ordered
            ]
            findings.append(
                self.make_finding(
                    severity=severity,
                    entity=EntityRef(type="object", id=accession_number, field="accession_number"),
                    entity_id_for_fingerprint=accession_number,
                    evidence_keys=object_ids,
                    summary=(
                        f"Accession number {accession_number!r} is used by {len(group)} objects."
                    ),
                    explanation=(
                        f"Objects {', '.join(object_ids)} all have accession_number="
                        f"{accession_number!r}. Accession numbers must uniquely identify one "
                        f"object."
                    ),
                    recommendation=(
                        "Confirm which object legitimately holds this accession number and "
                        "correct or reassign the others according to institutional policy."
                    ),
                    evidence=evidence,
                )
            )
        return findings


class RequiredFieldMissingRule(Rule):
    """CORE002: a policy-required field is missing.

    Whitespace-only values are already normalized to None by the ingestion adapter, so a missing
    value here means the canonical field is None. Which fields are required is ruleset-specific and
    supplied via `RuleContext.required_fields`; unknown field names are ignored defensively rather
    than raising, so a typo in a ruleset cannot crash a scan.
    """

    rule = RuleRef(
        id="CORE002_REQUIRED_FIELD_MISSING",
        name="Required field missing",
        version="1.0.0",
    )
    default_severity: Severity = "high"

    def evaluate(self, ctx: RuleContext, severity: Severity) -> list[Finding]:
        checked_fields = [f for f in ctx.required_fields if f in REQUIRABLE_OBJECT_FIELDS]

        findings: list[Finding] = []
        for obj in sorted(ctx.objects, key=lambda o: o.object_id):
            for field_name in checked_fields:
                if getattr(obj, field_name) is not None:
                    continue
                findings.append(
                    self.make_finding(
                        severity=severity,
                        entity=EntityRef(type="object", id=obj.object_id, field=field_name),
                        entity_id_for_fingerprint=obj.object_id,
                        evidence_keys=[field_name],
                        summary=f"Object {obj.object_id} is missing required field {field_name!r}.",
                        explanation=(
                            f"Object {obj.object_id} has no value for {field_name!r}, which the "
                            f"active ruleset marks as required."
                        ),
                        recommendation=(
                            f"Populate {field_name!r} for object {obj.object_id}, or relax the "
                            f"requirement in the ruleset if the field is not applicable."
                        ),
                        evidence=[
                            EvidenceItem(
                                source_file=obj.source_ref.source_file,
                                source_row=obj.source_ref.source_row_number,
                                field=field_name,
                                value=None,
                            )
                        ],
                    )
                )
        return findings
