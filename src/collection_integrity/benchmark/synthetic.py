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

# Column order for the media table this generator emits.
MEDIA_COLUMNS = ("media_id", "object_id", "path_or_url", "publication_status")


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


def generate_clean_media(objects: list[dict[str, str]], seed: int) -> list[dict[str, str]]:
    """Generate 1-2 media rows per object, each pointing at a valid object_id.

    Deterministic from `seed`. Every media row's object_id references a real object, so a correct
    REF001 finds no orphans in this output.
    """
    rng = random.Random(seed)
    rows: list[dict[str, str]] = []
    media_counter = 1
    for obj in objects:
        for _ in range(rng.randint(1, 2)):
            mid = f"IMG-{media_counter:04d}"
            rows.append(
                {
                    "media_id": mid,
                    "object_id": obj["object_id"],
                    "path_or_url": f"media/{mid}.jpg",
                    "publication_status": rng.choice(["public", "internal", "private"]),
                }
            )
            media_counter += 1
    return rows
