"""Deterministic synthetic museum-object generator.

Produces realistic-looking but entirely fabricated object records for benchmarking. The data is
generated, not drawn from any real collection, so it can be redistributed freely and does not
represent any institution's records (see docs/DATA_CARD.md, to be written in Phase 3).

Given the same seed and count, `generate_clean_objects` always returns identical rows, so
benchmark runs are reproducible. The "clean" output is internally consistent: unique object ids,
unique accession numbers, and every policy-required field populated — so a correct rule engine
finds zero issues in it.
"""

from __future__ import annotations

import random

OBJECT_NAMES = [
    "Painting",
    "Sculpture",
    "Vase",
    "Textile",
    "Photograph",
    "Manuscript",
    "Coin",
    "Necklace",
    "Bowl",
    "Print",
    "Drawing",
    "Mask",
]

TITLE_HEADS = [
    "Portrait of",
    "Study for",
    "View of",
    "Still Life with",
    "Composition in",
    "Figure of",
    "Landscape near",
    "Head of",
]

TITLE_TAILS = [
    "a Young Woman",
    "the Harbor",
    "Blue and Gold",
    "a Reclining Figure",
    "Autumn Fields",
    "an Unknown Man",
    "Two Dancers",
    "the Old Bridge",
    "Fruit and Flowers",
    "a Seated Musician",
]

DEPARTMENTS = [
    "European Paintings",
    "Asian Art",
    "Decorative Arts",
    "Photography",
    "Ancient Art",
    "Textiles",
]


# Column order for the objects table this generator emits.
OBJECT_COLUMNS = ("object_id", "accession_number", "title", "object_name", "department")


def generate_clean_objects(count: int, seed: int) -> list[dict[str, str]]:
    """Generate `count` internally consistent object rows, deterministically from `seed`."""
    if count <= 0:
        raise ValueError("count must be positive")

    rng = random.Random(seed)
    rows: list[dict[str, str]] = []
    for i in range(1, count + 1):
        # Accession numbers follow a YYYY.lot.item convention and are made unique by construction.
        year = 1960 + (i % 55)
        accession = f"{year}.{(i // 10) + 1}.{(i % 10) + 1}-{i}"
        title = f"{rng.choice(TITLE_HEADS)} {rng.choice(TITLE_TAILS)}"
        rows.append(
            {
                "object_id": f"OBJ-{i:04d}",
                "accession_number": accession,
                "title": title,
                "object_name": rng.choice(OBJECT_NAMES),
                "department": rng.choice(DEPARTMENTS),
            }
        )
    return rows
