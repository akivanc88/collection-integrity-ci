"""Slice F accuracy validation: DATE001, VOCAB001, SCHEMA001 on AI-generated object data.

Generates objects with valid production dates and in-vocabulary statuses (clean = no findings),
then injects inverted date ranges, out-of-vocabulary values, and unparseable dates and confirms
each rule recovers exactly its injected errors at precision = recall = 1.0.
"""

from pathlib import Path

from collection_integrity.benchmark.dataset import write_objects_csv
from collection_integrity.benchmark.injectors import InjectionManifest, inject_object_field_errors
from collection_integrity.benchmark.metrics import score
from collection_integrity.benchmark.synthetic import (
    OBJECT_WITH_DATES_COLUMNS,
    PUBLICATION_VOCABULARY,
    add_dates_and_status,
    generate_clean_objects,
)
from collection_integrity.ingestion.mapper import (
    load_mapping,
    load_objects,
    object_field_sources,
)
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.registry import RuleRegistry

MAPPING = """version: 1
dataset:
  name: bench-object-fields
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
      publication_status: publication_status
      production_start_date: production_start_date
      production_end_date: production_end_date
"""

VOCAB = {"publication_status": PUBLICATION_VOCABULARY}


def _scan(tmp_path: Path, objects: list) -> list:  # type: ignore[type-arg]
    write_objects_csv(objects, tmp_path / "objects.csv", OBJECT_WITH_DATES_COLUMNS)
    (tmp_path / "map.yaml").write_text(MAPPING, encoding="utf-8")
    mapping = load_mapping(tmp_path / "map.yaml")
    ctx = RuleContext(
        objects=load_objects(mapping, base_dir=tmp_path),
        required_fields=["accession_number", "object_name"],
        controlled_vocabularies=VOCAB,
        object_field_sources=object_field_sources(mapping),
    )
    return RuleRegistry.with_defaults().evaluate(ctx)


def test_clean_object_fields_have_no_findings(tmp_path: Path) -> None:
    objects = add_dates_and_status(generate_clean_objects(count=60, seed=7), seed=5)

    findings = _scan(tmp_path, objects)

    rule_ids = {
        "DATE001_INVERTED_DATE_RANGE",
        "VOCAB001_UNKNOWN_CONTROLLED_VALUE",
        "SCHEMA001_INVALID_FIELD_TYPE",
    }
    offending = [f for f in findings if f.rule.id in rule_ids]
    assert offending == [], [f.summary for f in offending]


def test_injected_object_field_errors_detected_with_perfect_precision_recall(
    tmp_path: Path,
) -> None:
    objects = add_dates_and_status(generate_clean_objects(count=60, seed=7), seed=5)
    dirty, errors = inject_object_field_errors(
        objects, seed=19, num_inverted_date=4, num_bad_vocab=4, num_bad_type=4
    )
    manifest = InjectionManifest(seed=19, errors=errors)

    findings = _scan(tmp_path, dirty)
    metrics = score(findings, manifest)

    for rule_id in (
        "DATE001_INVERTED_DATE_RANGE",
        "VOCAB001_UNKNOWN_CONTROLLED_VALUE",
        "SCHEMA001_INVALID_FIELD_TYPE",
    ):
        m = metrics[rule_id]
        assert m.precision == 1.0, (rule_id, m)
        assert m.recall == 1.0, (rule_id, m)
        assert m.true_positives == 4, (rule_id, m)
