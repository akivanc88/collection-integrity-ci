"""Command-line interface.

Only a minimal `scan` command exists so far: it reads one objects CSV directly (no configurable
mapping yet) and runs the single implemented rule, CORE001. This is the first vertical slice from
BUILD_BRIEF.md's Kickoff Prompt, not the full CLI specification in Section 13 — the full
`--mapping`/`--rules`/multi-entity interface is Phase 2/3 work tracked in docs/BACKLOG.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from collection_integrity.ingestion.csv_adapter import CsvIngestionError, load_objects_from_csv
from collection_integrity.rules.core_rules import check_duplicate_accession_numbers

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()

SEVERITY_ORDER = {"critical": 3, "high": 2, "medium": 1, "low": 0}


@app.callback()
def _main() -> None:
    """Collection Integrity CI: a local-first data-QA layer for museum collection records."""


@app.command()
def scan(
    objects_csv: Annotated[
        Path, typer.Option(help="Path to an objects CSV file (object_id, accession_number, ...).")
    ],
    output_dir: Annotated[Path, typer.Option(help="Directory to write findings.json into.")] = Path(
        "build/scan"
    ),
    fail_on: Annotated[
        str,
        typer.Option(help="Minimum severity that fails the run: critical|high|medium|low|none."),
    ] = "critical",
) -> None:
    """Scan an objects CSV and report duplicate-accession-number findings."""
    if fail_on not in {*SEVERITY_ORDER, "none"}:
        console.print(f"[red]Invalid --fail-on value: {fail_on!r}[/red]")
        raise typer.Exit(code=2)

    if not objects_csv.exists():
        console.print(f"[red]Input file not found: {objects_csv}[/red]")
        raise typer.Exit(code=2)

    try:
        objects = load_objects_from_csv(objects_csv, source_name=objects_csv.stem)
    except CsvIngestionError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    findings = check_duplicate_accession_numbers(objects)

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
