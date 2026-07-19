"""Slice E accuracy validation: LOC001 and LOC002 on AI-generated location data.

Generates a valid location hierarchy + one current assignment per object (clean = no findings),
then injects extra current assignments, missing parents, and cycles, and confirms both rules
recover exactly the injected errors at precision = recall = 1.0.
"""

from pathlib import Path

from collection_integrity.benchmark.dataset import write_objects_csv
from collection_integrity.benchmark.injectors import (
    InjectionManifest,
    inject_extra_current_location,
    inject_location_hierarchy_errors,
)
from collection_integrity.benchmark.metrics import score
from collection_integrity.benchmark.synthetic import (
    LOCATION_COLUMNS,
    OBJECT_COLUMNS,
    generate_clean_locations,
    generate_clean_objects,
)
from collection_integrity.ingestion.mapper import load_locations, load_mapping, load_objects
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.registry import RuleRegistry

MAPPING = """version: 1
dataset:
  name: bench-locations
  format: csv
  base_path: .
entities:
  objects:
    file: objects.csv
    primary_key: object_id
    fields:
      object_id: object_id
      accession_number: accession_number
      object_name: object_name
      title: title
  locations:
    file: locations.csv
    primary_key: location_id
    fields:
      location_id: location_id
      name: name
      parent_location_id: parent_location_id
      object_id: object_id
      is_current: is_current
"""


def _scan(tmp_path: Path, objects: list, locations: list) -> list:  # type: ignore[type-arg]
    write_objects_csv(objects, tmp_path / "objects.csv", OBJECT_COLUMNS)
    write_objects_csv(locations, tmp_path / "locations.csv", LOCATION_COLUMNS)
    (tmp_path / "map.yaml").write_text(MAPPING, encoding="utf-8")
    mapping = load_mapping(tmp_path / "map.yaml")
    ctx = RuleContext(
        objects=load_objects(mapping, base_dir=tmp_path),
        locations=load_locations(mapping, base_dir=tmp_path),
        required_fields=["accession_number", "object_name"],
    )
    return RuleRegistry.with_defaults().evaluate(ctx)


def test_clean_locations_have_no_findings(tmp_path: Path) -> None:
    objects = generate_clean_objects(count=40, seed=7)
    locations = generate_clean_locations(objects, num_nodes=15, seed=17)

    findings = _scan(tmp_path, objects, locations)

    loc = [
        f
        for f in findings
        if f.rule.id in {"LOC001_MULTIPLE_CURRENT_LOCATIONS", "LOC002_INVALID_LOCATION_HIERARCHY"}
    ]
    assert loc == [], [f.summary for f in loc]


def test_injected_location_errors_detected_with_perfect_precision_recall(tmp_path: Path) -> None:
    objects = generate_clean_objects(count=40, seed=7)
    locations = generate_clean_locations(objects, num_nodes=15, seed=17)

    locations, loc001_errors = inject_extra_current_location(locations, seed=23, num_extra=4)
    locations, loc002_errors = inject_location_hierarchy_errors(
        locations, seed=29, num_missing_parent=2, num_cycle=2
    )
    manifest = InjectionManifest(seed=23, errors=loc001_errors + loc002_errors)

    findings = _scan(tmp_path, objects, locations)
    metrics = score(findings, manifest)

    loc001 = metrics["LOC001_MULTIPLE_CURRENT_LOCATIONS"]
    assert loc001.precision == 1.0 and loc001.recall == 1.0, loc001
    assert loc001.true_positives == 4, loc001

    loc002 = metrics["LOC002_INVALID_LOCATION_HIERARCHY"]
    assert loc002.precision == 1.0 and loc002.recall == 1.0, loc002
    # 2 missing-parent + 2 cycles x 2 nodes = 6 flagged locations.
    assert loc002.true_positives == 6, loc002
