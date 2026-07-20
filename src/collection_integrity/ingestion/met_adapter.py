"""Metropolitan Museum of Art Open Access adapter (BUILD_BRIEF.md Section 24, Phase 4).

Source: https://github.com/metmuseum/openaccess — a single `MetObjects.csv` (CC0 metadata).
This adapter maps the Met's object-level columns onto canonical `CollectionObject` fields so the
deterministic rules (duplicate accession, missing required fields, inverted/invalid production
dates) run on real Met exports without a hand-written mapping.

Scope and honesty: only object-level identity/cataloging fields are mapped. Met artist columns are
pipe-delimited multi-valued within the same row (no clean 1:1 constituent table in this file), so
maker/agent extraction and DATE002 are intentionally deferred to the relational NGA adapter and the
backlog. Production dates come from the integer `Object Begin/End Date` year columns; these parse
as 4-digit CE years (the overwhelming majority of records). Ancient/BCE year values that our shared
date parser cannot represent as a calendar date are a documented limitation (docs/DATA_SOURCES.md).
"""

from __future__ import annotations

from pathlib import Path

from collection_integrity.canonical.mappings import DatasetMapping
from collection_integrity.ingestion.source_base import (
    SourceLoad,
    build_objects_mapping,
    load_from_mapping,
)

SOURCE_NAME = "met"
DESCRIPTION = "Metropolitan Museum of Art Open Access (MetObjects.csv, CC0)"

# canonical field -> Met CSV column header (github.com/metmuseum/openaccess schema).
FIELD_MAP = {
    "object_id": "Object ID",
    "accession_number": "Object Number",
    "title": "Title",
    "object_name": "Object Name",
    "department": "Department",
    "culture": "Culture",
    "production_start_date": "Object Begin Date",
    "production_end_date": "Object End Date",
}


def build_mapping(input_path: Path) -> DatasetMapping:
    """Build the Met objects mapping for a `MetObjects.csv`-shaped file at `input_path`."""
    return build_objects_mapping(name=SOURCE_NAME, input_path=input_path, fields=FIELD_MAP)


def load(input_path: Path) -> SourceLoad:
    """Ingest a `MetObjects.csv` file into canonical entities."""
    return load_from_mapping(build_mapping(input_path), Path("."))
