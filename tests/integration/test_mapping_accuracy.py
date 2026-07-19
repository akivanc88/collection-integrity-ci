"""Slice B accuracy validation: the configurable mapping path (CSV and JSON) recovers the same
injected errors, at precision = recall = 1.0, as the direct CSV path.

Uses the AI-generated synthetic dataset, writes it through a renamed-column schema in both CSV and
JSON, ingests via a dataset mapping, and scores against the injection manifest.
"""

from pathlib import Path

from collection_integrity.benchmark.dataset import write_objects_csv, write_objects_json
from collection_integrity.benchmark.injectors import inject_errors
from collection_integrity.benchmark.metrics import score
from collection_integrity.benchmark.synthetic import generate_clean_objects
from collection_integrity.ingestion.mapper import load_mapping, load_objects
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.registry import RuleRegistry

REQUIRED_FIELDS = ["accession_number", "object_name"]

# Source columns are deliberately renamed away from the canonical names to exercise the mapping.
RENAMED_COLUMNS = ("oid", "acc", "ttl", "otype", "dept")


def _rename(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "oid": r["object_id"],
            "acc": r["accession_number"],
            "ttl": r["title"],
            "otype": r["object_name"],
            "dept": r["department"],
        }
        for r in rows
    ]


def _mapping_yaml(fmt: str, data_file: str) -> str:
    return (
        "version: 1\n"
        f"dataset:\n  name: bench-{fmt}\n  format: {fmt}\n  base_path: .\n"
        "entities:\n  objects:\n"
        f"    file: {data_file}\n"
        "    primary_key: object_id\n"
        "    fields:\n"
        "      object_id: oid\n"
        "      accession_number: acc\n"
        "      title: ttl\n"
        "      object_name: otype\n"
    )


def _score_via_mapping(mapping_path: Path, base_dir: Path, manifest) -> dict:  # type: ignore[type-arg]
    mapping = load_mapping(mapping_path)
    objects = load_objects(mapping, base_dir=base_dir)
    ctx = RuleContext(objects=objects, required_fields=REQUIRED_FIELDS)
    findings = RuleRegistry.with_defaults().evaluate(ctx)
    return score(findings, manifest)


def test_mapping_path_matches_ground_truth_for_csv_and_json(tmp_path: Path) -> None:
    clean = generate_clean_objects(count=60, seed=7)
    dirty, manifest = inject_errors(clean, seed=11, num_duplicate_accession=4, num_missing_field=4)
    renamed = _rename(dirty)

    write_objects_csv(renamed, tmp_path / "objects.csv", RENAMED_COLUMNS)
    write_objects_json(renamed, tmp_path / "objects.json", RENAMED_COLUMNS)
    (tmp_path / "map_csv.yaml").write_text(_mapping_yaml("csv", "objects.csv"), encoding="utf-8")
    (tmp_path / "map_json.yaml").write_text(_mapping_yaml("json", "objects.json"), encoding="utf-8")

    for mapping_name in ("map_csv.yaml", "map_json.yaml"):
        metrics = _score_via_mapping(tmp_path / mapping_name, tmp_path, manifest)
        for rule_id, m in metrics.items():
            assert m.precision == 1.0, f"{mapping_name} {rule_id} precision {m.precision}"
            assert m.recall == 1.0, f"{mapping_name} {rule_id} recall {m.recall}"
