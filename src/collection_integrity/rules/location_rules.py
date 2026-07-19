"""Location rules (BUILD_BRIEF.md Section 11, items 6-7).

LOC001 flags an object with more than one location assignment marked current. LOC002 flags an
invalid location hierarchy: a parent that does not exist, or a cycle in the parent chain.

Location rows are dual-purpose (see LocationRecord): a row with an object_id + is_current is an
assignment (LOC001's input), and a row with a location_id + parent_location_id is a hierarchy node
(LOC002's input). A row may be both.
"""

from __future__ import annotations

from collections import defaultdict

from collection_integrity.canonical.models import LocationRecord
from collection_integrity.engine.findings import (
    EntityRef,
    EvidenceItem,
    Finding,
    RuleRef,
    Severity,
)
from collection_integrity.rules.base import Rule, RuleContext


class MultipleCurrentLocationsRule(Rule):
    """LOC001: an object is assigned more than one current location."""

    rule = RuleRef(
        id="LOC001_MULTIPLE_CURRENT_LOCATIONS",
        name="Multiple current locations",
        version="1.0.0",
    )
    default_severity: Severity = "high"

    def evaluate(self, ctx: RuleContext, severity: Severity) -> list[Finding]:
        current_by_object: dict[str, list[LocationRecord]] = defaultdict(list)
        for loc in ctx.locations:
            if loc.object_id and loc.is_current is True:
                current_by_object[loc.object_id].append(loc)

        findings: list[Finding] = []
        for object_id, assignments in sorted(current_by_object.items()):
            if len(assignments) < 2:
                continue
            ordered = sorted(assignments, key=lambda a: a.location_id)
            location_ids = [a.location_id for a in ordered]
            findings.append(
                self.make_finding(
                    severity=severity,
                    entity=EntityRef(type="object", id=object_id, field="current_location_id"),
                    entity_id_for_fingerprint=object_id,
                    evidence_keys=location_ids,
                    summary=(
                        f"Object {object_id} is marked current at {len(assignments)} locations "
                        f"({', '.join(location_ids)})."
                    ),
                    explanation=(
                        f"Object {object_id} has {len(assignments)} location assignments marked "
                        f"current: {', '.join(location_ids)}. The profile requires a single "
                        f"current location."
                    ),
                    recommendation=(
                        "Resolve which location is current and clear is_current on the others."
                    ),
                    evidence=[
                        EvidenceItem(
                            source_file=a.source_ref.source_file,
                            source_row=a.source_ref.source_row_number,
                            field="is_current",
                            value=a.location_id,
                        )
                        for a in ordered
                    ],
                )
            )
        return findings


class InvalidLocationHierarchyRule(Rule):
    """LOC002: a location has a missing parent or sits in a parent-chain cycle."""

    rule = RuleRef(
        id="LOC002_INVALID_LOCATION_HIERARCHY",
        name="Invalid location hierarchy",
        version="1.0.0",
    )
    default_severity: Severity = "medium"

    def evaluate(self, ctx: RuleContext, severity: Severity) -> list[Finding]:
        # Deduplicate hierarchy nodes by location_id (assignment rows may repeat a location_id).
        parent_of: dict[str, str | None] = {}
        node_ref: dict[str, LocationRecord] = {}
        for loc in ctx.locations:
            if loc.location_id not in node_ref:
                node_ref[loc.location_id] = loc
                parent_of[loc.location_id] = loc.parent_location_id or None
            elif loc.parent_location_id and parent_of.get(loc.location_id) is None:
                parent_of[loc.location_id] = loc.parent_location_id

        known = set(parent_of)
        findings: list[Finding] = []

        # Missing parents.
        for location_id in sorted(known):
            parent = parent_of[location_id]
            if parent is not None and parent not in known:
                loc = node_ref[location_id]
                findings.append(
                    self._finding(
                        severity,
                        location_id,
                        loc,
                        summary=(
                            f"Location {location_id} references parent {parent!r}, which does not "
                            f"exist."
                        ),
                        explanation=(
                            f"Location {location_id} has parent_location_id={parent!r}, but no "
                            f"location with that id is present."
                        ),
                        field="parent_location_id",
                        value=parent,
                        evidence_key=f"missing:{parent}",
                    )
                )

        # Cycles: each node whose parent chain loops back onto itself.
        for location_id in sorted(known):
            if self._in_cycle(location_id, parent_of, known):
                loc = node_ref[location_id]
                findings.append(
                    self._finding(
                        severity,
                        location_id,
                        loc,
                        summary=f"Location {location_id} is part of a parent-chain cycle.",
                        explanation=(
                            f"Following parent_location_id from {location_id} eventually returns "
                            f"to {location_id}; the location hierarchy contains a cycle."
                        ),
                        field="parent_location_id",
                        value=parent_of[location_id],
                        evidence_key="cycle",
                    )
                )
        return findings

    @staticmethod
    def _in_cycle(start: str, parent_of: dict[str, str | None], known: set[str]) -> bool:
        """True only when `start` itself lies on a cycle (its parent chain returns to it)."""
        node = parent_of.get(start)
        seen: set[str] = set()
        while node is not None and node in known:
            if node == start:
                return True
            if node in seen:
                # A cycle exists further up the chain but does not include `start`.
                return False
            seen.add(node)
            node = parent_of.get(node)
        return False

    def _finding(
        self,
        severity: Severity,
        location_id: str,
        loc: LocationRecord,
        *,
        summary: str,
        explanation: str,
        field: str,
        value: str | None,
        evidence_key: str,
    ) -> Finding:
        return self.make_finding(
            severity=severity,
            entity=EntityRef(type="location", id=location_id, field="parent_location_id"),
            entity_id_for_fingerprint=location_id,
            evidence_keys=[evidence_key],
            summary=summary,
            explanation=explanation,
            recommendation=(
                "Correct the parent_location_id, add the missing parent location, or break the "
                "cycle so the hierarchy forms a tree."
            ),
            evidence=[
                EvidenceItem(
                    source_file=loc.source_ref.source_file,
                    source_row=loc.source_ref.source_row_number,
                    field=field,
                    value=value,
                )
            ],
        )
