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

from collection_integrity.benchmark.injectors import inject_errors, inject_orphan_media
from collection_integrity.benchmark.synthetic import generate_clean_media, generate_clean_objects
from collection_integrity.canonical.models import CollectionObject, MediaAsset, SourceRef
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


def _dirty_context() -> tuple[list[CollectionObject], list[MediaAsset]]:
    clean = generate_clean_objects(count=40, seed=7)
    dirty_objs, _ = inject_errors(clean, seed=11, num_duplicate_accession=3, num_missing_field=3)
    media = generate_clean_media(clean, seed=13)
    dirty_media, _ = inject_orphan_media(
        media, {o["object_id"] for o in clean}, seed=21, num_orphan=4
    )
    return _rows_to_objects(dirty_objs), _rows_to_media(dirty_media)


def _fingerprints(rule: Rule, objects: list[CollectionObject], media: list[MediaAsset]) -> set[str]:
    ctx = RuleContext(objects=objects, media=media, required_fields=REQUIRED_FIELDS)
    return {f.fingerprint for f in rule.evaluate(ctx, rule.default_severity)}


@pytest.mark.parametrize("rule_cls", ALL_RULE_CLASSES, ids=lambda c: c().rule.id)
def test_fingerprints_stable_across_identical_runs(rule_cls: type[Rule]) -> None:
    objects, media = _dirty_context()
    rule = rule_cls()

    assert _fingerprints(rule, objects, media) == _fingerprints(rule, objects, media)


@pytest.mark.parametrize("rule_cls", ALL_RULE_CLASSES, ids=lambda c: c().rule.id)
def test_fingerprints_invariant_to_input_order(rule_cls: type[Rule]) -> None:
    objects, media = _dirty_context()
    shuffled_objs, shuffled_media = objects[:], media[:]
    random.Random(123).shuffle(shuffled_objs)
    random.Random(456).shuffle(shuffled_media)
    rule = rule_cls()

    assert _fingerprints(rule, objects, media) == _fingerprints(rule, shuffled_objs, shuffled_media)


def test_ref001_actually_produces_findings_in_this_harness() -> None:
    # Guard: if the media harness ever stops producing orphans, the REF001 determinism cases above
    # would pass trivially. This asserts the harness genuinely exercises REF001.
    objects, media = _dirty_context()
    orphan_rule = next(c() for c in ALL_RULE_CLASSES if c().rule.id == "REF001_ORPHAN_MEDIA_OBJECT")
    assert len(_fingerprints(orphan_rule, objects, media)) == 4
