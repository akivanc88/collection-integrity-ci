"""Date rules (BUILD_BRIEF.md Section 11, item 9).

DATE001 flags an object whose production start date is after its production end date. DATE002
(agent-lifespan conflict) needs the agent entity and is tracked in docs/BACKLOG.md.
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


class InvertedDateRangeRule(Rule):
    """DATE001: production_start_date is after production_end_date."""

    rule = RuleRef(
        id="DATE001_INVERTED_DATE_RANGE",
        name="Inverted production date range",
        version="1.0.0",
    )
    default_severity: Severity = "medium"

    def evaluate(self, ctx: RuleContext, severity: Severity) -> list[Finding]:
        findings: list[Finding] = []
        for obj in sorted(ctx.objects, key=lambda o: o.object_id):
            start, end = obj.production_start_date, obj.production_end_date
            if start is None or end is None or start <= end:
                continue
            findings.append(
                self.make_finding(
                    severity=severity,
                    entity=EntityRef(
                        type="object", id=obj.object_id, field="production_start_date"
                    ),
                    entity_id_for_fingerprint=obj.object_id,
                    evidence_keys=[start.isoformat(), end.isoformat()],
                    summary=(
                        f"Object {obj.object_id} has production start {start.isoformat()} after "
                        f"end {end.isoformat()}."
                    ),
                    explanation=(
                        f"Object {obj.object_id} has production_start_date={start.isoformat()} "
                        f"which is later than production_end_date={end.isoformat()}."
                    ),
                    recommendation=(
                        "Correct the production start or end date so the range is not inverted."
                    ),
                    evidence=[
                        EvidenceItem(
                            source_file=obj.source_ref.source_file,
                            source_row=obj.source_ref.source_row_number,
                            field="production_start_date",
                            value=start.isoformat(),
                        ),
                        EvidenceItem(
                            source_file=obj.source_ref.source_file,
                            source_row=obj.source_ref.source_row_number,
                            field="production_end_date",
                            value=end.isoformat(),
                        ),
                    ],
                )
            )
        return findings
