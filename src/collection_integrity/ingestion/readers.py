"""Raw record readers for supported source formats.

Each reader returns a list of `(row_number, raw_fields)` pairs where `raw_fields` maps source
column/key names to string values, preserving the original values for provenance. Row numbers are
1-based and, for CSV, count the header as row 1 (so the first data row is row 2), matching what a
spreadsheet shows. For JSON, row numbers are the 1-based position in the array.

These readers do no canonical mapping — that is `mapper.py`'s job.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

RawRecord = tuple[int, dict[str, str]]


class IngestionError(ValueError):
    """Raised when a source file cannot be read into raw records."""


def read_csv_rows(path: Path) -> list[RawRecord]:
    # Decoding and CSV parsing both happen lazily while iterating, so malformed bytes surface here
    # rather than at open(). Translate them into IngestionError so the CLI reports invalid input
    # (exit 2) instead of crashing with an unhandled traceback (VL-05 contract).
    try:
        # utf-8-sig strips a leading byte-order mark if present (Excel and many museum exports emit
        # one). Without this the BOM binds to the first header name, so a mapping keyed on that
        # column silently matches nothing — see the BOM regression test.
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                raise IngestionError(f"{path}: no header row")
            records: list[RawRecord] = []
            for row_number, row in enumerate(reader, start=2):
                records.append(
                    (row_number, {k: (v or "") for k, v in row.items() if k is not None})
                )
            return records
    except UnicodeDecodeError as exc:
        raise IngestionError(f"{path}: not valid UTF-8 text: {exc}") from exc
    except csv.Error as exc:
        raise IngestionError(f"{path}: malformed CSV: {exc}") from exc


def read_json_rows(path: Path) -> list[RawRecord]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise IngestionError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise IngestionError(f"{path}: expected a JSON array of records")

    records: list[RawRecord] = []
    for position, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise IngestionError(f"{path}: record {position} is not a JSON object")
        # Stringify scalar values so downstream mapping/transforms see a consistent type; the raw
        # string is what gets preserved for provenance.
        raw = {str(k): _stringify(v) for k, v in item.items()}
        records.append((position, raw))
    return records


def read_rows(path: Path, fmt: str) -> list[RawRecord]:
    if fmt == "csv":
        return read_csv_rows(path)
    if fmt == "json":
        return read_json_rows(path)
    raise IngestionError(f"unsupported format: {fmt!r}")


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
