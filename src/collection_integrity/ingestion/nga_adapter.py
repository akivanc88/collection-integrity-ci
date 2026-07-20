"""National Gallery of Art Open Data adapter (BUILD_BRIEF.md Section 24, Phase 4).

Source: https://github.com/NationalGalleryOfArt/opendata (CC0). Unlike the Met and Cleveland
single-file exports, the NGA publishes a *relational* dataset: `objects.csv`, a
`objects_constituents.csv` many-to-many link table, and `constituents.csv` (artists/makers, with
birth/death years). A flat column mapping cannot express that join, so this adapter is the one that
needs bespoke loading.

It reuses the ordinary mapper for `objects.csv` (as the objects entity) and `constituents.csv` (as
the agents entity) — inheriting provenance, date parsing, and SCHEMA001 field sources for free — and
adds only the join: it reads the link table and stamps each object's `maker_ids`, which lets DATE002
(production date vs. maker lifespan) run, a check impossible without the relational link.

Ancient/BCE `beginyear`/`endyear` values are a documented limitation (docs/DATA_SOURCES.md).
"""

from __future__ import annotations

import os
from pathlib import Path

from collection_integrity.canonical.mappings import (
    DatasetInfo,
    DatasetMapping,
    EntityMapping,
    coerce_field_mapping,
)
from collection_integrity.ingestion.readers import IngestionError, read_csv_rows
from collection_integrity.ingestion.source_base import SourceLoad, load_from_mapping

SOURCE_NAME = "nga"
DESCRIPTION = "National Gallery of Art Open Data (objects/constituents CSVs, CC0)"

OBJECTS_FILE = "objects.csv"
CONSTITUENTS_FILE = "constituents.csv"
LINK_FILE = "objects_constituents.csv"

# canonical object field -> NGA objects.csv column.
OBJECT_FIELDS = {
    "object_id": "objectid",
    "accession_number": "accessionnum",
    "title": "title",
    "object_name": "classification",
    "department": "departmentabbr",
    "production_start_date": "beginyear",
    "production_end_date": "endyear",
}

# canonical agent field -> NGA constituents.csv column (beginyear/endyear = maker's life dates).
AGENT_FIELDS = {
    "agent_id": "constituentid",
    "preferred_name": "preferreddisplayname",
    "nationality": "nationality",
    "birth_date": "beginyear",
    "death_date": "endyear",
}


def build_mapping(input_dir: Path) -> DatasetMapping:
    """The objects+agents mapping; the maker link is applied separately by `load`."""
    return DatasetMapping(
        version=1,
        dataset=DatasetInfo(name=SOURCE_NAME, format="csv", base_path=str(input_dir)),
        entities={
            "objects": EntityMapping(
                file=OBJECTS_FILE,
                primary_key="object_id",
                fields={c: coerce_field_mapping(s) for c, s in OBJECT_FIELDS.items()},
            ),
            "agents": EntityMapping(
                file=CONSTITUENTS_FILE,
                primary_key="agent_id",
                fields={c: coerce_field_mapping(s) for c, s in AGENT_FIELDS.items()},
            ),
        },
    )


def _maker_ids_by_object(link_path: Path) -> dict[str, list[str]]:
    """Read the link table into {objectid: [constituentid, ...]}, ordered by displayorder.

    Rows missing either id are skipped (they cannot express a link). Ordering is deterministic so
    the canonical maker list is stable regardless of link-table row order.
    """
    if not link_path.exists():
        raise IngestionError(f"NGA link table not found: {link_path}")
    pairs: dict[str, list[tuple[int, str]]] = {}
    for row_number, raw in read_csv_rows(link_path):
        object_id = raw.get("objectid", "").strip()
        constituent_id = raw.get("constituentid", "").strip()
        if not object_id or not constituent_id:
            continue
        raw_order = raw.get("displayorder", "").strip()
        order = int(raw_order) if raw_order.lstrip("-").isdigit() else row_number
        pairs.setdefault(object_id, []).append((order, constituent_id))
    return {oid: [cid for _, cid in sorted(items)] for oid, items in pairs.items()}


def load(input_dir: Path) -> SourceLoad:
    """Ingest an NGA opendata directory (objects + constituents + link table)."""
    mapping = build_mapping(input_dir)
    loaded = load_from_mapping(mapping, Path("."))

    link_path = input_dir / LINK_FILE
    makers = _maker_ids_by_object(link_path)
    objects = [
        obj.model_copy(update={"maker_ids": makers.get(obj.object_id, [])})
        for obj in loaded.objects
    ]

    return SourceLoad(
        objects=objects,
        agents=loaded.agents,
        object_field_sources=loaded.object_field_sources,
        input_files=[*loaded.input_files, Path(os.path.normpath(link_path))],
    )
