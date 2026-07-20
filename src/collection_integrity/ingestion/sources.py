"""Registry of built-in source adapters (BUILD_BRIEF.md Section 24, Phase 4).

`collection-ci scan --source <name> --input <path>` looks a loader up here and ingests the export
into canonical entities, then runs the ordinary rule engine. New institutions are added by writing
an adapter module and registering it below.
"""

from __future__ import annotations

from pathlib import Path

from collection_integrity.ingestion import cleveland_adapter, met_adapter, nga_adapter
from collection_integrity.ingestion.readers import IngestionError
from collection_integrity.ingestion.source_base import SourceLoad, SourceLoader

_LOADERS: dict[str, SourceLoader] = {
    met_adapter.SOURCE_NAME: met_adapter.load,
    cleveland_adapter.SOURCE_NAME: cleveland_adapter.load,
    nga_adapter.SOURCE_NAME: nga_adapter.load,
}

_DESCRIPTIONS: dict[str, str] = {
    met_adapter.SOURCE_NAME: met_adapter.DESCRIPTION,
    cleveland_adapter.SOURCE_NAME: cleveland_adapter.DESCRIPTION,
    nga_adapter.SOURCE_NAME: nga_adapter.DESCRIPTION,
}


def available_sources() -> list[str]:
    """Registered source names, sorted for stable CLI help and error messages."""
    return sorted(_LOADERS)


def source_description(name: str) -> str:
    return _DESCRIPTIONS.get(name, name)


def load_source(name: str, input_path: Path) -> SourceLoad:
    """Ingest a registered source's export into canonical entities, validating name and path."""
    loader = _LOADERS.get(name)
    if loader is None:
        known = ", ".join(available_sources())
        raise IngestionError(f"unknown source {name!r}; known sources: {known}")
    if not input_path.exists():
        raise IngestionError(f"input not found: {input_path}")
    return loader(input_path)
