"""Slice M validation: the benchmark runner scores every benchmarked rule at P=R=1.0, and is
deterministic by seed."""

import json
from pathlib import Path

from typer.testing import CliRunner

from collection_integrity.benchmark.runner import (
    BENCHMARK_RULES,
    BenchmarkResult,
    run_benchmark,
)
from collection_integrity.cli import app

runner = CliRunner()


def test_benchmark_hits_perfect_precision_recall() -> None:
    result = run_benchmark(count=60, seed=42)

    assert set(result.per_rule) == set(BENCHMARK_RULES)
    for rule_id, m in result.per_rule.items():
        assert m["precision"] == 1.0, (rule_id, m)
        assert m["recall"] == 1.0, (rule_id, m)
        assert m["f1"] == 1.0, (rule_id, m)
    assert result.meets_target is True
    # 5 rules x 4 injected errors each = 20 findings.
    assert result.total_findings == 20


def test_meets_target_is_false_when_a_rule_underperforms() -> None:
    good = {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    bad = {"precision": 0.5, "recall": 1.0, "f1": 0.67}
    perfect = BenchmarkResult(
        seed=1, object_count=1, runtime_seconds=0.0, total_findings=1, per_rule={"A": dict(good)}
    )
    imperfect = BenchmarkResult(
        seed=1,
        object_count=1,
        runtime_seconds=0.0,
        total_findings=1,
        per_rule={"A": dict(good), "B": dict(bad)},
    )

    assert perfect.meets_target is True
    assert imperfect.meets_target is False


def test_benchmark_is_deterministic_by_seed() -> None:
    a = run_benchmark(count=50, seed=7)
    b = run_benchmark(count=50, seed=7)

    assert a.per_rule == b.per_rule
    assert a.total_findings == b.total_findings


def test_benchmark_cli_writes_report_and_exits_zero(tmp_path: Path) -> None:
    result = runner.invoke(app, ["benchmark", "--output-dir", str(tmp_path), "--seed", "42"])

    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path / "benchmark_report.json").read_text(encoding="utf-8"))
    assert report["meets_target"] is True
    assert report["per_rule"]["CORE001_DUPLICATE_ACCESSION_NUMBER"]["precision"] == 1.0
    assert report["seed"] == 42
