"""Synthetic datasets in real museum-export schemas, for validating source adapters (Phase 4).

Each generator writes a file whose *field names match the institution's published open-data schema*
(so the adapter is exercised exactly as it would be on a real download) and returns a
`SourceScenario` recording the ground-truth errors it injected. Tests score an adapter's findings
against that ground truth with precision/recall/F1, the same labeled-injection method the Phase 2/3
benchmark uses — just applied to real-schema columns rather than canonical ones.

The generator is schema-driven: a `SchemaSpec` maps canonical fields to an institution's source
column names, and `write_dataset` builds identical rows/injections and serializes them as CSV or
JSON. This keeps every source adapter validated by the same disjoint, leakage-free error set.

The data is fabricated (no real collection records), deterministic, and safe to redistribute.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

# Rule ids scored by these fixtures. CORE001 findings are keyed by the duplicated accession number
# (that is the finding's entity id); the row-level rules are keyed by the object's id.
CORE001 = "CORE001_DUPLICATE_ACCESSION_NUMBER"
CORE002 = "CORE002_REQUIRED_FIELD_MISSING"
DATE001 = "DATE001_INVERTED_DATE_RANGE"
DATE002 = "DATE002_IMPOSSIBLE_AGENT_LIFESPAN_CONFLICT"
SCHEMA001 = "SCHEMA001_INVALID_FIELD_TYPE"


@dataclass
class SourceScenario:
    """Ground truth for a generated dataset: rule id -> the entity ids that should be flagged."""

    expected: dict[str, set[str]] = field(default_factory=dict)

    def add(self, rule_id: str, entity_id: str) -> None:
        self.expected.setdefault(rule_id, set()).add(entity_id)


@dataclass(frozen=True)
class SchemaSpec:
    """An institution's schema as a canonical-field -> source-column-name map.

    Must include the fields the injections use: object_id, accession_number, object_name, title,
    department, culture, production_start_date, production_end_date.
    """

    name: str
    columns: dict[str, str]


MET_SPEC = SchemaSpec(
    "met",
    {
        "object_id": "Object ID",
        "accession_number": "Object Number",
        "object_name": "Object Name",
        "title": "Title",
        "department": "Department",
        "culture": "Culture",
        "production_start_date": "Object Begin Date",
        "production_end_date": "Object End Date",
    },
)

CLEVELAND_SPEC = SchemaSpec(
    "cleveland",
    {
        "object_id": "id",
        "accession_number": "accession_number",
        "object_name": "type",
        "title": "title",
        "department": "department",
        "culture": "culture",
        "production_start_date": "creation_date_earliest",
        "production_end_date": "creation_date_latest",
    },
)


def write_dataset(
    path: Path,
    spec: SchemaSpec,
    *,
    fmt: str = "csv",
    clean_count: int = 40,
    injected_per_rule: int = 3,
) -> SourceScenario:
    """Write a dataset in `spec`'s schema (CSV or JSON) with labeled injected errors.

    Injections are disjoint (each row carries at most one error) and leakage-free: a row with an
    empty accession triggers CORE002 but not CORE001 (empty accessions are never duplicates), and a
    row with an unparseable begin date triggers SCHEMA001 but not DATE001 (no valid start to
    compare). Clean rows have unique accessions, non-empty names, and valid begin<=end years.
    """
    scenario = SourceScenario()
    rows: list[dict[str, str]] = []
    next_id = 0

    def clean_row(accession: str) -> dict[str, str]:
        nonlocal next_id
        oid = f"{spec.name.upper()}-{next_id:04d}"
        next_id += 1
        return {
            "object_id": oid,
            "accession_number": accession,
            "object_name": "Painting",
            "title": f"Untitled {oid}",
            "department": "Paintings",
            "culture": "American",
            "production_start_date": "1700",
            "production_end_date": "1750",
        }

    for i in range(clean_count):
        rows.append(clean_row(f"2000.{i}.1"))

    # CORE001: duplicate accession numbers (a clean row plus a partner sharing its accession).
    for i in range(injected_per_rule):
        acc = f"DUP.{i}.1"
        rows.append(clean_row(acc))
        rows.append(clean_row(acc))  # same accession, different object id -> a true duplicate
        scenario.add(CORE001, acc)

    # CORE002: missing required field (empty accession number).
    for _ in range(injected_per_rule):
        r = clean_row("")
        scenario.add(CORE002, r["object_id"])
        rows.append(r)

    # DATE001: inverted production range (begin year after end year).
    for i in range(injected_per_rule):
        r = clean_row(f"INV.{i}.1")
        r["production_start_date"], r["production_end_date"] = "1900", "1850"
        scenario.add(DATE001, r["object_id"])
        rows.append(r)

    # SCHEMA001: unparseable begin date.
    for i in range(injected_per_rule):
        r = clean_row(f"BAD.{i}.1")
        r["production_start_date"] = "not-a-year"
        scenario.add(SCHEMA001, r["object_id"])
        rows.append(r)

    path.parent.mkdir(parents=True, exist_ok=True)
    _serialize(path, spec, rows, fmt)
    return scenario


def _serialize(path: Path, spec: SchemaSpec, rows: list[dict[str, str]], fmt: str) -> None:
    """Write canonical-keyed rows out under the schema's source column names."""
    ordered = list(spec.columns)  # canonical fields, stable order
    if fmt == "json":
        payload = [{spec.columns[c]: r[c] for c in ordered} for r in rows]
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return
    headers = [spec.columns[c] for c in ordered]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows([[r[c] for c in ordered] for r in rows])


