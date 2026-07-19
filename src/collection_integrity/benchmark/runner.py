"""Benchmark runner (BUILD_BRIEF.md Section 13, 16).

Ties the synthetic generator, injectors, engine, and scorer into one reproducible measurement:
generate a clean dataset, inject labeled errors, scan, and score precision/recall/F1 per rule
against the ground-truth manifest. Deterministic by seed. This covers the object-level rules
(CORE001/002, DATE001, VOCAB001, SCHEMA001); multi-entity benchmark coverage is tracked in
docs/BACKLOG.md.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from collection_integrity.benchmark.injectors import inject_errors, inject_object_field_errors
from collection_integrity.benchmark.metrics import score
from collection_integrity.benchmark.synthetic import (
    PUBLICATION_VOCABULARY,
    add_dates_and_status,
    generate_clean_objects,
)
from collection_integrity.canonical.models import CollectionObject, SourceRef
from collection_integrity.ingestion.mapper import parse_date
from collection_integrity.provenance import hash_record
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.registry import RuleRegistry

BENCHMARK_RULES = (
    "CORE001_DUPLICATE_ACCESSION_NUMBER",
    "CORE002_REQUIRED_FIELD_MISSING",
    "DATE001_INVERTED_DATE_RANGE",
    "VOCAB001_UNKNOWN_CONTROLLED_VALUE",
    "SCHEMA001_INVALID_FIELD_TYPE",
)
_VOCAB = {"publication_status": PUBLICATION_VOCABULARY}
_FIELD_SOURCES = {
    "production_start_date": "production_start_date",
    "production_end_date": "production_end_date",
}


@dataclass(frozen=True)
class BenchmarkResult:
    seed: int
    object_count: int
    runtime_seconds: float
    total_findings: int
    per_rule: dict[str, dict[str, float]]

    @property
    def meets_target(self) -> bool:
        """Target: precision and recall of 1.0 for every benchmarked rule."""
        return all(m["precision"] == 1.0 and m["recall"] == 1.0 for m in self.per_rule.values())

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "object_count": self.object_count,
            "runtime_seconds": round(self.runtime_seconds, 6),
            "total_findings": self.total_findings,
            "meets_target": self.meets_target,
            "per_rule": self.per_rule,
        }


def _rows_to_objects(rows: list[dict[str, str]]) -> list[CollectionObject]:
    objects: list[CollectionObject] = []
    for i, row in enumerate(rows, start=2):
        objects.append(
            CollectionObject(
                object_id=row["object_id"],
                accession_number=(row.get("accession_number") or "").strip() or None,
                title=(row.get("title") or "").strip() or None,
                object_name=(row.get("object_name") or "").strip() or None,
                publication_status=(row.get("publication_status") or "").strip() or None,
                production_start_date=parse_date(row.get("production_start_date", "")),
                production_end_date=parse_date(row.get("production_end_date", "")),
                source_ref=SourceRef(
                    source_name="benchmark",
                    source_file="benchmark.csv",
                    source_record_id=row["object_id"],
                    source_row_number=i,
                    source_hash=hash_record(row),
                    ingested_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
                    raw_fields=row,
                ),
            )
        )
    return objects


def run_benchmark(count: int = 60, seed: int = 42, per_rule_errors: int = 4) -> BenchmarkResult:
    clean = generate_clean_objects(count=count, seed=seed)
    dated = add_dates_and_status(clean, seed=seed + 1)
    dirty, manifest = inject_errors(
        dated,
        seed=seed + 2,
        num_duplicate_accession=per_rule_errors,
        num_missing_field=per_rule_errors,
    )
    dirty, field_errors = inject_object_field_errors(
        dirty,
        seed=seed + 3,
        num_inverted_date=per_rule_errors,
        num_bad_vocab=per_rule_errors,
        num_bad_type=per_rule_errors,
    )
    manifest.errors.extend(field_errors)

    objects = _rows_to_objects(dirty)
    ctx = RuleContext(
        objects=objects,
        required_fields=["accession_number", "object_name"],
        controlled_vocabularies=_VOCAB,
        object_field_sources=_FIELD_SOURCES,
    )

    start = time.monotonic()
    findings = RuleRegistry.with_defaults().evaluate(ctx)
    runtime = time.monotonic() - start

    metrics = score(findings, manifest)
    per_rule = {
        rid: {
            "precision": metrics[rid].precision,
            "recall": metrics[rid].recall,
            "f1": metrics[rid].f1,
            "true_positives": float(metrics[rid].true_positives),
            "false_positives": float(metrics[rid].false_positives),
            "false_negatives": float(metrics[rid].false_negatives),
        }
        for rid in BENCHMARK_RULES
    }
    return BenchmarkResult(
        seed=seed,
        object_count=count,
        runtime_seconds=runtime,
        total_findings=len(findings),
        per_rule=per_rule,
    )
