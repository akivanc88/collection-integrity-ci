"""Controlled-vocabulary rules (BUILD_BRIEF.md Section 11, item 11).

VOCAB001 flags an object field whose value is outside the configured controlled vocabulary for
that field. The vocabularies come from the ruleset via RuleContext.controlled_vocabularies; when a
field has no configured vocabulary the check is inactive for it.
"""

from __future__ import annotations

from collection_integrity.engine.findings import (
    EntityRef,
    EvidenceItem,
    Finding,
    RuleRef,
    Severity,
)
from collection_integrity.rules.base import Rule, RuleContext


class UnknownControlledValueRule(Rule):
    """VOCAB001: an object field value is not in its configured vocabulary."""

    rule = RuleRef(
        id="VOCAB001_UNKNOWN_CONTROLLED_VALUE",
        name="Unknown controlled value",
        version="1.0.0",
    )
    default_severity: Severity = "medium"

    def evaluate(self, ctx: RuleContext, severity: Severity) -> list[Finding]:
        findings: list[Finding] = []
        for field_name, allowed in sorted(ctx.controlled_vocabularies.items()):
            allowed_set = set(allowed)
            for obj in sorted(ctx.objects, key=lambda o: o.object_id):
                value = getattr(obj, field_name, None)
                if value is None or value in allowed_set:
                    continue
                findings.append(
                    self.make_finding(
                        severity=severity,
                        entity=EntityRef(type="object", id=obj.object_id, field=field_name),
                        entity_id_for_fingerprint=obj.object_id,
                        evidence_keys=[field_name, str(value)],
                        summary=(
                            f"Object {obj.object_id} has {field_name}={value!r}, which is not in "
                            f"the controlled vocabulary."
                        ),
                        explanation=(
                            f"Object {obj.object_id} has {field_name}={value!r}. The configured "
                            f"vocabulary for {field_name} allows: {', '.join(sorted(allowed_set))}."
                        ),
                        recommendation=(
                            f"Change {field_name} to an allowed value, or extend the vocabulary in "
                            f"the ruleset if {value!r} is legitimate."
                        ),
                        evidence=[
                            EvidenceItem(
                                source_file=obj.source_ref.source_file,
                                source_row=obj.source_ref.source_row_number,
                                field=field_name,
                                value=value,
                            )
                        ],
                    )
                )
        return findings
