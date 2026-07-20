"""Accuracy validation for the NGA source adapter (Phase 4, Slice Q).

The NGA export is relational (objects + a many-to-many constituents link table + constituents). The
adapter joins the link table to stamp each object's maker_ids, which lets DATE002 (production after
the linked maker's death) run. This test injects DATE002 conflicts alongside the object-level errors
and asserts the engine recovers every labeled error at precision = recall = 1.
"""

from __future__ import annotations

from pathlib import Path

from collection_integrity.benchmark.source_fixtures import (
    CORE001,
    DATE001,
    DATE002,
    SCHEMA001,
    score,
    write_nga_dataset,
)
from collection_integrity.ingestion import nga_adapter
from collection_integrity.ingestion.sources import load_source
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.registry import RuleRegistry

DEFAULT_REQUIRED = ["accession_number", "object_name"]


def _scan(directory: Path) -> list:  # type: ignore[type-arg]
    loaded = load_source("nga", directory)
    ctx = RuleContext(
        objects=loaded.objects,
        agents=loaded.agents,
        required_fields=DEFAULT_REQUIRED,
        object_field_sources=loaded.object_field_sources,
    )
    return RuleRegistry.with_defaults().evaluate(ctx)


def test_nga_adapter_recovers_all_injected_errors(tmp_path: Path) -> None:
    scenario = write_nga_dataset(tmp_path)
    metrics = score(_scan(tmp_path), scenario)

    for rule_id in (CORE001, DATE001, SCHEMA001, DATE002):
        assert metrics[rule_id]["precision"] == 1.0, (rule_id, metrics[rule_id])
        assert metrics[rule_id]["recall"] == 1.0, (rule_id, metrics[rule_id])
    assert set(metrics) == {CORE001, DATE001, SCHEMA001, DATE002}


def test_nga_join_populates_maker_ids(tmp_path: Path) -> None:
    write_nga_dataset(tmp_path, clean_count=5, injected_per_rule=0)
    loaded = load_source("nga", tmp_path)
    # Every object got at least one maker from the link table; the multi-maker object got two.
    assert all(o.maker_ids for o in loaded.objects)
    assert any(len(o.maker_ids) == 2 for o in loaded.objects)
    # Makers are AgentOrMaker records with birth/death dates parsed from beginyear/endyear.
    assert loaded.agents
    assert all(a.birth_date is not None and a.death_date is not None for a in loaded.agents)


def test_nga_maker_order_is_deterministic_by_displayorder(tmp_path: Path) -> None:
    # Reverse the physical order of the link rows for one object; join order must be unchanged.
    write_nga_dataset(tmp_path, clean_count=1, injected_per_rule=0)
    link = tmp_path / "objects_constituents.csv"
    lines = link.read_text().splitlines()
    header, body = lines[0], lines[1:]
    link.write_text("\n".join([header, *reversed(body)]) + "\n")

    loaded = load_source("nga", tmp_path)
    multi = [o for o in loaded.objects if len(o.maker_ids) == 2][0]
    assert multi.maker_ids == sorted(multi.maker_ids)  # displayorder 0,1 -> C-000x before C-000y


def test_nga_missing_link_table_errors(tmp_path: Path) -> None:
    write_nga_dataset(tmp_path, clean_count=3, injected_per_rule=0)
    (tmp_path / "objects_constituents.csv").unlink()
    try:
        nga_adapter.load(tmp_path)
    except Exception as exc:  # noqa: BLE001
        assert "link table not found" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected a missing-link-table error")
