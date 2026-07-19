"""Apply a dataset mapping to raw records, producing canonical objects with provenance.

This is the general ingestion path (BUILD_BRIEF.md Section 10) that sits in front of the raw
readers. It replaces the fixed-column CSV adapter for configurable sources; the old adapter
remains for the simple, mapping-free case.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import yaml

from collection_integrity.canonical.mappings import (
    DatasetMapping,
    EntityMapping,
    FieldMapping,
    coerce_field_mapping,
)
from collection_integrity.canonical.models import (
    AgentOrMaker,
    CollectionObject,
    LocationRecord,
    MediaAsset,
    RightsRecord,
    SourceRef,
)
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
    "production_start_date",
    "production_end_date",
}
LIST_OBJECT_FIELDS = {"media_ids", "maker_ids", "materials", "techniques"}

# Object fields with a non-string canonical type, and the type SCHEMA001 checks them against.
TYPED_OBJECT_FIELDS = {
    "production_start_date": "date",
    "production_end_date": "date",
}

SCALAR_MEDIA_FIELDS = {
    "media_id",
    "object_id",
    "path_or_url",
    "media_type",
    "mime_type",
    "width",
    "height",
    "file_size",
    "checksum",
    "is_primary",
    "publication_status",
    "rights_id",
}

SCALAR_RIGHTS_FIELDS = {
    "rights_id",
    "rights_status",
    "copyright_holder",
    "license_uri",
    "credit_line",
    "publication_allowed",
    "review_required",
}

SCALAR_LOCATION_FIELDS = {
    "location_id",
    "name",
    "parent_location_id",
    "object_id",
    "is_current",
}

SCALAR_AGENT_FIELDS = {
    "agent_id",
    "preferred_name",
    "nationality",
    "birth_date",
    "death_date",
}

_TRUE = {"true", "1", "yes", "y", "t"}
_FALSE = {"false", "0", "no", "n", "f"}

# A mapped entity record: the canonical-name -> value dict plus its provenance.
MappedRecord = tuple[dict[str, str | list[str]], SourceRef]


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


def _load_entity_records(
    mapping: DatasetMapping,
    entity_name: str,
    base_dir: Path,
    scalar_fields: set[str],
    list_fields: set[str],
) -> list[MappedRecord]:
    """Read an entity's file and apply its field mapping, keyed by the entity's primary key.

    The primary key's mapped value must be non-empty for every record; an empty one is a fatal
    ingestion error (a record with no identity cannot be referenced or reported on).
    """
    if entity_name not in mapping.entities:
        raise IngestionError(f"mapping has no {entity_name!r} entity")
    entity = mapping.entities[entity_name]

    base_path = Path(mapping.dataset.base_path)
    if not base_path.is_absolute():
        base_path = base_dir / base_path
    file_path = base_path / entity.file

    records = read_rows(file_path, mapping.dataset.format)

    out: list[MappedRecord] = []
    for row_number, raw_fields in records:
        mapped: dict[str, str | list[str]] = {}
        for canonical, field_mapping in entity.fields.items():
            value = _map_value(raw_fields, field_mapping)
            if canonical in scalar_fields:
                text = value if isinstance(value, str) else ""
                mapped[canonical] = text.strip()
            elif canonical in list_fields:
                mapped[canonical] = value if isinstance(value, list) else []

        key_value = str(mapped.get(entity.primary_key, "")).strip()
        if not key_value:
            raise IngestionError(
                f"{file_path}: record {row_number} has an empty mapped {entity.primary_key}"
            )

        source_ref = SourceRef(
            source_name=mapping.dataset.name,
            source_file=str(file_path),
            source_record_id=key_value,
            source_row_number=row_number,
            source_hash=hash_record(raw_fields),
            ingested_at=datetime.now(UTC),
            raw_fields=raw_fields,
        )
        out.append((mapped, source_ref))
    return out


def load_objects(mapping: DatasetMapping, base_dir: Path) -> list[CollectionObject]:
    """Load the `objects` entity described by `mapping` into canonical records."""
    records = _load_entity_records(
        mapping, "objects", base_dir, SCALAR_OBJECT_FIELDS, LIST_OBJECT_FIELDS
    )
    return [_build_object(mapped, ref) for mapped, ref in records]


def load_media(mapping: DatasetMapping, base_dir: Path) -> list[MediaAsset]:
    """Load the `media` entity described by `mapping` into canonical records."""
    records = _load_entity_records(mapping, "media", base_dir, SCALAR_MEDIA_FIELDS, set())
    return [_build_media(mapped, ref) for mapped, ref in records]


def load_rights(mapping: DatasetMapping, base_dir: Path) -> list[RightsRecord]:
    """Load the `rights` entity described by `mapping` into canonical records."""
    records = _load_entity_records(mapping, "rights", base_dir, SCALAR_RIGHTS_FIELDS, set())
    return [_build_rights(mapped, ref) for mapped, ref in records]


def load_locations(mapping: DatasetMapping, base_dir: Path) -> list[LocationRecord]:
    """Load the `locations` entity described by `mapping` into canonical records."""
    records = _load_entity_records(mapping, "locations", base_dir, SCALAR_LOCATION_FIELDS, set())
    return [_build_location(mapped, ref) for mapped, ref in records]


def load_agents(mapping: DatasetMapping, base_dir: Path) -> list[AgentOrMaker]:
    """Load the `agents` entity described by `mapping` into canonical records."""
    records = _load_entity_records(mapping, "agents", base_dir, SCALAR_AGENT_FIELDS, set())
    return [_build_agent(mapped, ref) for mapped, ref in records]


def has_entity(mapping: DatasetMapping, entity_name: str) -> bool:
    return entity_name in mapping.entities


def _scalar(mapped: dict[str, str | list[str]], name: str) -> str | None:
    value = mapped.get(name)
    return value or None if isinstance(value, str) else None


def _int(mapped: dict[str, str | list[str]], name: str) -> int | None:
    value = mapped.get(name)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return int(value.strip())
    except ValueError:
        # A non-integer here is a type problem for SCHEMA001 to report later; ingestion keeps the
        # raw value in source_ref.raw_fields and leaves the canonical field unset.
        return None


def _bool(mapped: dict[str, str | list[str]], name: str) -> bool | None:
    value = mapped.get(name)
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    return None


def parse_date(raw: str) -> date | None:
    """Parse a museum-style date string, or return None if it is empty or unparseable.

    Accepts ISO dates (YYYY-MM-DD) and bare years (YYYY, mapped to Jan 1). SCHEMA001 and the date
    rules share this parser so "what counts as a valid date" is defined in exactly one place.
    """
    text = raw.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    if text.isdigit() and len(text) == 4:
        return date(int(text), 1, 1)
    return None


def _date(mapped: dict[str, str | list[str]], name: str) -> date | None:
    value = mapped.get(name)
    return parse_date(value) if isinstance(value, str) else None


def object_field_sources(mapping: DatasetMapping) -> dict[str, str]:
    """canonical field name -> source column, for the objects entity (used by SCHEMA001)."""
    entity = mapping.entities.get("objects")
    if entity is None:
        return {}
    return {canonical: fm.source for canonical, fm in entity.fields.items()}


def resolve_entity_files(mapping: DatasetMapping, base_dir: Path) -> list[Path]:
    """Resolved paths of every entity data file the mapping references (for manifest hashing)."""
    base_path = Path(mapping.dataset.base_path)
    if not base_path.is_absolute():
        base_path = base_dir / base_path
    return [base_path / entity.file for entity in mapping.entities.values()]


def _build_object(mapped: dict[str, str | list[str]], source_ref: SourceRef) -> CollectionObject:
    def listing(name: str) -> list[str]:
        value = mapped.get(name)
        return value if isinstance(value, list) else []

    return CollectionObject(
        object_id=str(mapped["object_id"]),
        accession_number=_scalar(mapped, "accession_number"),
        title=_scalar(mapped, "title"),
        object_name=_scalar(mapped, "object_name"),
        description=_scalar(mapped, "description"),
        department=_scalar(mapped, "department"),
        culture=_scalar(mapped, "culture"),
        current_location_id=_scalar(mapped, "current_location_id"),
        rights_id=_scalar(mapped, "rights_id"),
        publication_status=_scalar(mapped, "publication_status"),
        production_start_date=_date(mapped, "production_start_date"),
        production_end_date=_date(mapped, "production_end_date"),
        media_ids=listing("media_ids"),
        maker_ids=listing("maker_ids"),
        materials=listing("materials"),
        techniques=listing("techniques"),
        source_ref=source_ref,
    )


def _build_media(mapped: dict[str, str | list[str]], source_ref: SourceRef) -> MediaAsset:
    return MediaAsset(
        media_id=str(mapped["media_id"]),
        object_id=_scalar(mapped, "object_id"),
        path_or_url=_scalar(mapped, "path_or_url"),
        media_type=_scalar(mapped, "media_type"),
        mime_type=_scalar(mapped, "mime_type"),
        width=_int(mapped, "width"),
        height=_int(mapped, "height"),
        file_size=_int(mapped, "file_size"),
        checksum=_scalar(mapped, "checksum"),
        publication_status=_scalar(mapped, "publication_status"),
        rights_id=_scalar(mapped, "rights_id"),
        source_ref=source_ref,
    )


def _build_rights(mapped: dict[str, str | list[str]], source_ref: SourceRef) -> RightsRecord:
    return RightsRecord(
        rights_id=str(mapped["rights_id"]),
        rights_status=_scalar(mapped, "rights_status"),
        copyright_holder=_scalar(mapped, "copyright_holder"),
        license_uri=_scalar(mapped, "license_uri"),
        credit_line=_scalar(mapped, "credit_line"),
        publication_allowed=_bool(mapped, "publication_allowed"),
        review_required=_bool(mapped, "review_required"),
        source_ref=source_ref,
    )


def _build_location(mapped: dict[str, str | list[str]], source_ref: SourceRef) -> LocationRecord:
    return LocationRecord(
        location_id=str(mapped["location_id"]),
        name=_scalar(mapped, "name"),
        parent_location_id=_scalar(mapped, "parent_location_id"),
        object_id=_scalar(mapped, "object_id"),
        is_current=_bool(mapped, "is_current"),
        source_ref=source_ref,
    )


def _build_agent(mapped: dict[str, str | list[str]], source_ref: SourceRef) -> AgentOrMaker:
    return AgentOrMaker(
        agent_id=str(mapped["agent_id"]),
        preferred_name=_scalar(mapped, "preferred_name"),
        nationality=_scalar(mapped, "nationality"),
        birth_date=_date(mapped, "birth_date"),
        death_date=_date(mapped, "death_date"),
        source_ref=source_ref,
    )
