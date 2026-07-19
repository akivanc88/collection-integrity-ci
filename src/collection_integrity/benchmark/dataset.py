"""Read/write helpers for benchmark object tables."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path


def write_objects_csv(rows: list[dict[str, str]], path: Path, columns: Sequence[str]) -> None:
    """Write object rows to a CSV file with a fixed column order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})
