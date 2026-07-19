"""Dataset-mapping configuration models (BUILD_BRIEF.md Section 10).

A mapping describes how a source export's columns/keys correspond to canonical fields, so the
engine can ingest arbitrary CSV/JSON without hard-coded column names. Only the `objects` entity
and a small transform set are supported so far; media/rights/location/agent entities are added as
their rules land.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Transforms that may be applied to a source value during mapping.
TransformName = Literal["split_pipe", "strip"]


class FieldMapping(BaseModel):
    """How one canonical field is populated from a source record."""

    model_config = ConfigDict(frozen=True)

    source: str
    transform: TransformName | None = None


class EntityMapping(BaseModel):
    model_config = ConfigDict(frozen=True)

    file: str
    primary_key: str
    # canonical field name -> source mapping
    fields: dict[str, FieldMapping]


class DatasetInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    format: Literal["csv", "json"]
    base_path: str = "."


class DatasetMapping(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: int = 1
    dataset: DatasetInfo
    entities: dict[str, EntityMapping] = Field(default_factory=dict)


def coerce_field_mapping(raw: str | dict[str, str]) -> FieldMapping:
    """Accept either a bare source-column string or a {source, transform} mapping.

    This lets a mapping file write `title: title` for the common case and
    `media_ids: {source: media_ids, transform: split_pipe}` when a transform is needed. Pydantic
    validates the transform value against the allowed set.
    """
    if isinstance(raw, str):
        return FieldMapping(source=raw)
    return FieldMapping.model_validate(raw)
