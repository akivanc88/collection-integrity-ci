"""Score scan findings against an injection manifest (BUILD_BRIEF.md Section 16 metrics).

Computes precision, recall, and F1 for the deterministic rules by matching findings to the ground
truth in an `InjectionManifest`. Matching is exact on the identity a correct rule would report:

- CORE001: the flagged accession value must be one the manifest marked as duplicated.
- CORE002: the flagged (object_id, field) pair must be one the manifest blanked.

Any finding that does not match a labeled error is a false positive; any labeled error with no
matching finding is a false negative.
"""

from __future__ import annotations

from dataclasses import dataclass

from collection_integrity.benchmark.injectors import InjectionManifest
from collection_integrity.engine.findings import Finding


@dataclass(frozen=True)
class RuleMetrics:
    rule_id: str
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return 1.0 if denom == 0 else self.true_positives / denom

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return 1.0 if denom == 0 else self.true_positives / denom

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 0.0 if (p + r) == 0 else 2 * p * r / (p + r)


def score(findings: list[Finding], manifest: InjectionManifest) -> dict[str, RuleMetrics]:
    """Return per-rule metrics for the rules the manifest has ground truth for."""
    core001_found = {
        f.entity.id for f in findings if f.rule.id == "CORE001_DUPLICATE_ACCESSION_NUMBER"
    }
    core002_found = {
        (f.entity.id, f.entity.field or "")
        for f in findings
        if f.rule.id == "CORE002_REQUIRED_FIELD_MISSING"
    }

    ref001_found = {f.entity.id for f in findings if f.rule.id == "REF001_ORPHAN_MEDIA_OBJECT"}

    return {
        "CORE001_DUPLICATE_ACCESSION_NUMBER": _metrics(
            "CORE001_DUPLICATE_ACCESSION_NUMBER",
            core001_found,
            manifest.expected_core001_accessions(),
        ),
        "CORE002_REQUIRED_FIELD_MISSING": _metrics(
            "CORE002_REQUIRED_FIELD_MISSING", core002_found, manifest.expected_core002_keys()
        ),
        "REF001_ORPHAN_MEDIA_OBJECT": _metrics(
            "REF001_ORPHAN_MEDIA_OBJECT", ref001_found, manifest.expected_ref001_media()
        ),
    }


def _metrics(rule_id: str, found: set, expected: set) -> RuleMetrics:  # type: ignore[type-arg]
    tp = len(found & expected)
    fp = len(found - expected)
    fn = len(expected - found)
    return RuleMetrics(rule_id=rule_id, true_positives=tp, false_positives=fp, false_negatives=fn)
