"""Verify the "Validated on real data" claims against a committed real-data fixture.

`tests/fixtures/real/cleveland_date_errors.csv` holds real rows from the Cleveland Museum of Art
Open Access dataset (CC0, so redistribution is permitted) — the ten objects whose production
end-date precedes the start-date, plus two clean rows. Scanning it through the Cleveland adapter
must reproduce exactly the ten DATE001 findings the showcase page cites, so that claim is
CI-verified and cannot silently drift. No network access is needed.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from collection_integrity.cli import app

REPO = Path(__file__).parent.parent.parent
FIXTURE = REPO / "tests" / "fixtures" / "real" / "cleveland_date_errors.csv"
PAGE = REPO / "site_src" / "real-data.md"
runner = CliRunner()

# The ten real Cleveland objects with inverted date ranges, by accession number (shown on the page).
EXPECTED_INVERTED_ACCESSIONS = {
    "1917.425",  # Storage Basket, 1985 -> 1905
    "1924.650",  # Peasant Leaning on His Doorway, 1648 -> 1558
    "1926.479",  # Cornelis Claesz Anslo, 1641 -> 1631
    "1929.894",  # The Watering Hole, 1906 -> 1903
    "1932.417",  # Morning Glories, 1921 -> 1911
    "1922.523",  # The Horrors of War, 1810 -> 186
    "1915.403",  # Buckle, 918 -> 907
    "1917.601",  # Four Continents, 1755 -> 1665
    "1932.542",  # Madonna Enthroned, 1885 -> 188
    "1917.601.1",  # Figure of Europe and America, 1755 -> 1665
}


def test_real_cleveland_fixture_reproduces_inverted_date_findings(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "scan",
            "--source",
            "cleveland",
            "--input",
            str(FIXTURE),
            "--output-dir",
            str(tmp_path / "out"),
            "--fail-on",
            "none",
        ],
    )
    assert result.exit_code == 0, result.output
    findings = json.loads((tmp_path / "out" / "findings.json").read_text())

    date001 = [f for f in findings if f["rule"]["id"].startswith("DATE001")]
    # Exactly ten inverted-date findings, one per flagged object; the two clean rows produce none.
    assert len(date001) == 10, [f["entity"]["id"] for f in date001]

    # Each finding must be for one of the expected real objects; and every clean row is silent.
    for f in date001:
        for e in f["evidence"]:
            if e["field"] == "production_start_date":
                start = e["value"]
            if e["field"] == "production_end_date":
                end = e["value"]
        assert end < start, f"finding {f['entity']['id']} is not actually inverted: {start}..{end}"


def test_page_claim_matches_fixture() -> None:
    # The page states "10 Cleveland objects"; keep that number tied to the fixture.
    assert len(EXPECTED_INVERTED_ACCESSIONS) == 10
    page = PAGE.read_text(encoding="utf-8")
    assert "10 Cleveland objects" in page
    assert "inverted-date errors in Cleveland's data and one in the Met's" in page
