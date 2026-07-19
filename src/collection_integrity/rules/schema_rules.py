"""Schema/type rules (BUILD_BRIEF.md Section 11, item 3).

SCHEMA001 flags a value that is present in the source but cannot be parsed to its declared
canonical type. It reuses the ingestion parser so "valid" is defined once, and reads the raw value
back from provenance (source_ref.raw_fields) via the object's canonical->source field map, so the
finding shows the offending original text rather than a silently-dropped None.
"""

from __future__ import annotations

from collection_integrity.engine.findings import (
    EntityRef,
    EvidenceItem,
    Finding,
    RuleRef,
    Severity,
)
from collection_integrity.ingestion.mapper import TYPED_OBJECT_FIELDS, parse_date
from collection_integrity.rules.base import Rule, RuleContext


class InvalidFieldTypeRule(Rule):
    """SCHEMA001: a non-empty source value does not parse to its declared type."""

    rule = RuleRef(
        id="SCHEMA001_INVALID_FIELD_TYPE",
        name="Invalid field type",
        version="1.0.0",
    )
    default_severity: Severity = "high"

    def evaluate(self, ctx: RuleContext, severity: Severity) -> list[Finding]:
        if not ctx.object_field_sources:
            return []

        findings: list[Finding] = []
        for obj in sorted(ctx.objects, key=lambda o: o.object_id):
            raw_fields = obj.source_ref.raw_fields or {}
            for field_name, expected_type in sorted(TYPED_OBJECT_FIELDS.items()):
                source = ctx.object_field_sources.get(field_name)
                if source is None:
                    continue
                raw = (raw_fields.get(source) or "").strip()
                if not raw or _parses(raw, expected_type):
                    continue
                findings.append(
                    self.make_finding(
                        severity=severity,
                        entity=EntityRef(type="object", id=obj.object_id, field=field_name),
                        entity_id_for_fingerprint=obj.object_id,
                        evidence_keys=[field_name, expected_type],
                        summary=(
                            f"Object {obj.object_id} has {field_name}={raw!r}, which is not a "
                            f"valid {expected_type}."
                        ),
                        explanation=(
                            f"Object {obj.object_id} has a value of {raw!r} for {field_name}, but "
                            f"that field must be a {expected_type}. The raw value is preserved."
                        ),
                        recommendation=(
                            f"Correct the {field_name} value to a valid {expected_type}."
                        ),
                        evidence=[
                            EvidenceItem(
                                source_file=obj.source_ref.source_file,
                                source_row=obj.source_ref.source_row_number,
                                field=field_name,
                                value=raw,
                            )
                        ],
                    )
                )
        return findings


def _parses(raw: str, expected_type: str) -> bool:
    if expected_type == "date":
        return parse_date(raw) is not None
    if expected_type == "int":
        try:
            int(raw)
            return True
        except ValueError:
            return False
    return True
