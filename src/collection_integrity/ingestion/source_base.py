"""Shared plumbing for built-in source adapters (BUILD_BRIEF.md Section 24, Phase 4).

A source adapter is a *built-in, versioned mapping profile* for a known institution's published
open-data schema. Instead of asking a user to hand-write a dataset-mapping YAML for the Met's or
Cleveland's column names, the adapter constructs the same `DatasetMapping` in code, so the entire
existing ingestion / transform / provenance / rule pipeline is reused unchanged.

Adapters that ingest a single flat table of objects share `build_objects_mapping`. Adapters whose
source is genuinely relational (e.g. the NGA's many-to-many object<->constituent link table, which
a flat mapping cannot express) build their own mapping and loader.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Literal

from collection_integrity.canonical.mappings import (
    DatasetInfo,
    DatasetMapping,
    EntityMapping,
    coerce_field_mapping,
)

# An adapter turns an input path (a file, or for multi-file sources a directory) into a mapping.
SourceBuilder = Callable[[Path], DatasetMapping]


def build_objects_mapping(
    *,
    name: str,
    input_path: Path,
    fields: dict[str, str],
    fmt: Literal["csv", "json"] = "csv",
    primary_key: str = "object_id",
) -> DatasetMapping:
    """Build a single-file `objects` mapping from a {canonical_field: source_column} dict.

    `input_path` is the data file itself; its parent becomes the mapping's base path and its name
    the entity file, so the standard mapper reads it in place with correct provenance.
    """
    return DatasetMapping(
        version=1,
        dataset=DatasetInfo(name=name, format=fmt, base_path=str(input_path.parent)),
        entities={
            "objects": EntityMapping(
                file=input_path.name,
                primary_key=primary_key,
                fields={c: coerce_field_mapping(src) for c, src in fields.items()},
            )
        },
    )
