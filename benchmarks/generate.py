"""Regenerate the committed mini benchmark artifacts.

Deterministic: running this with the same seeds always reproduces the same files. Run from the
repo root with `uv run python benchmarks/generate.py`. Artifacts are small and committed so the
benchmark is reproducible without a generation step; regenerate only when the generator or
injectors change.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from collection_integrity.benchmark.dataset import write_objects_csv
from collection_integrity.benchmark.injectors import inject_errors
from collection_integrity.benchmark.synthetic import OBJECT_COLUMNS, generate_clean_objects

CLEAN_SEED = 7
INJECT_SEED = 11
COUNT = 60

ROOT = Path(__file__).parent
CLEAN_CSV = ROOT / "mini" / "objects_clean.csv"
DIRTY_CSV = ROOT / "mini" / "objects_dirty.csv"
MANIFEST = ROOT / "manifests" / "mini.json"


def main() -> None:
    clean = generate_clean_objects(count=COUNT, seed=CLEAN_SEED)
    dirty, manifest = inject_errors(
        clean, seed=INJECT_SEED, num_duplicate_accession=4, num_missing_field=4
    )

    write_objects_csv(clean, CLEAN_CSV, OBJECT_COLUMNS)
    write_objects_csv(dirty, DIRTY_CSV, OBJECT_COLUMNS)

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(
            {
                "clean_seed": CLEAN_SEED,
                "inject_seed": INJECT_SEED,
                "count": COUNT,
                "errors": [dataclasses.asdict(e) for e in manifest.errors],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {CLEAN_CSV}, {DIRTY_CSV}, {MANIFEST} ({len(manifest.errors)} injected errors)")


if __name__ == "__main__":
    main()
