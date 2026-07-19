import json
from pathlib import Path

import pytest

from collection_integrity.engine.baselines import (
    BaselineError,
    classify,
    load_baseline_fingerprints,
)
from collection_integrity.engine.findings import (
    EntityRef,
    EvidenceItem,
    Finding,
    RuleRef,
    compute_fingerprint,
)


def _finding(entity_id: str) -> Finding:
    return Finding(
        finding_id=f"fid-{entity_id}",
        fingerprint=compute_fingerprint("CORE001", "object", entity_id, "f", [entity_id]),
        rule=RuleRef(id="CORE001", name="c", version="1.0.0"),
        severity="critical",
        verification_type="deterministic",
        entity=EntityRef(type="object", id=entity_id, field="f"),
        summary="s",
        explanation="e",
        evidence=[EvidenceItem(source_file="x.csv", source_row=1, field="f", value="v")],
        recommendation="r",
        confidence=1.0,
        created_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
    )


def test_classify_new_unchanged_resolved() -> None:
    a, b, c = _finding("A"), _finding("B"), _finding("C")
    # Baseline had A and C; current has A and B. -> B new, A unchanged, C resolved.
    baseline = {a.fingerprint, c.fingerprint}

    comparison = classify([a, b], baseline)

    assert [f.entity.id for f in comparison.new] == ["B"]
    assert [f.entity.id for f in comparison.unchanged] == ["A"]
    assert comparison.resolved_fingerprints == {c.fingerprint}
    assert comparison.counts == {"new": 1, "unchanged": 1, "resolved": 1}


def test_load_baseline_fingerprints(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps([{"fingerprint": "abc"}, {"fingerprint": "def"}]), encoding="utf-8")

    assert load_baseline_fingerprints(path) == {"abc", "def"}


def test_load_baseline_rejects_non_array(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"not": "an array"}', encoding="utf-8")

    with pytest.raises(BaselineError):
        load_baseline_fingerprints(path)


def test_empty_baseline_makes_everything_new() -> None:
    a, b = _finding("A"), _finding("B")
    comparison = classify([a, b], set())

    assert len(comparison.new) == 2
    assert comparison.unchanged == []
    assert comparison.resolved_fingerprints == set()
