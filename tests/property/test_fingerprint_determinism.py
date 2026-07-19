"""VL-02: fingerprint determinism, parametrized over every registered rule.

For each rule, the set of finding fingerprints produced on a dataset must be:
  1. identical across two identical runs, and
  2. invariant to the order of the input rows.

This test fails automatically when a new rule is added whose fingerprint depends on run order or
input order, which is exactly the mechanism VL-02 relies on to stay honest as the rule set grows.
"""

from __future__ import annotations

import random

import pytest

from collection_integrity.benchmark.injectors import inject_errors
from collection_integrity.benchmark.synthetic import generate_clean_objects
from collection_integrity.canonical.models import CollectionObject, SourceRef
from collection_integrity.rules.base import Rule, RuleContext
from collection_integrity.rules.registry import ALL_RULE_CLASSES

REQUIRED_FIELDS = ["accession_number", "object_name"]


def _rows_to_objects(rows: list[dict[str, str]]) -> list[CollectionObject]:
    objects: list[CollectionObject] = []
    for i, row in enumerate(rows, start=2):
        acc = (row.get("accession_number") or "").strip() or None
        objects.append(
            CollectionObject(
                object_id=row["object_id"],
                accession_number=acc,
                title=(row.get("title") or "").strip() or None,
                object_name=(row.get("object_name") or "").strip() or None,
                source_ref=SourceRef(
                    source_name="vl02",
                    source_file="vl02.csv",
                    source_record_id=row["object_id"],
                    source_row_number=i,
                    source_hash="x",
                    ingested_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
                ),
            )
        )
    return objects


def _dirty_objects() -> list[CollectionObject]:
    clean = generate_clean_objects(count=40, seed=7)
    dirty, _ = inject_errors(clean, seed=11, num_duplicate_accession=3, num_missing_field=3)
    return _rows_to_objects(dirty)


def _fingerprints(rule: Rule, objects: list[CollectionObject]) -> set[str]:
    ctx = RuleContext(objects=objects, required_fields=REQUIRED_FIELDS)
    return {f.fingerprint for f in rule.evaluate(ctx, rule.default_severity)}


@pytest.mark.parametrize("rule_cls", ALL_RULE_CLASSES, ids=lambda c: c().rule.id)
def test_fingerprints_stable_across_identical_runs(rule_cls: type[Rule]) -> None:
    objects = _dirty_objects()
    rule = rule_cls()

    assert _fingerprints(rule, objects) == _fingerprints(rule, objects)


@pytest.mark.parametrize("rule_cls", ALL_RULE_CLASSES, ids=lambda c: c().rule.id)
def test_fingerprints_invariant_to_input_order(rule_cls: type[Rule]) -> None:
    objects = _dirty_objects()
    shuffled = objects[:]
    random.Random(123).shuffle(shuffled)
    rule = rule_cls()

    assert _fingerprints(rule, objects) == _fingerprints(rule, shuffled)
