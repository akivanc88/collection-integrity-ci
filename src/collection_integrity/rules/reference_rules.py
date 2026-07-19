"""Referential-integrity rules (BUILD_BRIEF.md Section 11, items 4-5).

REF001 (orphan media -> object) is implemented. REF002 (orphan rights reference) is tracked in
docs/BACKLOG.md and lands with the RightsRecord entity.
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


class OrphanMediaObjectRule(Rule):
    """REF001: a media record references an object_id that does not exist."""

    rule = RuleRef(
        id="REF001_ORPHAN_MEDIA_OBJECT",
        name="Orphan media object reference",
        version="1.0.0",
    )
    default_severity: Severity = "high"

    def evaluate(self, ctx: RuleContext, severity: Severity) -> list[Finding]:
        object_ids = {o.object_id for o in ctx.objects}

        findings: list[Finding] = []
        for media in sorted(ctx.media, key=lambda m: m.media_id):
            # A media record with no object_id at all is a missing-reference concern for a
            # required-field rule, not an orphan reference; REF001 only flags a present-but-unknown
            # target.
            if not media.object_id:
                continue
            if media.object_id in object_ids:
                continue
            findings.append(
                self.make_finding(
                    severity=severity,
                    entity=EntityRef(type="media", id=media.media_id, field="object_id"),
                    entity_id_for_fingerprint=media.media_id,
                    evidence_keys=[media.object_id],
                    summary=(
                        f"Media {media.media_id} references object {media.object_id!r}, "
                        f"which does not exist."
                    ),
                    explanation=(
                        f"Media record {media.media_id} has object_id={media.object_id!r}, but no "
                        f"object with that id is present in the objects entity. The media asset is "
                        f"orphaned."
                    ),
                    recommendation=(
                        "Correct the media record's object_id, restore the missing object, or "
                        "remove the orphaned media reference according to institutional policy."
                    ),
                    evidence=[
                        EvidenceItem(
                            source_file=media.source_ref.source_file,
                            source_row=media.source_ref.source_row_number,
                            field="object_id",
                            value=media.object_id,
                        )
                    ],
                )
            )
        return findings
