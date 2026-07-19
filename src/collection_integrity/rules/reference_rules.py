"""Referential-integrity rules (BUILD_BRIEF.md Section 11, items 4-5).

REF001 (orphan media -> object) and REF002 (orphan rights reference from an object or media
record) are implemented here.
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


class OrphanRightsReferenceRule(Rule):
    """REF002: an object or media record references a rights_id that does not exist."""

    rule = RuleRef(
        id="REF002_ORPHAN_RIGHTS_REFERENCE",
        name="Orphan rights reference",
        version="1.0.0",
    )
    default_severity: Severity = "high"

    def evaluate(self, ctx: RuleContext, severity: Severity) -> list[Finding]:
        rights_ids = {r.rights_id for r in ctx.rights}

        # (entity_type, entity_id, rights_id, source_ref) for every entity that names a rights id.
        referers: list[tuple[str, str, str, object]] = []
        for obj in ctx.objects:
            if obj.rights_id:
                referers.append(("object", obj.object_id, obj.rights_id, obj.source_ref))
        for media in ctx.media:
            if media.rights_id:
                referers.append(("media", media.media_id, media.rights_id, media.source_ref))

        findings: list[Finding] = []
        for entity_type, entity_id, rights_id, source_ref in sorted(
            referers, key=lambda r: (r[0], r[1])
        ):
            if rights_id in rights_ids:
                continue
            findings.append(
                self.make_finding(
                    severity=severity,
                    entity=EntityRef(type=entity_type, id=entity_id, field="rights_id"),
                    entity_id_for_fingerprint=entity_id,
                    evidence_keys=[rights_id],
                    summary=(
                        f"{entity_type.capitalize()} {entity_id} references rights record "
                        f"{rights_id!r}, which does not exist."
                    ),
                    explanation=(
                        f"{entity_type.capitalize()} {entity_id} has rights_id={rights_id!r}, but "
                        f"no rights record with that id is present in the rights entity."
                    ),
                    recommendation=(
                        "Correct the rights_id, restore the missing rights record, or clear the "
                        "reference according to institutional policy."
                    ),
                    evidence=[
                        EvidenceItem(
                            source_file=source_ref.source_file,  # type: ignore[attr-defined]
                            source_row=source_ref.source_row_number,  # type: ignore[attr-defined]
                            field="rights_id",
                            value=rights_id,
                        )
                    ],
                )
            )
        return findings
