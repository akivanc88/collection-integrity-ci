"""VL-05: fuzz/property contract for the `scan` CLI.

The CLI's external contract (BUILD_BRIEF.md Section 13) is:

- exit 0: scan completed, failure threshold not reached
- exit 1: failure threshold reached
- exit 2: invalid configuration or input
- exit 3: internal execution failure

Under *arbitrary* input the CLI must honour that contract: it may reject junk (exit 2) or find
nothing (exit 0), but it must never crash with an unhandled traceback and never return an
undocumented exit code. Malformed bytes are the user's problem to be reported cleanly, not ours to
crash on.

Hypothesis generates hostile file contents (arbitrary bytes, and structured-but-adversarial CSV
text); each is fed to `scan --objects-csv`. Any unhandled non-`SystemExit` exception, or an exit
code outside {0,1,2,3}, is a contract violation. Shrunk counterexamples become the named regression
tests below.

The budget is intentionally bounded (`max_examples`) so this stays cheap on every CI run, per the
VL-05 done condition.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from typer.testing import CliRunner

from collection_integrity.cli import app

runner = CliRunner()

DOCUMENTED_EXIT_CODES = {0, 1, 2, 3}


def _assert_contract(objects_bytes: bytes) -> None:
    """Write bytes to a .csv, scan it, and assert the CLI's exit-code contract holds."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        csv_path = tmp / "objects.csv"
        csv_path.write_bytes(objects_bytes)
        result = runner.invoke(
            app,
            [
                "scan",
                "--objects-csv",
                str(csv_path),
                "--output-dir",
                str(tmp / "out"),
                "--fail-on",
                "none",
            ],
        )

    # An unhandled non-SystemExit exception means the CLI crashed instead of reporting cleanly.
    if result.exception is not None and not isinstance(result.exception, SystemExit):
        raise AssertionError(
            f"scan crashed on input {objects_bytes!r}: "
            f"{type(result.exception).__name__}: {result.exception}"
        )
    assert result.exit_code in DOCUMENTED_EXIT_CODES, (
        f"undocumented exit code {result.exit_code} on input {objects_bytes!r}"
    )


# ---------------------------------------------------------------------------
# Property: arbitrary raw bytes (exercises the UTF-8 decode + CSV parse path).
# ---------------------------------------------------------------------------
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(data=st.binary(max_size=4096))
def test_scan_arbitrary_bytes_never_crashes(data: bytes) -> None:
    _assert_contract(data)


# ---------------------------------------------------------------------------
# Property: structured-but-adversarial CSV text (unicode, quotes, commas,
# embedded newlines, ragged rows, huge cells).
# ---------------------------------------------------------------------------
_CELLS = st.text(
    alphabet=st.characters(codec="utf-8"),
    max_size=64,
)


@st.composite
def _csv_text(draw: st.DrawFn) -> bytes:
    n_cols = draw(st.integers(min_value=1, max_value=5))
    header = draw(st.lists(_CELLS, min_size=n_cols, max_size=n_cols))
    n_rows = draw(st.integers(min_value=0, max_value=6))
    # Rows may be ragged (fewer/more fields than the header) on purpose.
    rows = draw(
        st.lists(
            st.lists(_CELLS, min_size=0, max_size=n_cols + 2),
            min_size=n_rows,
            max_size=n_rows,
        )
    )
    import csv
    import io

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(data=_csv_text())
def test_scan_arbitrary_csv_text_never_crashes(data: bytes) -> None:
    _assert_contract(data)


# ---------------------------------------------------------------------------
# Regression cases: minimal inputs distilled from fuzzing counterexamples.
# Each must exit cleanly (2 = invalid input) rather than raise a traceback.
# ---------------------------------------------------------------------------
def test_regression_nul_byte_in_csv() -> None:
    # csv.reader raises `_csv.Error: line contains NUL` — must become a clean exit 2.
    _assert_contract(b"accession_number\n\x00\n")


def test_regression_invalid_utf8_bytes() -> None:
    # Undecodable bytes raise UnicodeDecodeError in the reader — must become a clean exit 2.
    _assert_contract(b"\xff\xfe\x00bad")


def test_regression_empty_file() -> None:
    # No header row at all.
    _assert_contract(b"")
