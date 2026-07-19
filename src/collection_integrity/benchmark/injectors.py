"""Deterministic error injection for benchmarking (BUILD_BRIEF.md Section 16).

Takes a clean object table and introduces labeled errors, recording each in a manifest so a scan's
findings can be scored against ground truth. Injection is:

- deterministic by seed,
- non-mutating (the input rows are copied, never changed in place),
- disjoint (no row receives more than one injected error, so a label maps to exactly one rule),
- free of label leakage (no marker column is added; the manifest is stored separately).

Injectors exist for the currently implemented rules: CORE001/CORE002 on objects (`inject_errors`),
REF001 on media (`inject_orphan_media`), and REF002/RIGHTS001 on objects (`inject_orphan_rights`,
`inject_publication_conflict`). Injectors for the remaining Section 11 rules land alongside them.
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field


@dataclass(frozen=True)
class InjectedError:
    error_id: str
    expected_rule_id: str
    entity_type: str
    entity_id: str
    field: str
    before_value: str
    after_value: str


@dataclass
class InjectionManifest:
    seed: int
    errors: list[InjectedError] = field(default_factory=list)

    def expected_core001_accessions(self) -> set[str]:
        """Accession values a correct CORE001 run must flag (one finding per value)."""
        return {
            e.after_value
            for e in self.errors
            if e.expected_rule_id == "CORE001_DUPLICATE_ACCESSION_NUMBER"
        }

    def expected_core002_keys(self) -> set[tuple[str, str]]:
        """(object_id, field) pairs a correct CORE002 run must flag."""
        return {
            (e.entity_id, e.field)
            for e in self.errors
            if e.expected_rule_id == "CORE002_REQUIRED_FIELD_MISSING"
        }

    def expected_ref001_media(self) -> set[str]:
        """media_ids a correct REF001 run must flag as orphaned."""
        return {
            e.entity_id for e in self.errors if e.expected_rule_id == "REF001_ORPHAN_MEDIA_OBJECT"
        }

    def expected_ref002_ids(self) -> set[str]:
        """entity ids a correct REF002 run must flag as having an orphan rights reference."""
        return {
            e.entity_id
            for e in self.errors
            if e.expected_rule_id == "REF002_ORPHAN_RIGHTS_REFERENCE"
        }

    def expected_rights001_ids(self) -> set[str]:
        """entity ids a correct RIGHTS001 run must flag as a publication conflict."""
        rid = "RIGHTS001_PUBLICATION_CONFLICT"
        return {e.entity_id for e in self.errors if e.expected_rule_id == rid}

    def expected_loc001_ids(self) -> set[str]:
        """object ids a correct LOC001 run must flag as having multiple current locations."""
        rid = "LOC001_MULTIPLE_CURRENT_LOCATIONS"
        return {e.entity_id for e in self.errors if e.expected_rule_id == rid}

    def expected_loc002_ids(self) -> set[str]:
        """location ids a correct LOC002 run must flag (missing parent or cycle)."""
        rid = "LOC002_INVALID_LOCATION_HIERARCHY"
        return {e.entity_id for e in self.errors if e.expected_rule_id == rid}


def inject_errors(
    clean_rows: list[dict[str, str]],
    seed: int,
    num_duplicate_accession: int = 3,
    num_missing_field: int = 3,
) -> tuple[list[dict[str, str]], InjectionManifest]:
    """Return a corrupted copy of `clean_rows` and a manifest of what was injected.

    The input list and its dicts are never modified.
    """
    needed = num_duplicate_accession * 2 + num_missing_field
    if needed > len(clean_rows):
        raise ValueError(
            f"Need at least {needed} rows to inject {num_duplicate_accession} duplicate-accession "
            f"and {num_missing_field} missing-field errors, got {len(clean_rows)}"
        )

    rows = copy.deepcopy(clean_rows)
    rng = random.Random(seed)

    # Choose disjoint row indices up front so no row gets two injected errors.
    indices = list(range(len(rows)))
    rng.shuffle(indices)
    pool = iter(indices)

    manifest = InjectionManifest(seed=seed)

    # CORE001: copy a source row's accession onto a distinct target row, creating a duplicate.
    for n in range(num_duplicate_accession):
        source_idx = next(pool)
        target_idx = next(pool)
        duplicated = rows[source_idx]["accession_number"]
        before = rows[target_idx]["accession_number"]
        rows[target_idx]["accession_number"] = duplicated
        manifest.errors.append(
            InjectedError(
                error_id=f"DUP-ACC-{n + 1}",
                expected_rule_id="CORE001_DUPLICATE_ACCESSION_NUMBER",
                entity_type="object",
                entity_id=rows[target_idx]["object_id"],
                field="accession_number",
                before_value=before,
                after_value=duplicated,
            )
        )

    # CORE002: blank a required field. Alternate between accession_number and object_name.
    missing_fields = ("accession_number", "object_name")
    for n in range(num_missing_field):
        idx = next(pool)
        target_field = missing_fields[n % len(missing_fields)]
        before = rows[idx][target_field]
        rows[idx][target_field] = ""
        manifest.errors.append(
            InjectedError(
                error_id=f"MISSING-{n + 1}",
                expected_rule_id="CORE002_REQUIRED_FIELD_MISSING",
                entity_type="object",
                entity_id=rows[idx]["object_id"],
                field=target_field,
                before_value=before,
                after_value="",
            )
        )

    return rows, manifest


def inject_orphan_media(
    clean_media: list[dict[str, str]],
    valid_object_ids: set[str],
    seed: int,
    num_orphan: int = 3,
) -> tuple[list[dict[str, str]], list[InjectedError]]:
    """Repoint some media rows at non-existent object ids, returning corrupted rows + labels.

    Non-mutating: the input list and its dicts are copied. Orphan target ids are synthesised to be
    absent from `valid_object_ids`, so REF001 (and only REF001) should flag exactly these rows.
    """
    if num_orphan > len(clean_media):
        raise ValueError(f"need at least {num_orphan} media rows, got {len(clean_media)}")

    rows = copy.deepcopy(clean_media)
    rng = random.Random(seed)
    indices = list(range(len(rows)))
    rng.shuffle(indices)

    errors: list[InjectedError] = []
    for n in range(num_orphan):
        idx = indices[n]
        before = rows[idx]["object_id"]
        # A target id guaranteed not to exist among the real objects.
        bogus = f"MISSING-OBJ-{n + 1}"
        assert bogus not in valid_object_ids
        rows[idx]["object_id"] = bogus
        errors.append(
            InjectedError(
                error_id=f"ORPHAN-MEDIA-{n + 1}",
                expected_rule_id="REF001_ORPHAN_MEDIA_OBJECT",
                entity_type="media",
                entity_id=rows[idx]["media_id"],
                field="object_id",
                before_value=before,
                after_value=bogus,
            )
        )
    return rows, errors


def inject_orphan_rights(
    object_rows: list[dict[str, str]],
    valid_rights_ids: set[str],
    seed: int,
    num_orphan: int = 3,
) -> tuple[list[dict[str, str]], list[InjectedError]]:
    """Repoint some objects' rights_id at non-existent rights records (REF002). Non-mutating."""
    if num_orphan > len(object_rows):
        raise ValueError(f"need at least {num_orphan} object rows, got {len(object_rows)}")

    rows = copy.deepcopy(object_rows)
    rng = random.Random(seed)
    indices = list(range(len(rows)))
    rng.shuffle(indices)

    errors: list[InjectedError] = []
    for n in range(num_orphan):
        idx = indices[n]
        before = rows[idx].get("rights_id", "")
        bogus = f"MISSING-RIGHTS-{n + 1}"
        assert bogus not in valid_rights_ids
        rows[idx]["rights_id"] = bogus
        errors.append(
            InjectedError(
                error_id=f"ORPHAN-RIGHTS-{n + 1}",
                expected_rule_id="REF002_ORPHAN_RIGHTS_REFERENCE",
                entity_type="object",
                entity_id=rows[idx]["object_id"],
                field="rights_id",
                before_value=before,
                after_value=bogus,
            )
        )
    return rows, errors


