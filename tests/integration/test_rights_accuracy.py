"""Slice D accuracy validation: REF002 and RIGHTS001 on AI-generated rights-linked data.

Generates objects linked to a mix of permissive/restricted rights (clean = no conflicts, no
orphans), then injects orphan rights references and publication conflicts and confirms both rules
recover exactly the injected errors at precision = recall = 1.0.
"""

from pathlib import Path

from collection_integrity.benchmark.dataset import write_objects_csv
from collection_integrity.benchmark.injectors import (
    InjectionManifest,
    inject_orphan_rights,
    inject_publication_conflict,
)
from collection_integrity.benchmark.metrics import score
from collection_integrity.benchmark.synthetic import (
    OBJECT_WITH_RIGHTS_COLUMNS,
    RIGHTS_COLUMNS,
    generate_clean_objects,
    generate_clean_rights,
    link_objects_to_rights,
    rights_permits_publication,
)
from collection_integrity.ingestion.mapper import load_mapping, load_objects, load_rights
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.registry import RuleRegistry

MAPPING = """version: 1
dataset:
  name: bench-rights
  format: csv
  base_path: .
entities:
  objects:
    file: objects.csv
    primary_key: object_id
    fields:
      object_id: object_id
      accession_number: accession_number
      object_name: object_name
      title: title
      rights_id: rights_id
      publication_status: publication_status
  rights:
    file: rights.csv
    primary_key: rights_id
    fields:
      rights_id: rights_id
      rights_status: rights_status
      publication_allowed: publication_allowed
      review_required: review_required
"""


def _build(tmp_path: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], set[str]]:
    base_objects = generate_clean_objects(count=60, seed=7)
    rights = generate_clean_rights(count=20, seed=9)
    linked = link_objects_to_rights(base_objects, rights, seed=15)
    restricted = {r["rights_id"] for r in rights if not rights_permits_publication(r)}
    write_objects_csv(rights, tmp_path / "rights.csv", RIGHTS_COLUMNS)
    return linked, rights, restricted


def _scan(tmp_path: Path, objects: list[dict[str, str]]) -> list:  # type: ignore[type-arg]
    write_objects_csv(objects, tmp_path / "objects.csv", OBJECT_WITH_RIGHTS_COLUMNS)
    (tmp_path / "map.yaml").write_text(MAPPING, encoding="utf-8")
    mapping = load_mapping(tmp_path / "map.yaml")
    ctx = RuleContext(
        objects=load_objects(mapping, base_dir=tmp_path),
        rights=load_rights(mapping, base_dir=tmp_path),
        required_fields=["accession_number", "object_name"],
    )
    return RuleRegistry.with_defaults().evaluate(ctx)


def test_clean_rights_linked_data_has_no_ref002_or_rights001(tmp_path: Path) -> None:
    linked, _rights, _restricted = _build(tmp_path)

    findings = _scan(tmp_path, linked)

    offending = [
        f
        for f in findings
        if f.rule.id in {"REF002_ORPHAN_RIGHTS_REFERENCE", "RIGHTS001_PUBLICATION_CONFLICT"}
    ]
    assert offending == [], [f.summary for f in offending]


def test_injected_rights_errors_detected_with_perfect_precision_recall(tmp_path: Path) -> None:
    linked, rights, restricted = _build(tmp_path)
    valid_rights_ids = {r["rights_id"] for r in rights}

    dirty, orphan_errors = inject_orphan_rights(linked, valid_rights_ids, seed=31, num_orphan=5)
    dirty, conflict_errors = inject_publication_conflict(dirty, restricted, seed=41, num_conflict=5)
    manifest = InjectionManifest(seed=31, errors=orphan_errors + conflict_errors)

    findings = _scan(tmp_path, dirty)
    metrics = score(findings, manifest)

    for rule_id in ("REF002_ORPHAN_RIGHTS_REFERENCE", "RIGHTS001_PUBLICATION_CONFLICT"):
        m = metrics[rule_id]
        assert m.precision == 1.0, (rule_id, m)
        assert m.recall == 1.0, (rule_id, m)
        assert m.true_positives == 5, (rule_id, m)
