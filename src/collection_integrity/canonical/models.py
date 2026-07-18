"""Canonical domain models with source provenance.

See BUILD_BRIEF.md Section 9. Only `SourceRef` and `CollectionObject` are implemented so far;
`MediaAsset`, `RightsRecord`, `LocationRecord`, and `AgentOrMaker` are tracked in
docs/BACKLOG.md and will be added alongside the rules that need them (Phase 2).
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class SourceRef(BaseModel):
    """Provenance pointer back to the exact source location a value came from."""

    model_config = ConfigDict(frozen=True)

    source_name: str
    source_file: str
    source_record_id: str
    source_row_number: int | None = None
    json_pointer: str | None = None
    source_hash: str
    ingested_at: datetime
    raw_fields: dict[str, str] | None = None


class CollectionObject(BaseModel):
    """A canonical museum collection object record."""

    model_config = ConfigDict(frozen=True)

    object_id: str
    accession_number: str | None = None
    title: str | None = None
    object_name: str | None = None
    description: str | None = None
    maker_ids: list[str] = Field(default_factory=list)
    production_start_date: date | None = None
    production_end_date: date | None = None
    materials: list[str] = Field(default_factory=list)
    techniques: list[str] = Field(default_factory=list)
    department: str | None = None
    culture: str | None = None
    current_location_id: str | None = None
    rights_id: str | None = None
    media_ids: list[str] = Field(default_factory=list)
    publication_status: str | None = None
    source_ref: SourceRef
