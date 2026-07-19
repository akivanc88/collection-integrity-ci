"""Command-line interface.

The `scan` command ingests objects either directly from a canonical-column CSV (--objects-csv) or
through a configurable dataset-mapping YAML that describes an arbitrary CSV/JSON export (--mapping),
then runs the enabled deterministic rules through the rule registry. This is an early Phase 2
shape, not the full CLI specification in Section 13 — per-rule enable/disable via a ruleset file,
multi-entity ingestion (media/rights/locations), and the other report formats are tracked in
docs/BACKLOG.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from collection_integrity.canonical.models import CollectionObject, MediaAsset, RightsRecord
from collection_integrity.ingestion.csv_adapter import CsvIngestionError, load_objects_from_csv
from collection_integrity.ingestion.mapper import (
    has_entity,
    load_mapping,
    load_media,
    load_objects,
    load_rights,
)
from collection_integrity.ingestion.readers import IngestionError
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.core_rules import REQUIRABLE_OBJECT_FIELDS
from collection_integrity.rules.registry import RuleRegistry

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()

SEVERITY_ORDER = {"critical": 3, "high": 2, "medium": 1, "low": 0}

# Default policy-required fields for CORE002 until a ruleset file can configure them (Phase 2).
DEFAULT_REQUIRED_FIELDS = ["accession_number", "object_name"]


@app.callback()
def _main() -> None:
    """Collection Integrity CI: a local-first data-QA layer for museum collection records."""


@app.command()
def scan(
    objects_csv: Annotated[
        Path | None,
        typer.Option(help="Path to an objects CSV with canonical column names (simple path)."),
    ] = None,
    mapping: Annotated[
        Path | None,
        typer.Option(help="Path to a dataset-mapping YAML (configurable CSV/JSON ingestion)."),
    ] = None,
    output_dir: Annotated[Path, typer.Option(help="Directory to write findings.json into.")] = Path(
        "build/scan"
    ),
    fail_on: Annotated[
        str,
        typer.Option(help="Minimum severity that fails the run: critical|high|medium|low|none."),
    ] = "critical",
    required_field: Annotated[
        list[str] | None,
        typer.Option(
            help=(
                "Object field required by policy (repeatable). Defaults to accession_number and "
                f"object_name. Allowed: {', '.join(REQUIRABLE_OBJECT_FIELDS)}."
            )
        ),
    ] = None,
) -> None:
    """Scan collection objects and report deterministic integrity findings.

    Provide exactly one input: --objects-csv (canonical columns) or --mapping (a dataset-mapping
    YAML that describes an arbitrary CSV/JSON export).
    """
    if fail_on not in {*SEVERITY_ORDER, "none"}:
        console.print(f"[red]Invalid --fail-on value: {fail_on!r}[/red]")
        raise typer.Exit(code=2)

    if (objects_csv is None) == (mapping is None):
        console.print("[red]Provide exactly one of --objects-csv or --mapping.[/red]")
        raise typer.Exit(code=2)

    required_fields = required_field if required_field else DEFAULT_REQUIRED_FIELDS
    unknown = [f for f in required_fields if f not in REQUIRABLE_OBJECT_FIELDS]
    if unknown:
        console.print(f"[red]Unknown required field(s): {unknown}[/red]")
        raise typer.Exit(code=2)

    try:
        objects, media, rights = _load_entities(objects_csv, mapping)
    except (CsvIngestionError, IngestionError, FileNotFoundError, KeyError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    registry = RuleRegistry.with_defaults()
    ctx = RuleContext(objects=objects, media=media, rights=rights, required_fields=required_fields)
    findings = registry.evaluate(ctx)

    output_dir.mkdir(parents=True, exist_ok=True)
    findings_path = output_dir / "findings.json"
    findings_path.write_text(
        json.dumps([f.model_dump(mode="json") for f in findings], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    _print_console_summary(objects, findings)
    console.print(f"\nWrote {len(findings)} finding(s) to [bold]{findings_path}[/bold]")

    if fail_on == "none":
        raise typer.Exit(code=0)
    threshold = SEVERITY_ORDER[fail_on]
    if any(SEVERITY_ORDER[f.severity] >= threshold for f in findings):
        raise typer.Exit(code=1)
    raise typer.Exit(code=0)


def _load_entities(
    objects_csv: Path | None, mapping_path: Path | None
) -> tuple[list[CollectionObject], list[MediaAsset], list[RightsRecord]]:
    """Load objects, plus media/rights when the mapping defines those entities."""
    if objects_csv is not None:
        if not objects_csv.exists():
            raise FileNotFoundError(f"Input file not found: {objects_csv}")
        return load_objects_from_csv(objects_csv, source_name=objects_csv.stem), [], []

    assert mapping_path is not None  # guaranteed by the caller's exactly-one check
    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_path}")
    mapping = load_mapping(mapping_path)
    base = mapping_path.parent
    objects = load_objects(mapping, base_dir=base)
    media = load_media(mapping, base_dir=base) if has_entity(mapping, "media") else []
    rights = load_rights(mapping, base_dir=base) if has_entity(mapping, "rights") else []
    return objects, media, rights


def _print_console_summary(objects: list, findings: list) -> None:  # type: ignore[type-arg]
    console.print(f"Scanned {len(objects)} object record(s).")
    if not findings:
        console.print("[green]No findings.[/green]")
        return

    table = Table(title="Findings")
    table.add_column("Rule")
    table.add_column("Severity")
    table.add_column("Summary")
    for finding in findings:
        table.add_row(finding.rule.id, finding.severity, finding.summary)
    console.print(table)


if __name__ == "__main__":
    app()
