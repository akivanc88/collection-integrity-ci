from pathlib import Path

import pytest

from collection_integrity.ingestion.mapper import load_mapping, load_objects
from collection_integrity.ingestion.readers import IngestionError
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.registry import RuleRegistry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(mapping_name: str) -> list:  # type: ignore[type-arg]
    mapping = load_mapping(FIXTURES / mapping_name)
    return load_objects(mapping, base_dir=FIXTURES)


def test_csv_mapping_renames_columns_and_splits_pipe() -> None:
    objects = _load("mapping_csv.yaml")

    assert [o.object_id for o in objects] == ["A1", "A2", "A3"]
    assert objects[0].accession_number == "2001.5.1"
    assert objects[0].object_name == "Sunrise"
    assert objects[0].media_ids == ["IMG-1", "IMG-2"]
    assert objects[2].media_ids == []


def test_json_and_csv_mappings_produce_equivalent_records() -> None:
    csv_objects = _load("mapping_csv.yaml")
    json_objects = _load("mapping_json.yaml")

    def canonical(objs: list) -> list:  # type: ignore[type-arg]
        return [
            (o.object_id, o.accession_number, o.object_name, o.title, tuple(o.media_ids))
            for o in objs
        ]

    assert canonical(csv_objects) == canonical(json_objects)


def test_row_numbers_preserved_from_source() -> None:
    csv_objects = _load("mapping_csv.yaml")
    # CSV counts the header as row 1, so A1 is row 2.
    assert csv_objects[0].source_ref.source_row_number == 2

    json_objects = _load("mapping_json.yaml")
    # JSON row numbers are 1-based array positions.
    assert json_objects[0].source_ref.source_row_number == 1


def test_raw_fields_preserved_for_provenance() -> None:
    objects = _load("mapping_csv.yaml")
    assert objects[0].source_ref.raw_fields is not None
    assert objects[0].source_ref.raw_fields["id"] == "A1"


def test_rules_run_through_mapped_objects() -> None:
    objects = _load("mapping_csv.yaml")
    ctx = RuleContext(objects=objects, required_fields=["accession_number"])
    findings = RuleRegistry.with_defaults().evaluate(ctx)

    # A2 and A3 share accession 2001.5.2 -> one CORE001 finding, no missing required fields.
    core001 = [f for f in findings if f.rule.id == "CORE001_DUPLICATE_ACCESSION_NUMBER"]
    assert len(core001) == 1
    assert core001[0].entity.id == "2001.5.2"


def test_mapping_without_objects_entity_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "version: 1\ndataset:\n  name: x\n  format: csv\nentities: {}\n", encoding="utf-8"
    )
    mapping = load_mapping(bad)

    with pytest.raises(IngestionError):
        load_objects(mapping, base_dir=tmp_path)


def test_invalid_json_array_raises(tmp_path: Path) -> None:
    (tmp_path / "obj.json").write_text('{"not": "an array"}', encoding="utf-8")
    mapping_file = tmp_path / "m.yaml"
    mapping_file.write_text(
        "version: 1\n"
        "dataset:\n  name: x\n  format: json\n  base_path: .\n"
        "entities:\n  objects:\n    file: obj.json\n    primary_key: object_id\n"
        "    fields:\n      object_id: id\n",
        encoding="utf-8",
    )
    mapping = load_mapping(mapping_file)

    # Assert the specific array guard fires, not just any IngestionError — a top-level object
    # must be rejected as "not an array", distinct from the per-record "not a JSON object" check.
    with pytest.raises(IngestionError, match="expected a JSON array"):
        load_objects(mapping, base_dir=tmp_path)


def test_empty_mapped_object_id_raises(tmp_path: Path) -> None:
    (tmp_path / "obj.csv").write_text("id,acc\n,2001.1.1\n", encoding="utf-8")
    mapping_file = tmp_path / "m.yaml"
    mapping_file.write_text(
        "version: 1\n"
        "dataset:\n  name: x\n  format: csv\n  base_path: .\n"
        "entities:\n  objects:\n    file: obj.csv\n    primary_key: object_id\n"
        "    fields:\n      object_id: id\n      accession_number: acc\n",
        encoding="utf-8",
    )
    mapping = load_mapping(mapping_file)

    with pytest.raises(IngestionError, match="empty mapped object_id"):
        load_objects(mapping, base_dir=tmp_path)
