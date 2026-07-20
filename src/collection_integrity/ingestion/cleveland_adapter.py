"""Cleveland Museum of Art Open Access adapter (BUILD_BRIEF.md Section 24, Phase 4).

Source: https://github.com/ClevelandMuseumArt/openaccess — published as both `data/openaccess.csv`
and `data/openaccess.json` (CC0 metadata). Cleveland uses the same field names in both formats, so
one field map serves both; the format is chosen from the input file's extension.

Scope: object-level identity/cataloging fields. Cleveland's `creation_date_earliest` /
`creation_date_latest` are the year bounds used for production dates (4-digit CE years parse via the
shared date parser; ancient/BCE values are a documented limitation, see docs/DATA_SOURCES.md).
Artist/creator extraction (the `creators` array) is deferred to the relational NGA adapter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from collection_integrity.canonical.mappings import DatasetMapping
from collection_integrity.ingestion.source_base import build_objects_mapping

SOURCE_NAME = "cleveland"
DESCRIPTION = "Cleveland Museum of Art Open Access (openaccess.csv/.json, CC0)"

# canonical field -> Cleveland column/key (github.com/ClevelandMuseumArt/openaccess schema).
FIELD_MAP = {
    "object_id": "id",
    "accession_number": "accession_number",
    "title": "title",
    "object_name": "type",
    "department": "department",
    "culture": "culture",
    "production_start_date": "creation_date_earliest",
    "production_end_date": "creation_date_latest",
}


def _format_for(input_path: Path) -> Literal["csv", "json"]:
    return "json" if input_path.suffix.lower() == ".json" else "csv"


def build_mapping(input_path: Path) -> DatasetMapping:
    """Build the Cleveland objects mapping, choosing CSV or JSON from the file extension."""
    return build_objects_mapping(
        name=SOURCE_NAME, input_path=input_path, fields=FIELD_MAP, fmt=_format_for(input_path)
    )
