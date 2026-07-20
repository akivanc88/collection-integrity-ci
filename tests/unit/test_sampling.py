"""Tests for bounded source sampling (Phase 4, Slice R).

The safety-critical property is that sampling is bounded regardless of input size — verified here by
feeding an *infinite* line generator and asserting the bounder returns. Relational NGA sampling must
also stay referentially consistent so the subset re-ingests with no dangling references.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from collection_integrity.benchmark.source_fixtures import write_nga_dataset
from collection_integrity.ingestion.sampling import (
    bound_csv_text,
    bound_nga_directory,
    take_bounded_lines,
)
from collection_integrity.ingestion.sources import load_source


def test_take_bounded_lines_keeps_header_plus_limit() -> None:
    lines = ["header", "a", "b", "c", "d"]
    assert take_bounded_lines(lines, 2) == ["header", "a", "b"]


def test_take_bounded_lines_stops_on_infinite_stream() -> None:
    def infinite() -> Iterator[str]:
        yield "header"
        i = 0
        while True:
            yield f"row{i}"
            i += 1

    result = take_bounded_lines(infinite(), 5)  # must return, not hang
    assert result == ["header", "row0", "row1", "row2", "row3", "row4"]


def test_take_bounded_lines_empty_and_negative() -> None:
    assert take_bounded_lines([], 10) == []
    with pytest.raises(ValueError, match="non-negative"):
        take_bounded_lines(["header"], -1)


def test_bound_csv_text_roundtrips_header() -> None:
    text = "col1,col2\n1,2\n3,4\n5,6\n"
    assert bound_csv_text(text, 1) == "col1,col2\n1,2\n"
    assert bound_csv_text(text, 0) == "col1,col2\n"


def test_bound_nga_directory_is_referentially_consistent(tmp_path: Path) -> None:
    src = tmp_path / "full"
    out = tmp_path / "sample"
    write_nga_dataset(src, clean_count=30, injected_per_rule=3)

    counts = bound_nga_directory(src, out, limit=10)
    assert counts["objects"] == 10

    _, obj_rows = _read(out / "objects.csv")
    _, link_rows = _read(out / "objects_constituents.csv")
    _, con_rows = _read(out / "constituents.csv")
    kept_objects = {r["objectid"] for r in obj_rows}
    kept_constituents = {r["constituentid"] for r in con_rows}

    # No dangling references: every link points at a kept object and a kept constituent.
    assert all(r["objectid"] in kept_objects for r in link_rows)
    assert all(r["constituentid"] in kept_constituents for r in link_rows)
    # No orphan constituents: every kept constituent is referenced by a kept link.
    referenced = {r["constituentid"] for r in link_rows}
    assert kept_constituents == referenced


def test_bounded_nga_sample_reingests_through_adapter(tmp_path: Path) -> None:
    src = tmp_path / "full"
    out = tmp_path / "sample"
    write_nga_dataset(src, clean_count=30, injected_per_rule=3)
    bound_nga_directory(src, out, limit=8)

    loaded = load_source("nga", out)
    assert len(loaded.objects) == 8
    agent_ids = {a.agent_id for a in loaded.agents}
    # Every maker link in the sample resolves to a kept constituent (no dangling maker).
    for obj in loaded.objects:
        assert all(mid in agent_ids for mid in obj.maker_ids)


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    import csv

    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)
