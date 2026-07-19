"""Accuracy validation on generated datasets (VL-01, partial: implemented rules only).

Generates a clean synthetic dataset, confirms a correct engine finds nothing in it, then injects
labeled errors and confirms the engine recovers exactly those errors — precision and recall 1.0
for both CORE001 and CORE002, with zero false positives on the clean data.
"""

from pathlib import Path

from collection_integrity.benchmark.dataset import write_objects_csv
from collection_integrity.benchmark.injectors import inject_errors
from collection_integrity.benchmark.metrics import score
from collection_integrity.benchmark.synthetic import OBJECT_COLUMNS, generate_clean_objects
from collection_integrity.ingestion.csv_adapter import load_objects_from_csv
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.registry import RuleRegistry

REQUIRED_FIELDS = ["accession_number", "object_name"]


def _scan(csv_path: Path) -> list:  # type: ignore[type-arg]
    objects = load_objects_from_csv(csv_path, source_name="benchmark")
    ctx = RuleContext(objects=objects, required_fields=REQUIRED_FIELDS)
    return RuleRegistry.with_defaults().evaluate(ctx)


def test_clean_dataset_has_zero_findings(tmp_path: Path) -> None:
    rows = generate_clean_objects(count=60, seed=7)
    clean_csv = tmp_path / "clean.csv"
    write_objects_csv(rows, clean_csv, OBJECT_COLUMNS)

    findings = _scan(clean_csv)

    assert findings == [], f"clean dataset should have no findings, got {len(findings)}"


def test_injected_errors_are_detected_with_perfect_precision_and_recall(tmp_path: Path) -> None:
    clean = generate_clean_objects(count=60, seed=7)
    dirty, manifest = inject_errors(clean, seed=11, num_duplicate_accession=4, num_missing_field=4)
    dirty_csv = tmp_path / "dirty.csv"
    write_objects_csv(dirty, dirty_csv, OBJECT_COLUMNS)

    findings = _scan(dirty_csv)
    metrics = score(findings, manifest)

    for rule_id, m in metrics.items():
        assert m.precision == 1.0, f"{rule_id} precision {m.precision}: {m}"
        assert m.recall == 1.0, f"{rule_id} recall {m.recall}: {m}"
        assert m.f1 == 1.0, f"{rule_id} f1 {m.f1}: {m}"


def test_injection_does_not_mutate_input() -> None:
    clean = generate_clean_objects(count=40, seed=3)
    snapshot = [dict(r) for r in clean]

    inject_errors(clean, seed=5)

    assert clean == snapshot, "inject_errors must not modify its input rows"


def test_generation_is_deterministic_by_seed() -> None:
    a = generate_clean_objects(count=50, seed=99)
    b = generate_clean_objects(count=50, seed=99)

    assert a == b
