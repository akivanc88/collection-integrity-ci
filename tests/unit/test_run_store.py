from pathlib import Path

from collection_integrity.engine.findings import (
    EntityRef,
    EvidenceItem,
    Finding,
    RuleRef,
    compute_fingerprint,
)
from collection_integrity.engine.run_store import RunStore, RunSummary, summarize


def _finding(rule_id: str, entity_id: str, severity: str) -> Finding:
    return Finding(
        finding_id=f"fid-{entity_id}",
        fingerprint=compute_fingerprint(rule_id, "object", entity_id, "f", [entity_id]),
        rule=RuleRef(id=rule_id, name=rule_id, version="1.0.0"),
        severity=severity,  # type: ignore[arg-type]
        verification_type="deterministic",
        entity=EntityRef(type="object", id=entity_id, field="f"),
        summary="s",
        explanation="e",
        evidence=[EvidenceItem(source_file="x.csv", source_row=1, field="f", value="v")],
        recommendation="r",
        confidence=1.0,
        created_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
    )


def _sample() -> list[Finding]:
    return [
        _finding("CORE001_DUPLICATE_ACCESSION_NUMBER", "A1", "critical"),
        _finding("CORE002_REQUIRED_FIELD_MISSING", "A2", "high"),
        _finding("CORE002_REQUIRED_FIELD_MISSING", "A3", "high"),
    ]


def test_summarize_counts_by_severity() -> None:
    summary = summarize(_sample())

    assert summary.total_findings == 3
    assert summary.severity_counts == {"critical": 1, "high": 2}
    assert len(summary.fingerprints) == 3


def test_save_and_list_roundtrip(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    store.save(summarize(_sample(), run_id="run-a"))
    store.save(
        summarize(
            [_finding("CORE001_DUPLICATE_ACCESSION_NUMBER", "A9", "critical")], run_id="run-b"
        )
    )

    runs = store.list_runs()
    assert {r.run_id for r in runs} == {"run-a", "run-b"}
    assert store.latest() is not None


def test_persisted_fingerprints_are_stable_for_identical_findings(tmp_path: Path) -> None:
    # Two runs over the same findings must persist identical fingerprint sets (baseline stability).
    a = summarize(_sample(), run_id="a")
    b = summarize(_sample(), run_id="b")

    assert a.fingerprints == b.fingerprints


def test_empty_store_lists_nothing(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    assert store.list_runs() == []
    assert store.latest() is None


def test_saved_record_reloads_equal(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    original = summarize(_sample(), run_id="run-x")
    store.save(original)

    reloaded = store.list_runs()[0]
    assert reloaded == original


def test_fingerprints_are_sorted_regardless_of_finding_order() -> None:
    findings = _sample()
    # Feed findings in reverse-fingerprint order; the summary must still be ascending-sorted.
    reversed_findings = sorted(findings, key=lambda f: f.fingerprint, reverse=True)

    summary = summarize(reversed_findings)

    assert summary.fingerprints == sorted(f.fingerprint for f in findings)
    assert len(set(summary.fingerprints)) >= 2  # the assertion above is non-trivial


def _summary(run_id: str, created_at: str) -> RunSummary:
    return RunSummary(
        run_id=run_id,
        created_at=created_at,
        total_findings=0,
        severity_counts={},
        fingerprints=[],
    )


def test_list_runs_is_oldest_first_and_latest_is_most_recent(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    store.save(_summary("late", "2026-02-01T00:00:00+00:00"))
    store.save(_summary("early", "2026-01-01T00:00:00+00:00"))

    ordered = [r.run_id for r in store.list_runs()]
    assert ordered == ["early", "late"]
    assert store.latest() is not None
    assert store.latest().run_id == "late"
