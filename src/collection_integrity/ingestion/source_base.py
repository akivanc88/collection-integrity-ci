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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from collection_integrity.canonical.mappings import (
    DatasetInfo,
    DatasetMapping,
    EntityMapping,
    coerce_field_mapping,
)
from collection_integrity.canonical.models import (
    AgentOrMaker,
    CollectionObject,
    LocationRecord,
    MediaAsset,
    RightsRecord,
)

# An adapter turns an input path (a file, or for multi-file sources a directory) into a mapping.
SourceBuilder = Callable[[Path], DatasetMapping]


@dataclass
class SourceLoad:
    """Canonical entities produced by a source adapter, plus what the run manifest needs.

    `object_field_sources` maps canonical object fields to their source columns (SCHEMA001 uses it
    to report the offending raw value); `input_files` are the data files to hash into the manifest.
    """

    objects: list[CollectionObject]
    media: list[MediaAsset] = field(default_factory=list)
    rights: list[RightsRecord] = field(default_factory=list)
    locations: list[LocationRecord] = field(default_factory=list)
    agents: list[AgentOrMaker] = field(default_factory=list)
    object_field_sources: dict[str, str] = field(default_factory=dict)
    input_files: list[Path] = field(default_factory=list)


# An adapter loads an input path into canonical entities.
SourceLoader = Callable[[Path], SourceLoad]


def load_from_mapping(mapping: DatasetMapping, base_dir: Path) -> SourceLoad:
    """Load a `DatasetMapping` through the standard mapper into a `SourceLoad`.

    Used by the single-file adapters (Met, Cleveland). Imported lazily to avoid a module-load
    cycle with the mapper.
    """
    from collection_integrity.ingestion import mapper

    objects = mapper.load_objects(mapping, base_dir=base_dir)
    media = (
        mapper.load_media(mapping, base_dir=base_dir) if mapper.has_entity(mapping, "media") else []
    )
    rights = (
        mapper.load_rights(mapping, base_dir=base_dir)
        if mapper.has_entity(mapping, "rights")
        else []
    )
    locations = (
        mapper.load_locations(mapping, base_dir=base_dir)
        if mapper.has_entity(mapping, "locations")
        else []
    )
    agents = (
        mapper.load_agents(mapping, base_dir=base_dir)
        if mapper.has_entity(mapping, "agents")
        else []
    )
    return SourceLoad(
        objects=objects,
        media=media,
        rights=rights,
        locations=locations,
        agents=agents,
        object_field_sources=mapper.object_field_sources(mapping),
        input_files=mapper.resolve_entity_files(mapping, base_dir),
    )


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
