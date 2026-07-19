"""Rule registry: enable/disable rules and override severity per run (BUILD_BRIEF.md Section 11).

The registry is the single place the engine dispatches through. Rules register here by class; a
run receives a `RuleRegistry` snapshot describing which rules are enabled and at what severity, so
the CLI/ruleset layer can turn rules off or re-grade them without touching rule code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from collection_integrity.engine.findings import Finding, Severity
from collection_integrity.rules.base import Rule, RuleContext
from collection_integrity.rules.core_rules import (
    DuplicateAccessionNumberRule,
    RequiredFieldMissingRule,
)

# All rules known to the engine, in a stable order. New rules are appended here.
ALL_RULE_CLASSES: tuple[type[Rule], ...] = (
    DuplicateAccessionNumberRule,
    RequiredFieldMissingRule,
)


@dataclass(frozen=True)
class RuleSetting:
    enabled: bool = True
    severity_override: Severity | None = None


@dataclass
class RuleRegistry:
    """A configured set of rules for one run."""

    rules: dict[str, Rule] = field(default_factory=dict)
    settings: dict[str, RuleSetting] = field(default_factory=dict)

    @classmethod
    def with_defaults(cls) -> RuleRegistry:
        """Registry with every known rule enabled at its default severity."""
        registry = cls()
        for rule_cls in ALL_RULE_CLASSES:
            registry.register(rule_cls())
        return registry

    def register(self, rule: Rule) -> None:
        rule_id = rule.rule.id
        if rule_id in self.rules:
            raise ValueError(f"Duplicate rule id registered: {rule_id}")
        self.rules[rule_id] = rule
        self.settings.setdefault(rule_id, RuleSetting())

    def set_enabled(self, rule_id: str, enabled: bool) -> None:
        self._require(rule_id)
        current = self.settings[rule_id]
        self.settings[rule_id] = RuleSetting(enabled, current.severity_override)

    def override_severity(self, rule_id: str, severity: Severity) -> None:
        self._require(rule_id)
        current = self.settings[rule_id]
        self.settings[rule_id] = RuleSetting(current.enabled, severity)

    def effective_severity(self, rule_id: str) -> Severity:
        self._require(rule_id)
        return self.settings[rule_id].severity_override or self.rules[rule_id].default_severity

    def enabled_rules(self) -> list[Rule]:
        return [self.rules[rid] for rid in self.rules if self.settings[rid].enabled]

    def evaluate(self, ctx: RuleContext) -> list[Finding]:
        """Run every enabled rule and return all findings, in stable rule order."""
        findings: list[Finding] = []
        for rule in self.enabled_rules():
            findings.extend(rule.evaluate(ctx, self.effective_severity(rule.rule.id)))
        return findings

    def _require(self, rule_id: str) -> None:
        if rule_id not in self.rules:
            raise KeyError(f"Unknown rule id: {rule_id}")
