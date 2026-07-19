"""Date rules (BUILD_BRIEF.md Section 11, items 9-10).

DATE001 flags an object whose production start date is after its production end date. DATE002 is a
conservative policy rule flagging an impossible object/maker date relationship — only when both the
object's production dates and the maker's birth/death dates are present, and only for clear
impossibilities (production wholly before the maker's birth, or beginning after their death).
"""

from __future__ import annotations

from datetime import date

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


class AgentLifespanConflictRule(Rule):
    """DATE002: an object's production is impossible given a linked maker's lifespan."""

    rule = RuleRef(
        id="DATE002_IMPOSSIBLE_AGENT_LIFESPAN_CONFLICT",
        name="Impossible agent lifespan conflict",
        version="1.0.0",
    )
    default_severity: Severity = "medium"

    def evaluate(self, ctx: RuleContext, severity: Severity) -> list[Finding]:
        agents_by_id = {a.agent_id: a for a in ctx.agents}
        findings: list[Finding] = []
        for obj in sorted(ctx.objects, key=lambda o: o.object_id):
            start, end = obj.production_start_date, obj.production_end_date
            if start is None or end is None:
                continue
            for maker_id in obj.maker_ids:
                agent = agents_by_id.get(maker_id)
                if agent is None or agent.birth_date is None or agent.death_date is None:
                    continue
                reason = _impossible_reason(start, end, agent.birth_date, agent.death_date)
                if reason is None:
                    continue
                findings.append(
                    self.make_finding(
                        severity=severity,
                        entity=EntityRef(type="object", id=obj.object_id, field="maker_ids"),
                        entity_id_for_fingerprint=f"{obj.object_id}|{maker_id}",
                        evidence_keys=[maker_id, reason],
                        summary=(
                            f"Object {obj.object_id} production conflicts with maker {maker_id} "
                            f"lifespan ({reason})."
                        ),
                        explanation=(
                            f"Object {obj.object_id} was produced "
                            f"{start.isoformat()}..{end.isoformat()}, but maker {maker_id} lived "
                            f"{agent.birth_date.isoformat()}..{agent.death_date.isoformat()}. "
                            f"{reason}. This is a conservative consistency check based on the "
                            f"dates present, not an attribution judgement."
                        ),
                        recommendation=(
                            "Verify the production dates, the maker link, or the maker's life "
                            "dates; one of them is likely wrong."
                        ),
                        evidence=[
                            EvidenceItem(
                                source_file=obj.source_ref.source_file,
                                source_row=obj.source_ref.source_row_number,
                                field="production_start_date",
                                value=start.isoformat(),
                            ),
                            EvidenceItem(
                                source_file=agent.source_ref.source_file,
                                source_row=agent.source_ref.source_row_number,
                                field="death_date",
                                value=agent.death_date.isoformat(),
                            ),
                        ],
                    )
                )
        return findings


def _impossible_reason(start: date, end: date, birth: date, death: date) -> str | None:
    if end < birth:
        return "production ended before the maker was born"
    if start > death:
        return "production began after the maker died"
    return None
