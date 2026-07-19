"""Regenerate the committed clean and dirty example datasets.

Deterministic: same seeds reproduce the same files. Run from the repo root:
`uv run python examples/generate.py`. The clean dataset passes every enabled check; the dirty one
has labeled, injected errors for the rules that fire through the default CLI mapping path
(CORE001, CORE002, DATE001, SCHEMA001 — VOCAB001 needs a vocabulary config and is exercised in the
benchmark instead).
"""

from __future__ import annotations

import json
from pathlib import Path

from collection_integrity.benchmark.dataset import write_objects_csv
from collection_integrity.benchmark.injectors import inject_errors, inject_object_field_errors
from collection_integrity.benchmark.synthetic import (
    OBJECT_WITH_DATES_COLUMNS,
    add_dates_and_status,
    generate_clean_objects,
)

ROOT = Path(__file__).parent
COUNT = 250
CLEAN_SEED = 101
INJECT_SEED = 202

MAPPING = """version: 1
dataset:
  name: {name}
  format: csv
  base_path: {base_path}
entities:
  objects:
    file: objects.csv
    primary_key: object_id
    fields:
      object_id: object_id
      accession_number: accession_number
      object_name: object_name
      title: title
      publication_status: publication_status
      production_start_date: production_start_date
      production_end_date: production_end_date
"""


def main() -> None:
    clean = add_dates_and_status(generate_clean_objects(count=COUNT, seed=CLEAN_SEED), seed=5)

    dirty, manifest = inject_errors(
        clean, seed=INJECT_SEED, num_duplicate_accession=5, num_missing_field=5
    )
    dirty, field_errors = inject_object_field_errors(
        dirty, seed=INJECT_SEED + 1, num_inverted_date=5, num_bad_vocab=0, num_bad_type=5
    )
    manifest.errors.extend(field_errors)

    write_objects_csv(clean, ROOT / "clean" / "objects.csv", OBJECT_WITH_DATES_COLUMNS)
    write_objects_csv(dirty, ROOT / "dirty" / "objects.csv", OBJECT_WITH_DATES_COLUMNS)
    (ROOT / "mappings").mkdir(parents=True, exist_ok=True)
    (ROOT / "mappings" / "clean.yaml").write_text(
        MAPPING.format(name="example-clean", base_path="../clean"), "utf-8"
    )
    (ROOT / "mappings" / "dirty.yaml").write_text(
        MAPPING.format(name="example-dirty", base_path="../dirty"), "utf-8"
    )

    expected_counts: dict[str, int] = {}
    for err in manifest.errors:
        expected_counts[err.expected_rule_id] = expected_counts.get(err.expected_rule_id, 0) + 1
    (ROOT / "expected").mkdir(parents=True, exist_ok=True)
    (ROOT / "expected" / "dirty_expected.json").write_text(
        json.dumps(
            {
                "object_count": COUNT,
                "expected_findings_by_rule": dict(sorted(expected_counts.items())),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote clean ({COUNT}) + dirty examples; expected: {sorted(expected_counts.items())}")


if __name__ == "__main__":
    main()