def inject_publication_conflict(
    object_rows: list[dict[str, str]],
    restricted_rights_ids: set[str],
    seed: int,
    num_conflict: int = 3,
) -> tuple[list[dict[str, str]], list[InjectedError]]:
    """Flip some non-public objects linked to restricted rights to ``public`` (RIGHTS001).

    Non-mutating. Only objects currently linked to a restricted rights record and not already
    public are eligible, so each injected error is a genuine, isolated publication conflict.
    """
    rows = copy.deepcopy(object_rows)
    rng = random.Random(seed)

    eligible = [
        i
        for i, r in enumerate(rows)
        if r.get("rights_id") in restricted_rights_ids
        and r.get("publication_status", "").strip().lower() != "public"
    ]
    if num_conflict > len(eligible):
        raise ValueError(
            f"need at least {num_conflict} eligible objects (restricted, non-public), "
            f"got {len(eligible)}"
        )
    rng.shuffle(eligible)

    errors: list[InjectedError] = []
    for n in range(num_conflict):
        idx = eligible[n]
        before = rows[idx].get("publication_status", "")
        rows[idx]["publication_status"] = "public"
        errors.append(
            InjectedError(
                error_id=f"PUB-CONFLICT-{n + 1}",
                expected_rule_id="RIGHTS001_PUBLICATION_CONFLICT",
                entity_type="object",
                entity_id=rows[idx]["object_id"],
                field="publication_status",
                before_value=before,
                after_value="public",
            )
        )
    return rows, errors