def write_met_dataset(
    path: Path, *, clean_count: int = 40, injected_per_rule: int = 3
) -> SourceScenario:
    """Write a `MetObjects.csv`-schema file with labeled injected errors (thin wrapper)."""
    return write_dataset(
        path, MET_SPEC, fmt="csv", clean_count=clean_count, injected_per_rule=injected_per_rule
    )


NGA_OBJECT_COLUMNS = [
    "objectid",
    "accessionnum",
    "title",
    "classification",
    "departmentabbr",
    "beginyear",
    "endyear",
]
NGA_CONSTITUENT_COLUMNS = [
    "constituentid",
    "preferreddisplayname",
    "nationality",
    "beginyear",
    "endyear",
]
NGA_LINK_COLUMNS = ["objectid", "constituentid", "displayorder"]


def write_nga_dataset(
    directory: Path, *, clean_count: int = 30, injected_per_rule: int = 3
) -> SourceScenario:
    """Write an NGA opendata-schema directory (objects + constituents + link table) with labeled
    errors, exercising the relational join. Beyond the object-level rules (CORE001, DATE001,
    SCHEMA001) it injects DATE002 (production after the linked maker's death), which only fires when
    the many-to-many link is correctly assembled. Clean objects link to makers whose lifespans cover
    the production year; injected DATE001/SCHEMA001 rows use wide-lifespan makers so they stay
    disjoint from DATE002.
    """
    scenario = SourceScenario()
    objects: list[dict[str, str]] = []
    constituents: list[dict[str, str]] = []
    links: list[dict[str, str]] = []
    oid = cid = 0

    def maker(birth: int, death: int) -> str:
        nonlocal cid
        c = f"C-{cid:04d}"
        cid += 1
        constituents.append(
            {
                "constituentid": c,
                "preferreddisplayname": f"Maker {c}",
                "nationality": "American",
                "beginyear": str(birth),
                "endyear": str(death),
            }
        )
        return c

    def obj(accession: str, begin: str, end: str, makers: list[str]) -> str:
        nonlocal oid
        o = f"NGA-OBJ-{oid:04d}"
        oid += 1
        objects.append(
            {
                "objectid": o,
                "accessionnum": accession,
                "title": f"Untitled {o}",
                "classification": "Painting",
                "departmentabbr": "CG",
                "beginyear": begin,
                "endyear": end,
            }
        )
        for order, m in enumerate(makers):
            links.append({"objectid": o, "constituentid": m, "displayorder": str(order)})
        return o

    for i in range(clean_count):
        obj(f"2000.{i}.1", "1850", "1850", [maker(1820, 1890)])
    if clean_count:  # one clean object with two makers, both covering 1850 (many-to-many path)
        obj("2000.multi.1", "1850", "1850", [maker(1800, 1880), maker(1810, 1900)])

    # DATE002: production began after the linked maker died (needs the join to detect).
    for i in range(injected_per_rule):
        o = obj(f"D2.{i}.1", "1900", "1900", [maker(1820, 1850)])
        scenario.add(DATE002, o)

    # CORE001: duplicate accession (both rows well-formed and lifespan-consistent).
    for i in range(injected_per_rule):
        acc = f"DUP.{i}.1"
        obj(acc, "1850", "1850", [maker(1820, 1890)])
        obj(acc, "1860", "1860", [maker(1830, 1900)])
        scenario.add(CORE001, acc)

    # DATE001: inverted production range; wide-lifespan maker keeps it disjoint from DATE002.
    for i in range(injected_per_rule):
        o = obj(f"INV.{i}.1", "1900", "1850", [maker(1800, 1950)])
        scenario.add(DATE001, o)

    # SCHEMA001: unparseable begin date (DATE002 skips it — no valid production start).
    for i in range(injected_per_rule):
        o = obj(f"BAD.{i}.1", "not-a-year", "1900", [maker(1800, 1950)])
        scenario.add(SCHEMA001, o)

    directory.mkdir(parents=True, exist_ok=True)
    _write_csv(directory / "objects.csv", NGA_OBJECT_COLUMNS, objects)
    _write_csv(directory / "constituents.csv", NGA_CONSTITUENT_COLUMNS, constituents)
    _write_csv(directory / "objects_constituents.csv", NGA_LINK_COLUMNS, links)
    return scenario


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        writer.writerows([[r[c] for c in columns] for r in rows])


def score(findings: list, scenario: SourceScenario) -> dict[str, dict[str, float]]:  # type: ignore[type-arg]
    """Precision/recall/F1 per expected rule, comparing finding entity ids to the ground truth.

    Precision below 1.0 means the adapter surfaced something the scenario did not inject (a false
    positive); recall below 1.0 means it missed a labeled error. A perfect adapter scores 1.0/1.0
    on every rule and produces no finding for any rule absent from the scenario.
    """
    out: dict[str, dict[str, float]] = {}
    all_rules = set(scenario.expected) | {f.rule.id for f in findings}
    for rule_id in sorted(all_rules):
        expected = scenario.expected.get(rule_id, set())
        predicted = {f.entity.id for f in findings if f.rule.id == rule_id}
        tp = len(predicted & expected)
        fp = len(predicted - expected)
        fn = len(expected - predicted)
        precision = tp / (tp + fp) if (tp + fp) else 1.0
        recall = tp / (tp + fn) if (tp + fn) else 1.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        out[rule_id] = {"precision": precision, "recall": recall, "f1": f1}
    return out
