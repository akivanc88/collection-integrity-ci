"""Regression: parse_date must accept short CE years, not just 4-digit ones.

Surfaced by scanning real Met/Cleveland open data: encyclopedic collections record ancient and
early-CE works with 1-3 digit years (e.g. year 50, 185, 999). The parser previously accepted only
4-digit years, so thousands of legitimate ancient dates were wrongly flagged SCHEMA001. Year 0, BCE
(negative), and out-of-range values remain unset by design (a documented limitation).
"""

from __future__ import annotations

from datetime import date

import pytest

from collection_integrity.ingestion.mapper import parse_date


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1900", date(1900, 1, 1)),
        ("2023", date(2023, 1, 1)),
        ("999", date(999, 1, 1)),
        ("185", date(185, 1, 1)),
        ("50", date(50, 1, 1)),
        ("1", date(1, 1, 1)),
        ("1899-05-04", date(1899, 5, 4)),
    ],
)
def test_accepts_valid_ce_years(raw: str, expected: date) -> None:
    assert parse_date(raw) == expected


@pytest.mark.parametrize("raw", ["0", "-5", "-500", "10000", "", "  ", "n.d.", "circa 1900"])
def test_rejects_year_zero_bce_and_nonyears(raw: str) -> None:
    # These remain unset rather than fabricated (year 0 and BCE are the documented date limitation).
    assert parse_date(raw) is None
