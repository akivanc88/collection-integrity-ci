from pathlib import Path

import pytest

from collection_integrity.ingestion.csv_adapter import CsvIngestionError, load_objects_from_csv

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_loads_objects_with_provenance() -> None:
    objects = load_objects_from_csv(FIXTURES / "objects_clean.csv", source_name="test")

    assert len(objects) == 2
    first = objects[0]
    assert first.object_id == "OBJ-001"
    assert first.accession_number == "1998.12.1"
    assert first.title == "Portrait of a Woman"
    assert first.source_ref.source_name == "test"
    assert first.source_ref.source_row_number == 2
    assert first.source_ref.source_record_id == "OBJ-001"
    assert first.source_ref.source_hash


def test_row_numbers_count_header_as_row_one() -> None:
    objects = load_objects_from_csv(FIXTURES / "objects_clean.csv", source_name="test")

    assert [o.source_ref.source_row_number for o in objects] == [2, 3]


def test_whitespace_only_accession_number_normalized_to_none() -> None:
    objects = load_objects_from_csv(
        FIXTURES / "objects_duplicate_accession.csv", source_name="test"
    )

    by_id = {o.object_id: o for o in objects}
    assert by_id["OBJ-004"].accession_number is None
    assert by_id["OBJ-005"].accession_number is None


def test_missing_object_id_column_raises(tmp_path: Path) -> None:
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("accession_number\n1998.12.1\n", encoding="utf-8")

    with pytest.raises(CsvIngestionError):
        load_objects_from_csv(bad_csv, source_name="test")


def test_empty_object_id_raises(tmp_path: Path) -> None:
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("object_id,accession_number\n,1998.12.1\n", encoding="utf-8")

    with pytest.raises(CsvIngestionError):
        load_objects_from_csv(bad_csv, source_name="test")