def inject_extra_current_location(
    location_rows: list[dict[str, str]],
    seed: int,
    num_extra: int = 3,
) -> tuple[list[dict[str, str]], list[InjectedError]]:
    """Add a second current assignment for some objects (LOC001). Non-mutating (appends rows)."""
    rows = copy.deepcopy(location_rows)
    rng = random.Random(seed)

    assigned_objects = sorted(
        {r["object_id"] for r in rows if r.get("object_id") and r.get("is_current") == "true"}
    )
    if num_extra > len(assigned_objects):
        raise ValueError(f"need at least {num_extra} assigned objects, got {len(assigned_objects)}")
    rng.shuffle(assigned_objects)

    errors: list[InjectedError] = []
    for n in range(num_extra):
        object_id = assigned_objects[n]
        rows.append(
            {
                "location_id": f"EXTRA-ASG-{n + 1}",
                "name": "",
                "parent_location_id": "",
                "object_id": object_id,
                "is_current": "true",
            }
        )
        errors.append(
            InjectedError(
                error_id=f"MULTI-CURRENT-{n + 1}",
                expected_rule_id="LOC001_MULTIPLE_CURRENT_LOCATIONS",
                entity_type="object",
                entity_id=object_id,
                field="is_current",
                before_value="1 current",
                after_value="2 current",
            )
        )
    return rows, errors


def inject_location_hierarchy_errors(
    location_rows: list[dict[str, str]],
    seed: int,
    num_missing_parent: int = 2,
    num_cycle: int = 1,
) -> tuple[list[dict[str, str]], list[InjectedError]]:
    """Introduce missing-parent and cycle errors into the hierarchy (LOC002). Non-mutating.

    Missing-parent: repoint a node's parent at a synthesised non-existent id.
    Cycle: pick two distinct nodes and point them at each other (a 2-cycle), flagging both.
    """
    rows = copy.deepcopy(location_rows)
    rng = random.Random(seed)

    node_idx = [i for i, r in enumerate(rows) if not r.get("object_id")]
    if num_missing_parent + num_cycle * 2 > len(node_idx):
        raise ValueError("not enough hierarchy nodes to inject the requested errors")
    rng.shuffle(node_idx)
    pool = iter(node_idx)

    errors: list[InjectedError] = []

    for n in range(num_missing_parent):
        idx = next(pool)
        bogus = f"MISSING-LOC-{n + 1}"
        rows[idx]["parent_location_id"] = bogus
        errors.append(
            InjectedError(
                error_id=f"MISSING-PARENT-{n + 1}",
                expected_rule_id="LOC002_INVALID_LOCATION_HIERARCHY",
                entity_type="location",
                entity_id=rows[idx]["location_id"],
                field="parent_location_id",
                before_value="",
                after_value=bogus,
            )
        )

    for n in range(num_cycle):
        a_idx = next(pool)
        b_idx = next(pool)
        a_id = rows[a_idx]["location_id"]
        b_id = rows[b_idx]["location_id"]
        rows[a_idx]["parent_location_id"] = b_id
        rows[b_idx]["parent_location_id"] = a_id
        for loc_id in (a_id, b_id):
            errors.append(
                InjectedError(
                    error_id=f"CYCLE-{n + 1}-{loc_id}",
                    expected_rule_id="LOC002_INVALID_LOCATION_HIERARCHY",
                    entity_type="location",
                    entity_id=loc_id,
                    field="parent_location_id",
                    before_value="",
                    after_value="cycle",
                )
            )
    return rows, errors
