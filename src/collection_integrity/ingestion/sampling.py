"""Bounded sampling of source exports (BUILD_BRIEF.md Section 24, Phase 4; Section 20 safety).

The museum open-data exports are large (the Met's `MetObjects.csv` is hundreds of MB). The brief is
explicit: never download an entire large dataset automatically — provide `--limit` and explicit
paths. The safety guarantee therefore lives in one place, `take_bounded_lines`, which stops after a
bounded number of records regardless of how large (or infinite) the input is. Both the local-file
and the network sample paths in `scripts/fetch_sample.py` route through it, so the same tested bound
governs both. Nothing here writes to a source file; sampling only reads and writes a new subset.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path


def take_bounded_lines(lines: Iterable[str], limit: int) -> list[str]:
    """Return the header line plus at most `limit` data lines, consuming no more than needed.

    This is the safety boundary: given an arbitrarily large or even unbounded line iterator, it
    reads at most `limit + 2` lines and returns. `limit` counts data rows, not the header.
    """
    if limit < 0:
        raise ValueError("limit must be non-negative")
    iterator = iter(lines)
    try:
        header = next(iterator)
    except StopIteration:
        return []
    out = [header]
    for index, line in enumerate(iterator):
        if index >= limit:
            break
        out.append(line)
    return out


def bound_csv_text(text: str, limit: int) -> str:
    """Bound a CSV document (as text) to its header plus the first `limit` data rows."""
    kept = take_bounded_lines(text.splitlines(), limit)
    return "\n".join(kept) + ("\n" if kept else "")


def _read_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        rows = [{k: (v or "") for k, v in row.items() if k is not None} for row in reader]
    return fieldnames, rows


def _write_table(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def bound_nga_directory(src_dir: Path, out_dir: Path, limit: int) -> dict[str, int]:
    """Write a referentially-consistent bounded NGA sample: the first `limit` objects, only the link
    rows that reference them, and only the constituents those links reference.

    Returns the row counts written per file. Unlike single-file bounding, a relational sample must
    prune the link table and constituents so the subset ingests cleanly with no dangling references.
    """
    if limit < 0:
        raise ValueError("limit must be non-negative")
    out_dir.mkdir(parents=True, exist_ok=True)

    obj_fields, obj_rows = _read_table(src_dir / "objects.csv")
    kept_objects = obj_rows[:limit]
    kept_ids = {r["objectid"] for r in kept_objects}

    link_fields, link_rows = _read_table(src_dir / "objects_constituents.csv")
    kept_links = [r for r in link_rows if r.get("objectid", "") in kept_ids]
    referenced = {r["constituentid"] for r in kept_links if r.get("constituentid")}

    con_fields, con_rows = _read_table(src_dir / "constituents.csv")
    kept_constituents = [r for r in con_rows if r.get("constituentid", "") in referenced]

    _write_table(out_dir / "objects.csv", obj_fields, kept_objects)
    _write_table(out_dir / "objects_constituents.csv", link_fields, kept_links)
    _write_table(out_dir / "constituents.csv", con_fields, kept_constituents)
    return {
        "objects": len(kept_objects),
        "objects_constituents": len(kept_links),
        "constituents": len(kept_constituents),
    }
