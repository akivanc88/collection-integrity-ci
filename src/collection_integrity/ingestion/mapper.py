"""Apply a dataset mapping to raw records, producing canonical objects with provenance.

This is the general ingestion path (BUILD_BRIEF.md Section 10) that sits in front of the raw
readers. It replaces the fixed-column CSV adapter for configurable sources; the old adapter
remains for the simple, mapping-free case.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from collection_integrity.canonical.mappings import (
    DatasetMapping,
    EntityMapping,
    FieldMapping,
    coerce_field_mapping,
)
from collection_integrity.canonical.models import CollectionObject, SourceRef
from collection_integrity.ingestion.readers import IngestionError, read_rows
from collection_integrity.provenance import hash_record

# Canonical object fields the mapper knows how to populate. Others in a mapping are ignored with
# the raw value still preserved in source_ref.raw_fields.
SCALAR_OBJECT_FIELDS = {
    "object_id",
    "accession_number",
    "title",
    "object_name",
    "description",
    "department",
    "culture",
    "current_location_id",
    "rights_id",
    "publication_status",
}
LIST_OBJECT_FIELDS = {"media_ids", "maker_ids", "materials", "techniques"}


def load_mapping(path: Path) -> DatasetMapping:
    """Load and validate a dataset-mapping YAML file."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise IngestionError(f"{path}: mapping must be a YAML mapping")

    entities_raw = raw.get("entities", {}) or {}
    entities: dict[str, EntityMapping] = {}
    for name, ent in entities_raw.items():
        fields = {
            canonical: coerce_field_mapping(src) for canonical, src in ent.get("fields", {}).items()
        }
        entities[name] = EntityMapping(
            file=ent["file"], primary_key=ent["primary_key"], fields=fields
        )

    return DatasetMapping(
        version=raw.get("version", 1),
        dataset=raw["dataset"],
        entities=entities,
    )


def _apply_transform(value: str, transform: str | None) -> str | list[str]:
    if transform == "split_pipe":
        return [part.strip() for part in value.split("|") if part.strip()]
    if transform == "strip":
        return value.strip()
    return value


def _map_value(raw_fields: dict[str, str], mapping: FieldMapping) -> str | list[str]:
    return _apply_transform(raw_fields.get(mapping.source, ""), mapping.transform)


def load_objects(mapping: DatasetMapping, base_dir: Path) -> list[CollectionObject]:
    """Load the `objects` entity described by `mapping` into canonical records."""
    if "objects" not in mapping.entities:
        raise IngestionError("mapping has no 'objects' entity")
    entity = mapping.entities["objects"]

    base_path = Path(mapping.dataset.base_path)
    if not base_path.is_absolute():
        base_path = base_dir / base_path
    file_path = base_path / entity.file

    records = read_rows(file_path, mapping.dataset.format)

    objects: list[CollectionObject] = []
    for row_number, raw_fields in records:
        mapped: dict[str, str | list[str]] = {}
        for canonical, field_mapping in entity.fields.items():
            value = _map_value(raw_fields, field_mapping)
            if canonical in SCALAR_OBJECT_FIELDS:
                text = value if isinstance(value, str) else ""
                mapped[canonical] = text.strip()
            elif canonical in LIST_OBJECT_FIELDS:
                mapped[canonical] = value if isinstance(value, list) else []

        object_id = str(mapped.get("object_id", "")).strip()
        if not object_id:
            raise IngestionError(f"{file_path}: record {row_number} has an empty mapped object_id")

        source_ref = SourceRef(
            source_name=mapping.dataset.name,
            source_file=str(file_path),
            source_record_id=object_id,
            source_row_number=row_number,
            source_hash=hash_record(raw_fields),
            ingested_at=datetime.now(UTC),
            raw_fields=raw_fields,
        )
        objects.append(_build_object(mapped, source_ref))
    return objects


def _build_object(mapped: dict[str, str | list[str]], source_ref: SourceRef) -> CollectionObject:
    def scalar(name: str) -> str | None:
        value = mapped.get(name)
        return value or None if isinstance(value, str) else None

    def listing(name: str) -> list[str]:
        value = mapped.get(name)
        return value if isinstance(value, list) else []

    return CollectionObject(
        object_id=str(mapped["object_id"]),
        accession_number=scalar("accession_number"),
        title=scalar("title"),
        object_name=scalar("object_name"),
        description=scalar("description"),
        department=scalar("department"),
        culture=scalar("culture"),
        current_location_id=scalar("current_location_id"),
        rights_id=scalar("rights_id"),
        publication_status=scalar("publication_status"),
        media_ids=listing("media_ids"),
        maker_ids=listing("maker_ids"),
        materials=listing("materials"),
        techniques=listing("techniques"),
        source_ref=source_ref,
    )
