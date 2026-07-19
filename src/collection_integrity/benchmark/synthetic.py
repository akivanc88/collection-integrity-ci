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

# Column order for the rights table this generator emits.
RIGHTS_COLUMNS = ("rights_id", "rights_status", "publication_allowed", "review_required")

# Object columns including the rights link + publication status (used by the rights benchmark).
OBJECT_WITH_RIGHTS_COLUMNS = OBJECT_COLUMNS + ("rights_id", "publication_status")

# Location table columns (a union of hierarchy-node and object-assignment fields).
LOCATION_COLUMNS = ("location_id", "name", "parent_location_id", "object_id", "is_current")

# Object columns including production dates + publication status (for the object-field benchmark).
OBJECT_WITH_DATES_COLUMNS = OBJECT_COLUMNS + (
    "publication_status",
    "production_start_date",
    "production_end_date",
)

PUBLICATION_VOCABULARY = ["public", "internal", "private"]


def add_dates_and_status(objects: list[dict[str, str]], seed: int) -> list[dict[str, str]]:
    """Augment object rows with a valid production date range and an in-vocabulary status.

    Clean invariant: start <= end (parseable ISO dates) and publication_status is in
    PUBLICATION_VOCABULARY, so DATE001/VOCAB001/SCHEMA001 find nothing. An existing non-empty
    publication_status is preserved (so this composes after a rights-linking step that already set
    a status consistent with the rights record).
    """
    rng = random.Random(seed)
    out: list[dict[str, str]] = []
    for obj in objects:
        start_year = 1600 + rng.randint(0, 300)
        span = rng.randint(0, 40)
        status = obj.get("publication_status") or rng.choice(PUBLICATION_VOCABULARY)
        out.append(
            {
                **obj,
                "publication_status": status,
                "production_start_date": f"{start_year}-01-01",
                "production_end_date": f"{start_year + span}-01-01",
            }
        )
    return out


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


def generate_clean_rights(count: int, seed: int) -> list[dict[str, str]]:
    """Generate rights records: a mix of publication-permitting and non-permitting rows.

    Deterministic from `seed`. Roughly half permit publication (public_domain/licensed,
    publication_allowed=true, no review) and half do not (restricted, publication_allowed=false).
    """
    rng = random.Random(seed)
    rows: list[dict[str, str]] = []
    for i in range(1, count + 1):
        permissive = rng.random() < 0.5
        if permissive:
            rows.append(
                {
                    "rights_id": f"R-{i:03d}",
                    "rights_status": rng.choice(["public_domain", "licensed", "institution_owned"]),
                    "publication_allowed": "true",
                    "review_required": "false",
                }
            )
        else:
            rows.append(
                {
                    "rights_id": f"R-{i:03d}",
                    "rights_status": rng.choice(["restricted", "unknown", "review_required"]),
                    "publication_allowed": "false",
                    "review_required": rng.choice(["true", "false"]),
                }
            )
    return rows


def rights_permits_publication(rights_row: dict[str, str]) -> bool:
    """Mirror of the RIGHTS001 policy, used by the generator/injector to keep clean data clean."""
    if rights_row.get("publication_allowed", "").strip().lower() != "true":
        return False
    if rights_row.get("review_required", "").strip().lower() == "true":
        return False
    return rights_row.get("rights_status", "").strip().lower() not in {
        "restricted",
        "unknown",
        "review_required",
    }


def link_objects_to_rights(
    objects: list[dict[str, str]], rights: list[dict[str, str]], seed: int
) -> list[dict[str, str]]:
    """Return object rows augmented with a valid rights_id and a consistent publication_status.

    Clean invariant: an object is only marked ``public`` when its rights record permits
    publication, so a correct RIGHTS001 finds no conflicts and REF002 finds no orphans here.
    """
    rng = random.Random(seed)
    permits = {r["rights_id"]: rights_permits_publication(r) for r in rights}
    rights_ids = [r["rights_id"] for r in rights]

    linked: list[dict[str, str]] = []
    for obj in objects:
        rid = rng.choice(rights_ids)
        if permits[rid]:
            status = rng.choice(["public", "internal", "private"])
        else:
            status = rng.choice(["internal", "private"])
        linked.append({**obj, "rights_id": rid, "publication_status": status})
    return linked


def generate_clean_locations(
    objects: list[dict[str, str]], num_nodes: int, seed: int
) -> list[dict[str, str]]:
    """Generate a valid location hierarchy plus one current assignment per object.

    Clean invariant: the hierarchy is a tree (every parent exists, no cycles) and each object has
    exactly one current location assignment — so a correct LOC001/LOC002 finds nothing.
    """
    rng = random.Random(seed)
    rows: list[dict[str, str]] = []

    # A tree: node i's parent is some earlier node, so no cycles and every parent exists.
    node_ids = [f"LOC-{i:03d}" for i in range(1, num_nodes + 1)]
    for i, loc_id in enumerate(node_ids):
        parent = "" if i == 0 else rng.choice(node_ids[:i])
        rows.append(
            {
                "location_id": loc_id,
                "name": f"Location {i + 1}",
                "parent_location_id": parent,
                "object_id": "",
                "is_current": "",
            }
        )

    # One current assignment per object, each at a leaf-ish node.
    for n, obj in enumerate(objects, start=1):
        rows.append(
            {
                "location_id": f"ASG-{n:04d}",
                "name": "",
                "parent_location_id": "",
                "object_id": obj["object_id"],
                "is_current": "true",
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
