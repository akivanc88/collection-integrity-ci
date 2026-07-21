"""VL-04: threat-model adversarial fixtures and tests (BUILD_BRIEF.md Section 18).

Each test here pins one hostile-input item from the threat model: the tool must fail cleanly (a
controlled error or a neutralized output), never crash, never execute source content, never follow a
path outside its sandbox. The coverage table in `docs/THREAT_MODEL.md` maps every Section 18 item to
either one of these tests or a documented rationale for non-applicability.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from collection_integrity.cli import app
from collection_integrity.engine.media_files import (
    is_readable_image,
    read_image_size,
    resolve_local_path,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"
ADVERSARIAL = FIXTURES / "adversarial"
runner = CliRunner()

_FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")


# --- Item 1: spreadsheet formula injection ---------------------------------------------------
def test_formula_injection_neutralized_in_findings_csv(tmp_path: Path) -> None:
    # Source object_ids/titles are formulas; they flow into findings. The emitted findings.csv
    # must neutralize every cell so opening it in a spreadsheet cannot execute a formula.
    out = tmp_path / "scan"
    result = runner.invoke(
        app,
        [
            "scan",
            "--objects-csv",
            str(ADVERSARIAL / "objects_formula_injection.csv"),
            "--output-dir",
            str(out),
            "--fail-on",
            "none",
        ],
    )
    assert result.exit_code == 0, result.output

    with (out / "findings.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert len(rows) > 1, "expected findings from the duplicate accession"
    # No data cell may begin with a formula trigger; the neutralizer prefixes with an apostrophe.
    neutralized_seen = False
    for row in rows[1:]:
        for cell in row:
            assert not cell.startswith(_FORMULA_TRIGGERS), f"un-neutralized cell: {cell!r}"
            if len(cell) > 1 and cell[0] == "'" and cell[1] in _FORMULA_TRIGGERS:
                neutralized_seen = True
    # Guard against a vacuous pass: the formula accession must actually have reached a cell and
    # been defanged (e.g. the entity_id `=cmd|'/c calc'!A1` becomes `'=cmd|'/c calc'!A1`).
    assert neutralized_seen, "expected at least one neutralized formula cell"


# --- Item 2: path traversal in media paths ---------------------------------------------------
@pytest.mark.parametrize(
    "hostile",
    ["../../../etc/passwd", "../secrets.txt", "/etc/passwd", "sub/../../escape"],
)
def test_media_path_traversal_refused(tmp_path: Path, hostile: str) -> None:
    root = tmp_path / "media"
    root.mkdir()
    # A reference that escapes the media root resolves to None rather than being followed.
    assert resolve_local_path(hostile, root) is None


def test_media_path_within_root_is_allowed(tmp_path: Path) -> None:
    root = tmp_path / "media"
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "img.jpg").write_bytes(b"x")
    resolved = resolve_local_path("sub/img.jpg", root)
    assert resolved is not None and resolved.is_relative_to(root.resolve())


# --- Item 3: symlink traversal ---------------------------------------------------------------
def test_media_symlink_escaping_root_refused(tmp_path: Path) -> None:
    root = tmp_path / "media"
    root.mkdir()
    outside = tmp_path / "outside_secret.txt"
    outside.write_text("top secret", encoding="utf-8")
    link = root / "escape"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")
    # The symlink lives inside the root but resolves outside it, so it must be refused.
    assert resolve_local_path("escape", root) is None


# --- Items 4 & 5: malformed / decompression-bomb images --------------------------------------
def test_decompression_bomb_image_handled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Force Pillow's decompression-bomb guard by lowering the pixel ceiling, then read an image
    # that exceeds it. The reader must return None / False, never raise.
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 16)
    bomb = tmp_path / "bomb.png"
    Image.new("RGB", (64, 64)).save(bomb)  # 4096 pixels >> 2 * 16
    assert read_image_size(bomb) is None
    assert is_readable_image(bomb) is False


def test_unreadable_image_handled(tmp_path: Path) -> None:
    junk = tmp_path / "not_an_image.jpg"
    junk.write_bytes(b"this is not an image")
    assert read_image_size(junk) is None
    assert is_readable_image(junk) is False


# --- Item 11: denial of service from pathological records ------------------------------------
def test_pathological_row_volume_completes(tmp_path: Path) -> None:
    # A large row count with a sizeable (but within-limit) cell must still complete with a clean
    # exit code, not hang or crash. Deterministic single-pass rules bound the work.
    big_cell = "A" * 100_000  # under Python's default csv field limit (131072)
    lines = ["object_id,accession_number,object_name"]
    for i in range(4000):
        lines.append(f"OBJ-{i},ACC-{i % 2000},{big_cell if i == 0 else 'name'}")
    src = tmp_path / "pathological.csv"
    src.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["scan", "--objects-csv", str(src), "--output-dir", str(tmp_path / "out")],
    )
    # Duplicate accessions (i % 2000) guarantee findings -> exit 1 under the default threshold.
    assert result.exit_code in {0, 1}, result.output


def test_oversized_cell_rejected_cleanly(tmp_path: Path) -> None:
    # A single cell beyond the csv field-size limit is rejected as invalid input (exit 2), a clean
    # safeguard against a decompression-style single-record DoS — never an unhandled crash.
    src = tmp_path / "huge_cell.csv"
    src.write_text("object_id,object_name\nOBJ-1," + "A" * 300_000 + "\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["scan", "--objects-csv", str(src), "--output-dir", str(tmp_path / "out")],
    )
    assert result.exit_code == 2, result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)
