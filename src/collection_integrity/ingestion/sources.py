"""Registry of built-in source adapters (BUILD_BRIEF.md Section 24, Phase 4).

`collection-ci scan --source <name> --input <path>` looks a builder up here and constructs the
mapping in memory, then runs the ordinary ingestion pipeline. New institutions are added by writing
an adapter module and registering it below.
"""

from __future__ import annotations

from pathlib import Path

from collection_integrity.canonical.mappings import DatasetMapping
from collection_integrity.ingestion import cleveland_adapter, met_adapter
from collection_integrity.ingestion.readers import IngestionError
from collection_integrity.ingestion.source_base import SourceBuilder

_SOURCES: dict[str, SourceBuilder] = {
    met_adapter.SOURCE_NAME: met_adapter.build_mapping,
    cleveland_adapter.SOURCE_NAME: cleveland_adapter.build_mapping,
}

_DESCRIPTIONS: dict[str, str] = {
    met_adapter.SOURCE_NAME: met_adapter.DESCRIPTION,
    cleveland_adapter.SOURCE_NAME: cleveland_adapter.DESCRIPTION,
}


def available_sources() -> list[str]:
    """Registered source names, sorted for stable CLI help and error messages."""
    return sorted(_SOURCES)


def source_description(name: str) -> str:
    return _DESCRIPTIONS.get(name, name)


def build_source_mapping(name: str, input_path: Path) -> DatasetMapping:
    """Build the in-memory mapping for a registered source, validating the name and path."""
    builder = _SOURCES.get(name)
    if builder is None:
        known = ", ".join(available_sources())
        raise IngestionError(f"unknown source {name!r}; known sources: {known}")
    if not input_path.exists():
        raise IngestionError(f"input not found: {input_path}")
    return builder(input_path)
