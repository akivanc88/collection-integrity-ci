"""Command-line interface.

The `scan` command ingests objects either directly from a canonical-column CSV (--objects-csv) or
through a configurable dataset-mapping YAML that describes an arbitrary CSV/JSON export (--mapping,
which can also define media/rights/locations/agents entities), runs the enabled deterministic rules
through the rule registry, and can persist a run summary (--run-store). This is an early Phase 2
shape, not the full CLI specification in Section 13 — per-rule enable/disable via a ruleset file and
the CSV/HTML/SARIF/manifest report formats are tracked in docs/BACKLOG.md.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from collection_integrity.canonical.models import (
    AgentOrMaker,
    CollectionObject,
    LocationRecord,
    MediaAsset,
    RightsRecord,
)
from collection_integrity.engine.baselines import (
    BaselineError,
    classify,
    load_baseline_fingerprints,
)
from collection_integrity.engine.run_manifest import build_run_manifest, manifest_to_dict
from collection_integrity.engine.run_store import RunStore, summarize
from collection_integrity.ingestion.csv_adapter import CsvIngestionError, load_objects_from_csv
from collection_integrity.ingestion.mapper import (
    has_entity,
    load_agents,
    load_locations,
    load_mapping,
    load_media,
    load_objects,
    load_rights,
    object_field_sources,
    resolve_entity_files,
)
from collection_integrity.ingestion.readers import IngestionError
from collection_integrity.reporting.csv_report import write_findings_csv
from collection_integrity.reporting.html_report import write_html_report
from collection_integrity.reporting.json_report import write_findings_json
from collection_integrity.reporting.sarif_report import write_sarif_report
from collection_integrity.reporting.summary import write_summary_json
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
    media_root: Annotated[
        Path | None,
        typer.Option(help="Enable local media-file checks (MEDIA001-004), resolving paths here."),
    ] = None,
    min_image_width: Annotated[
        int, typer.Option(help="Minimum image width for MEDIA003 (0 disables).")
    ] = 0,
    min_image_height: Annotated[
        int, typer.Option(help="Minimum image height for MEDIA003 (0 disables).")
    ] = 0,
    run_store: Annotated[
        Path | None,
        typer.Option(help="Persist this run's summary + fingerprints under this directory."),
    ] = None,
    baseline: Annotated[
        Path | None,
        typer.Option(
            help="A prior findings.json to compare against (classify new/unchanged/resolved)."
        ),
    ] = None,
    only_new: Annotated[
        bool,
        typer.Option(
            "--only-new", help="With --baseline, the fail threshold considers only new findings."
        ),
    ] = False,
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

    started = time.monotonic()
    started_at = datetime.now(UTC).isoformat()
    run_id = uuid.uuid4().hex

    required_fields = required_field if required_field else DEFAULT_REQUIRED_FIELDS
    unknown = [f for f in required_fields if f not in REQUIRABLE_OBJECT_FIELDS]
    if unknown:
        console.print(f"[red]Unknown required field(s): {unknown}[/red]")
        raise typer.Exit(code=2)

    try:
        objects, media, rights, locations, agents, field_sources = _load_entities(
            objects_csv, mapping
        )
    except (CsvIngestionError, IngestionError, FileNotFoundError, KeyError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    if media_root is not None and not media_root.exists():
        console.print(f"[red]Media root not found: {media_root}[/red]")
        raise typer.Exit(code=2)

    registry = RuleRegistry.with_defaults()
    ctx = RuleContext(
        objects=objects,
        media=media,
        rights=rights,
        locations=locations,
        agents=agents,
        required_fields=required_fields,
        object_field_sources=field_sources,
        check_media_files=media_root is not None,
        media_root=media_root,
        min_image_width=min_image_width,
        min_image_height=min_image_height,
    )
    findings = registry.evaluate(ctx)
    ended_at = datetime.now(UTC).isoformat()
    elapsed = time.monotonic() - started

    input_counts = {
        "objects": len(objects),
        "media": len(media),
        "rights": len(rights),
        "locations": len(locations),
        "agents": len(agents),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    write_findings_json(findings, output_dir / "findings.json")
    write_findings_csv(findings, output_dir / "findings.csv")
    write_summary_json(findings, input_counts, output_dir / "summary.json")

    input_files, config_files = _report_source_files(objects_csv, mapping)
    manifest = build_run_manifest(
        command="collection-ci scan",
        run_id=run_id,
        started_at=started_at,
        ended_at=ended_at,
        elapsed_seconds=elapsed,
        input_files=input_files,
        config_files=config_files,
        enabled_rules=[(r.rule.id, r.rule.version) for r in registry.enabled_rules()],
        findings=findings,
    )
    manifest_dict = manifest_to_dict(manifest)
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest_dict, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_html_report(findings, manifest_dict, input_counts, output_dir / "report.html")
    write_sarif_report(
        findings,
        [(r.rule.id, r.rule.name, r.rule.version) for r in registry.enabled_rules()],
        output_dir / "results.sarif",
    )

    # Findings that count toward the failure threshold: all, or only-new against a baseline.
    threshold_findings = findings
    if baseline is not None:
        try:
            baseline_fps = load_baseline_fingerprints(baseline)
        except BaselineError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=2) from exc
        comparison = classify(findings, baseline_fps)
        console.print(
            f"Baseline: [bold]{comparison.counts['new']}[/bold] new, "
            f"{comparison.counts['unchanged']} unchanged, "
            f"{comparison.counts['resolved']} resolved."
        )
        _write_baseline_summary(comparison, output_dir / "baseline_comparison.json")
        if only_new:
            threshold_findings = comparison.new

    _print_console_summary(objects, findings)
    console.print(f"\nWrote {len(findings)} finding(s) to [bold]{output_dir}[/bold]")

    if run_store is not None:
        record_path = RunStore(run_store).save(summarize(findings, run_id=run_id))
        console.print(f"Recorded run to [bold]{record_path}[/bold]")

    if fail_on == "none":
        raise typer.Exit(code=0)
    threshold = SEVERITY_ORDER[fail_on]
    if any(SEVERITY_ORDER[f.severity] >= threshold for f in threshold_findings):
        raise typer.Exit(code=1)
    raise typer.Exit(code=0)


def _write_baseline_summary(comparison: object, path: Path) -> None:
    from collection_integrity.engine.baselines import BaselineComparison

    assert isinstance(comparison, BaselineComparison)
    payload = {
        "counts": comparison.counts,
        "new_fingerprints": sorted(f.fingerprint for f in comparison.new),
        "resolved_fingerprints": sorted(comparison.resolved_fingerprints),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@app.command()
def benchmark(
    output_dir: Annotated[
        Path, typer.Option(help="Directory to write benchmark_report.json into.")
    ] = Path("benchmarks/reports/latest"),
    seed: Annotated[int, typer.Option(help="Random seed (reproducible).")] = 42,
    count: Annotated[int, typer.Option(help="Number of synthetic objects.")] = 60,
) -> None:
    """Run the deterministic benchmark and report precision/recall/F1 per rule."""
    from collection_integrity.benchmark.runner import run_benchmark

    result = run_benchmark(count=count, seed=seed)

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "benchmark_report.json"
    report_path.write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    table = Table(title=f"Benchmark (seed {seed}, {count} objects)")
    table.add_column("Rule")
    table.add_column("Precision", justify="right")
    table.add_column("Recall", justify="right")
    table.add_column("F1", justify="right")
    for rule_id, m in result.per_rule.items():
        table.add_row(rule_id, f"{m['precision']:.2f}", f"{m['recall']:.2f}", f"{m['f1']:.2f}")
    console.print(table)
    console.print(
        f"Runtime {result.runtime_seconds:.4f}s | {result.total_findings} findings | "
        f"meets target: {'yes' if result.meets_target else 'no'}"
    )
    console.print(f"Wrote [bold]{report_path}[/bold]")
    raise typer.Exit(code=0 if result.meets_target else 1)


def _load_entities(
    objects_csv: Path | None, mapping_path: Path | None
) -> tuple[
    list[CollectionObject],
    list[MediaAsset],
    list[RightsRecord],
    list[LocationRecord],
    list[AgentOrMaker],
    dict[str, str],
]:
    """Load objects, plus media/rights/locations/agents when the mapping defines those entities.

    Also returns the objects entity's canonical->source field map, which SCHEMA001 uses to report
    the offending raw value.
    """
    if objects_csv is not None:
        if not objects_csv.exists():
            raise FileNotFoundError(f"Input file not found: {objects_csv}")
        # In the simple CSV path source columns already carry canonical names.
        return load_objects_from_csv(objects_csv, source_name=objects_csv.stem), [], [], [], [], {}

    assert mapping_path is not None  # guaranteed by the caller's exactly-one check
    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_path}")
    mapping = load_mapping(mapping_path)
    base = mapping_path.parent
    objects = load_objects(mapping, base_dir=base)
    media = load_media(mapping, base_dir=base) if has_entity(mapping, "media") else []
    rights = load_rights(mapping, base_dir=base) if has_entity(mapping, "rights") else []
    locations = load_locations(mapping, base_dir=base) if has_entity(mapping, "locations") else []
    agents = load_agents(mapping, base_dir=base) if has_entity(mapping, "agents") else []
    return objects, media, rights, locations, agents, object_field_sources(mapping)


def _report_source_files(
    objects_csv: Path | None, mapping_path: Path | None
) -> tuple[list[Path], list[Path]]:
    """(input data files, config files) to hash into the run manifest."""
    if objects_csv is not None:
        return [objects_csv], []
    assert mapping_path is not None
    mapping = load_mapping(mapping_path)
    return resolve_entity_files(mapping, mapping_path.parent), [mapping_path]


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
