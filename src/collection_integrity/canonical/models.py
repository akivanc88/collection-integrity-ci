"""Canonical domain models with source provenance.

See BUILD_BRIEF.md Section 9. `SourceRef`, `CollectionObject`, and `MediaAsset` are implemented;
`RightsRecord`, `LocationRecord`, and `AgentOrMaker` are tracked in docs/BACKLOG.md and added
alongside the rules that need them (Phase 2).
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


class MediaAsset(BaseModel):
    """A canonical media record (image or other asset) linked to a collection object."""

    model_config = ConfigDict(frozen=True)

    media_id: str
    object_id: str | None = None
    path_or_url: str | None = None
    media_type: str | None = None
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    file_size: int | None = None
    checksum: str | None = None
    is_primary: bool | None = None
    publication_status: str | None = None
    rights_id: str | None = None
    source_ref: SourceRef


class RightsRecord(BaseModel):
    """A canonical rights/usage record linked to objects or media."""

    model_config = ConfigDict(frozen=True)

    rights_id: str
    rights_status: str | None = None
    copyright_holder: str | None = None
    license_uri: str | None = None
    credit_line: str | None = None
    publication_allowed: bool | None = None
    review_required: bool | None = None
    expiry_date: date | None = None
    source_ref: SourceRef


class LocationRecord(BaseModel):
    """A canonical location record.

    A row may act as a hierarchy node (``location_id`` + ``parent_location_id``), an object
    location assignment (``object_id`` + ``is_current``), or both — see docs/DOMAIN_MODEL.md.
    """

    model_config = ConfigDict(frozen=True)

    location_id: str
    name: str | None = None
    parent_location_id: str | None = None
    object_id: str | None = None
    is_current: bool | None = None
    effective_start: date | None = None
    effective_end: date | None = None
    source_ref: SourceRef
