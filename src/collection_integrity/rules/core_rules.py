"""Core structural rules (BUILD_BRIEF.md Section 11, items 1-2).

Only CORE001 is implemented for the first vertical slice. CORE002 (required field missing) and
the rule registry/base class that will eventually dispatch to modules like this one are tracked in
docs/BACKLOG.md for Phase 2.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime

from collection_integrity.canonical.models import CollectionObject
from collection_integrity.engine.findings import (
    EntityRef,
    EvidenceItem,
    Finding,
    RuleRef,
    compute_fingerprint,
)

CORE001_RULE = RuleRef(
    id="CORE001_DUPLICATE_ACCESSION_NUMBER",
    name="Duplicate accession number",
    version="1.0.0",
)


def check_duplicate_accession_numbers(objects: list[CollectionObject]) -> list[Finding]:
    """Detect duplicate non-empty accession numbers.

    Whitespace-only accession numbers are already normalized to None by the ingestion adapter and
    are therefore excluded, matching "duplicate non-empty accession numbers" in the brief.
    """
    by_accession: dict[str, list[CollectionObject]] = defaultdict(list)
    for obj in objects:
        if obj.accession_number:
            by_accession[obj.accession_number].append(obj)

    findings: list[Finding] = []
    for accession_number, group in by_accession.items():
        if len(group) < 2:
            continue

        object_ids = sorted(o.object_id for o in group)
        evidence = [
            EvidenceItem(
                source_file=o.source_ref.source_file,
                source_row=o.source_ref.source_row_number,
                field="accession_number",
                value=o.accession_number,
            )
            for o in sorted(group, key=lambda o: o.object_id)
        ]

        findings.append(
            Finding(
                finding_id=str(uuid.uuid4()),
                fingerprint=compute_fingerprint(
                    rule_id=CORE001_RULE.id,
                    entity_type="object",
                    entity_id=accession_number,
                    field="accession_number",
                    evidence_keys=object_ids,
                ),
                rule=CORE001_RULE,
                severity="critical",
                verification_type="deterministic",
                entity=EntityRef(type="object", id=accession_number, field="accession_number"),
                summary=f"Accession number {accession_number!r} is used by {len(group)} objects.",
                explanation=(
                    f"Objects {', '.join(object_ids)} all have accession_number="
                    f"{accession_number!r}. Accession numbers must uniquely identify one object."
                ),
                evidence=evidence,
                recommendation=(
                    "Confirm which object legitimately holds this accession number and correct "
                    "or reassign the others according to institutional policy."
                ),
                confidence=1.0,
                created_at=datetime.now(UTC),
            )
        )
    return findings
