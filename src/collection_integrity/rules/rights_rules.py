"""Rights-policy rules (BUILD_BRIEF.md Section 11, item 8).

RIGHTS001 is a policy-consistency check, not legal advice: it flags an entity marked for public
release whose linked rights record does not clearly permit publication. It deliberately does not
fire when the rights reference is missing entirely — that is REF002's job — so an entity is never
double-reported for the same underlying problem.
"""

from __future__ import annotations

from collection_integrity.canonical.models import RightsRecord
from collection_integrity.engine.findings import (
    EntityRef,
    EvidenceItem,
    Finding,
    RuleRef,
    Severity,
)
from collection_integrity.rules.base import Rule, RuleContext

# Publication-status values that mean "released to the public".
PUBLIC_VALUES = frozenset({"public"})
# rights_status values that do not clearly permit publication.
NON_PERMISSIVE_STATUS = frozenset({"restricted", "unknown", "review_required"})


def _permits_publication(rights: RightsRecord) -> bool:
    """A rights record permits publication only when it says so unambiguously."""
    if rights.publication_allowed is not True:
        return False
    if rights.review_required is True:
        return False
    if rights.rights_status is not None and rights.rights_status.lower() in NON_PERMISSIVE_STATUS:
        return False
    return True


class PublicationRightsConflictRule(Rule):
    """RIGHTS001: a public entity is linked to rights that do not permit publication."""

    rule = RuleRef(
        id="RIGHTS001_PUBLICATION_CONFLICT",
        name="Publication rights conflict",
        version="1.0.0",
    )
    default_severity: Severity = "critical"

    def evaluate(self, ctx: RuleContext, severity: Severity) -> list[Finding]:
        rights_by_id = {r.rights_id: r for r in ctx.rights}

        rows: list[tuple[str, str, str | None, str | None, object]] = []
        for obj in ctx.objects:
            rows.append(
                ("object", obj.object_id, obj.publication_status, obj.rights_id, obj.source_ref)
            )
        for med in ctx.media:
            rows.append(
                ("media", med.media_id, med.publication_status, med.rights_id, med.source_ref)
            )

        findings: list[Finding] = []
        for entity_type, entity_id, pub_status, rights_id, source_ref in sorted(
            rows, key=lambda r: (r[0], r[1])
        ):
            if pub_status is None or pub_status.lower() not in PUBLIC_VALUES:
                continue
            if not rights_id:
                continue
            rights = rights_by_id.get(rights_id)
            # A missing rights record is REF002's concern, not RIGHTS001's.
            if rights is None or _permits_publication(rights):
                continue

            findings.append(
                self.make_finding(
                    severity=severity,
                    entity=EntityRef(type=entity_type, id=entity_id, field="publication_status"),
                    entity_id_for_fingerprint=entity_id,
                    evidence_keys=[rights_id],
                    summary=(
                        f"{entity_type.capitalize()} {entity_id} is public but its rights record "
                        f"{rights_id!r} does not permit publication."
                    ),
                    explanation=(
                        f"{entity_type.capitalize()} {entity_id} has publication_status="
                        f"{pub_status!r} while rights record {rights_id!r} has "
                        f"publication_allowed={rights.publication_allowed!r}, "
                        f"review_required={rights.review_required!r}, "
                        f"rights_status={rights.rights_status!r}. This is a policy conflict, not a "
                        f"legal determination."
                    ),
                    recommendation=(
                        "Send the record for rights review, or change the publication status to "
                        "match the rights record, according to institutional policy."
                    ),
                    evidence=[
                        EvidenceItem(
                            source_file=source_ref.source_file,  # type: ignore[attr-defined]
                            source_row=source_ref.source_row_number,  # type: ignore[attr-defined]
                            field="publication_status",
                            value=pub_status,
                        ),
                        EvidenceItem(
                            source_file=rights.source_ref.source_file,
                            source_row=rights.source_ref.source_row_number,
                            field="publication_allowed",
                            value=rights.publication_allowed,
                        ),
                    ],
                )
            )
        return findings
