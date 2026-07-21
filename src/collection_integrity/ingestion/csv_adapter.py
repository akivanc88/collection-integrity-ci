"""Minimal CSV ingestion for the first vertical slice.

This reads an objects CSV whose column names already match the canonical field names
(`object_id`, `accession_number`, `title`, `object_name`) directly, with no configurable mapping
yet. The configurable dataset-mapping layer described in BUILD_BRIEF.md Section 10 is Phase 2
work (tracked in docs/BACKLOG.md); this adapter is the minimal end-to-end path the mapping engine
will later sit in front of.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from collection_integrity.canonical.models import CollectionObject, SourceRef
from collection_integrity.provenance import hash_record

REQUIRED_COLUMNS = {"object_id"}


class CsvIngestionError(ValueError):
    """Raised when an objects CSV is missing required structure."""


def load_objects_from_csv(path: Path, source_name: str) -> list[CollectionObject]:
    """Read an objects CSV file into canonical `CollectionObject` records.

    Row numbering is 1-based and counts the header as row 1, so the first data row is row 2 —
    this matches what a spreadsheet application shows a user for that row.
    """
    try:
        return _read_objects(path, source_name)
    except UnicodeDecodeError as exc:
        raise CsvIngestionError(f"{path}: not valid UTF-8 text: {exc}") from exc
    except csv.Error as exc:
        raise CsvIngestionError(f"{path}: malformed CSV: {exc}") from exc


def _read_objects(path: Path, source_name: str) -> list[CollectionObject]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
            raise CsvIngestionError(f"{path}: missing required column(s): {sorted(missing)}")

        objects: list[CollectionObject] = []
        for row_number, row in enumerate(reader, start=2):
            object_id = (row.get("object_id") or "").strip()
            if not object_id:
                raise CsvIngestionError(f"{path}: row {row_number} has an empty object_id")

            clean_row = {k: (v or "") for k, v in row.items()}
            source_ref = SourceRef(
                source_name=source_name,
                source_file=str(path),
                source_record_id=object_id,
                source_row_number=row_number,
                source_hash=hash_record(clean_row),
                ingested_at=datetime.now(UTC),
                raw_fields=clean_row,
            )

            accession_number = (row.get("accession_number") or "").strip() or None
            objects.append(
                CollectionObject(
                    object_id=object_id,
                    accession_number=accession_number,
                    title=(row.get("title") or "").strip() or None,
                    object_name=(row.get("object_name") or "").strip() or None,
                    source_ref=source_ref,
                )
            )
        return objects
