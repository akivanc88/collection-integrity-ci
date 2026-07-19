from collection_integrity.canonical.models import AgentOrMaker, CollectionObject, SourceRef
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.date_rules import AgentLifespanConflictRule


def _ref(rid: str) -> SourceRef:
    return SourceRef(
        source_name="t",
        source_file="f.csv",
        source_record_id=rid,
        source_hash="x",
        ingested_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
    )


def _obj(oid: str, start: str, end: str, makers: list[str]) -> CollectionObject:
    return CollectionObject(
        object_id=oid,
        production_start_date=start,  # type: ignore[arg-type]
        production_end_date=end,  # type: ignore[arg-type]
        maker_ids=makers,
        source_ref=_ref(oid),
    )


def _agent(aid: str, birth: str, death: str) -> AgentOrMaker:
    return AgentOrMaker(
        agent_id=aid,
        birth_date=birth,  # type: ignore[arg-type]
        death_date=death,  # type: ignore[arg-type]
        source_ref=_ref(aid),
    )


def test_date002_flags_production_before_birth() -> None:
    ctx = RuleContext(
        objects=[_obj("O1", "1600-01-01", "1610-01-01", ["A1"])],
        agents=[_agent("A1", "1700-01-01", "1770-01-01")],
    )
    findings = AgentLifespanConflictRule().evaluate(ctx, severity="medium")

    assert [f.entity.id for f in findings] == ["O1"]
    assert "before the maker was born" in findings[0].summary


def test_date002_flags_production_after_death() -> None:
    ctx = RuleContext(
        objects=[_obj("O2", "1800-01-01", "1810-01-01", ["A1"])],
        agents=[_agent("A1", "1700-01-01", "1770-01-01")],
    )
    findings = AgentLifespanConflictRule().evaluate(ctx, severity="medium")

    assert [f.entity.id for f in findings] == ["O2"]
    assert "after the maker died" in findings[0].summary


def test_date002_no_conflict_within_lifespan() -> None:
    ctx = RuleContext(
        objects=[_obj("O3", "1730-01-01", "1740-01-01", ["A1"])],
        agents=[_agent("A1", "1700-01-01", "1770-01-01")],
    )
    assert AgentLifespanConflictRule().evaluate(ctx, severity="medium") == []


def test_date002_inactive_without_precise_dates() -> None:
    # Agent missing death_date -> conservative rule stays silent.
    agent = AgentOrMaker(agent_id="A1", birth_date="1700-01-01", source_ref=_ref("A1"))  # type: ignore[arg-type]
    ctx = RuleContext(
        objects=[_obj("O4", "1600-01-01", "1610-01-01", ["A1"])],
        agents=[agent],
    )
    assert AgentLifespanConflictRule().evaluate(ctx, severity="medium") == []


def test_date002_default_severity_is_medium() -> None:
    from collection_integrity.rules.registry import RuleRegistry

    registry = RuleRegistry.with_defaults()
    assert registry.effective_severity("DATE002_IMPOSSIBLE_AGENT_LIFESPAN_CONFLICT") == "medium"
