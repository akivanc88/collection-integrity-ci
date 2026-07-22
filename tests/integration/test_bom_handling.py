"""Regression: a UTF-8 BOM must not break the first mapped column.

Real-world CSV exports (Excel, and several museum open-data files including the Met's
`MetObjects.csv`) begin with a UTF-8 byte-order mark. Before the fix, the BOM bound to the first
header name (`"﻿Object Number"` instead of `"Object Number"`), so any mapping keyed on that
column silently matched nothing and every row was reported as missing that field — mass false
positives on otherwise-clean data. The readers now decode with utf-8-sig.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from collection_integrity.cli import app

runner = CliRunner()


def test_bom_prefixed_first_column_is_mapped(tmp_path: Path) -> None:
    # First column carries a BOM and is the required accession_number. With correct BOM handling,
    # the value is read and NO "required field missing" finding is produced for it.
    src = tmp_path / "bom.csv"
    src.write_bytes(
        b"\xef\xbb\xbfobject_id,accession_number,object_name\n"
        b"OBJ-1,1999.1,Vase\n"
        b"OBJ-2,1999.2,Bowl\n"
    )
    result = runner.invoke(
        app,
        [
            "scan",
            "--objects-csv",
            str(src),
            "--output-dir",
            str(tmp_path / "out"),
            "--fail-on",
            "none",
        ],
    )
    assert result.exit_code == 0, result.output
    findings = json.loads((tmp_path / "out" / "findings.json").read_text())
    # No accession_number should be reported missing — the BOM'd column was mapped correctly.
    missing_accession = [
        f
        for f in findings
        if f["rule"]["id"].startswith("CORE002") and f["entity"].get("field") == "accession_number"
    ]
    assert missing_accession == [], f"BOM broke first-column mapping: {missing_accession}"


def test_bom_prefixed_met_source_maps_accession(tmp_path: Path) -> None:
    # The Met adapter keys accession_number on "Object Number" (the first column, which carries the
    # BOM in the real export). A minimal BOM'd Met-shaped file must map it, not flag it missing.
    src = tmp_path / "met.csv"
    src.write_bytes(
        b"\xef\xbb\xbfObject Number,Object ID,Object Name,Title,"
        b"Object Begin Date,Object End Date\n"
        b"1979.486.1,1,Vase,Untitled,1900,1901\n"
    )
    result = runner.invoke(
        app,
        [
            "scan",
            "--source",
            "met",
            "--input",
            str(src),
            "--output-dir",
            str(tmp_path / "out"),
            "--fail-on",
            "none",
        ],
    )
    assert result.exit_code == 0, result.output
    findings = json.loads((tmp_path / "out" / "findings.json").read_text())
    missing_accession = [
        f
        for f in findings
        if f["rule"]["id"].startswith("CORE002") and f["entity"].get("field") == "accession_number"
    ]
    assert missing_accession == [], f"BOM broke Met accession mapping: {missing_accession}"
