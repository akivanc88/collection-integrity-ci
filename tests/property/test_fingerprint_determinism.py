"""VL-02: fingerprint determinism, parametrized over every registered rule.

For each rule, the set of finding fingerprints produced on a dataset must be:
  1. identical across two identical runs, and
  2. invariant to the order of the input rows.

The context carries both objects and media, each seeded with the errors the current rules detect,
so every rule actually produces findings here. This test fails automatically when a new rule is
added whose fingerprint depends on run order or input order — the mechanism VL-02 relies on to stay
honest as the rule set grows.
"""

from __future__ import annotations

import random

import pytest

from collection_integrity.benchmark.injectors import (
    inject_errors,
    inject_extra_current_location,
    inject_location_hierarchy_errors,
    inject_orphan_media,
    inject_orphan_rights,
    inject_publication_conflict,
)
from collection_integrity.benchmark.synthetic import (
    generate_clean_locations,
    generate_clean_media,
    generate_clean_objects,
    generate_clean_rights,
    link_objects_to_rights,
    rights_permits_publication,
)
from collection_integrity.canonical.models import (
    CollectionObject,
    LocationRecord,
    MediaAsset,
    RightsRecord,
    SourceRef,
)
from collection_integrity.rules.base import Rule, RuleContext
from collection_integrity.rules.registry import ALL_RULE_CLASSES

REQUIRED_FIELDS = ["accession_number", "object_name"]


def _ref(rid: str) -> SourceRef:
    return SourceRef(
        source_name="vl02",
        source_file="vl02.csv",
        source_record_id=rid,
        source_hash="x",
        ingested_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
    )


def _rows_to_objects(rows: list[dict[str, str]]) -> list[CollectionObject]:
    return [
        CollectionObject(
            object_id=row["object_id"],
            accession_number=(row.get("accession_number") or "").strip() or None,
            title=(row.get("title") or "").strip() or None,
            object_name=(row.get("object_name") or "").strip() or None,
            rights_id=(row.get("rights_id") or "").strip() or None,
            publication_status=(row.get("publication_status") or "").strip() or None,
            source_ref=_ref(row["object_id"]),
        )
        for row in rows
    ]


def _rows_to_media(rows: list[dict[str, str]]) -> list[MediaAsset]:
    return [
        MediaAsset(
            media_id=row["media_id"],
            object_id=(row.get("object_id") or "").strip() or None,
            source_ref=_ref(row["media_id"]),
        )
        for row in rows
    ]


def _rows_to_rights(rows: list[dict[str, str]]) -> list[RightsRecord]:
    return [
        RightsRecord(
            rights_id=row["rights_id"],
            rights_status=(row.get("rights_status") or "").strip() or None,
            publication_allowed=row.get("publication_allowed", "").strip().lower() == "true",
            review_required=row.get("review_required", "").strip().lower() == "true",
            source_ref=_ref(row["rights_id"]),
        )
        for row in rows
    ]


def _rows_to_locations(rows: list[dict[str, str]]) -> list[LocationRecord]:
    return [
        LocationRecord(
            location_id=row["location_id"],
            name=(row.get("name") or "").strip() or None,
            parent_location_id=(row.get("parent_location_id") or "").strip() or None,
            object_id=(row.get("object_id") or "").strip() or None,
            is_current=row.get("is_current", "").strip().lower() == "true",
            source_ref=_ref(row["location_id"]),
        )
        for row in rows
    ]


def _dirty_context() -> tuple[
    list[CollectionObject], list[MediaAsset], list[RightsRecord], list[LocationRecord]
]:
    clean = generate_clean_objects(count=40, seed=7)
    dirty_objs, _ = inject_errors(clean, seed=11, num_duplicate_accession=3, num_missing_field=3)

    rights = generate_clean_rights(count=16, seed=9)
    restricted = {r["rights_id"] for r in rights if not rights_permits_publication(r)}
    valid_rights = {r["rights_id"] for r in rights}
    # Re-link the (corrupted) objects to rights, then inject rights errors so REF002/RIGHTS001 fire.
    linked = link_objects_to_rights(dirty_objs, rights, seed=15)
    linked, _ = inject_orphan_rights(linked, valid_rights, seed=31, num_orphan=3)
    linked, _ = inject_publication_conflict(linked, restricted, seed=41, num_conflict=3)

    media = generate_clean_media(clean, seed=13)
    dirty_media, _ = inject_orphan_media(
        media, {o["object_id"] for o in clean}, seed=21, num_orphan=4
    )

    locations = generate_clean_locations(clean, num_nodes=15, seed=17)
    locations, _ = inject_extra_current_location(locations, seed=23, num_extra=3)
    locations, _ = inject_location_hierarchy_errors(
        locations, seed=29, num_missing_parent=2, num_cycle=1
    )

    return (
        _rows_to_objects(linked),
        _rows_to_media(dirty_media),
        _rows_to_rights(rights),
        _rows_to_locations(locations),
    )


def _fingerprints(
    rule: Rule,
    objects: list[CollectionObject],
    media: list[MediaAsset],
    rights: list[RightsRecord],
    locations: list[LocationRecord],
) -> set[str]:
    ctx = RuleContext(
        objects=objects,
        media=media,
        rights=rights,
        locations=locations,
        required_fields=REQUIRED_FIELDS,
    )
    return {f.fingerprint for f in rule.evaluate(ctx, rule.default_severity)}


@pytest.mark.parametrize("rule_cls", ALL_RULE_CLASSES, ids=lambda c: c().rule.id)
def test_fingerprints_stable_across_identical_runs(rule_cls: type[Rule]) -> None:
    objects, media, rights, locations = _dirty_context()
    rule = rule_cls()

    assert _fingerprints(rule, objects, media, rights, locations) == _fingerprints(
        rule, objects, media, rights, locations
    )


@pytest.mark.parametrize("rule_cls", ALL_RULE_CLASSES, ids=lambda c: c().rule.id)
def test_fingerprints_invariant_to_input_order(rule_cls: type[Rule]) -> None:
    objects, media, rights, locations = _dirty_context()
    s_objs, s_media, s_rights, s_locs = objects[:], media[:], rights[:], locations[:]
    random.Random(123).shuffle(s_objs)
    random.Random(456).shuffle(s_media)
    random.Random(789).shuffle(s_rights)
    random.Random(101).shuffle(s_locs)
    rule = rule_cls()

    assert _fingerprints(rule, objects, media, rights, locations) == _fingerprints(
        rule, s_objs, s_media, s_rights, s_locs
    )


@pytest.mark.parametrize(
    "rule_id,expected_count",
    [
        ("REF001_ORPHAN_MEDIA_OBJECT", 4),
        ("REF002_ORPHAN_RIGHTS_REFERENCE", 3),
        ("RIGHTS001_PUBLICATION_CONFLICT", 3),
        ("LOC001_MULTIPLE_CURRENT_LOCATIONS", 3),
        ("LOC002_INVALID_LOCATION_HIERARCHY", 4),
    ],
)
def test_harness_actually_exercises_each_rule(rule_id: str, expected_count: int) -> None:
    # Guard: if the harness ever stops producing findings for these rules, their determinism cases
    # above would pass trivially. This asserts the harness genuinely exercises them.
    objects, media, rights, locations = _dirty_context()
    rule = next(c() for c in ALL_RULE_CLASSES if c().rule.id == rule_id)
    assert len(_fingerprints(rule, objects, media, rights, locations)) == expected_count
