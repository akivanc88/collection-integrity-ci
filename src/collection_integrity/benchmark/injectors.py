"""Deterministic error injection for benchmarking (BUILD_BRIEF.md Section 16).

Takes a clean object table and introduces labeled errors, recording each in a manifest so a scan's
findings can be scored against ground truth. Injection is:

- deterministic by seed,
- non-mutating (the input rows are copied, never changed in place),
- disjoint (no row receives more than one injected error, so a label maps to exactly one rule),
- free of label leakage (no marker column is added; the manifest is stored separately).

Injectors exist for the currently implemented rules (CORE001, CORE002 on the objects table;
REF001 on the media table via `inject_orphan_media`). Injectors for the remaining Section 11 rules
land alongside those rules.
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
