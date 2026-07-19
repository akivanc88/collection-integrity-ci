from pathlib import Path

from collection_integrity.ingestion.mapper import load_mapping, load_media, load_objects
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.reference_rules import OrphanMediaObjectRule

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _ctx() -> RuleContext:
    mapping = load_mapping(FIXTURES / "mapping_with_media.yaml")
    objects = load_objects(mapping, base_dir=FIXTURES)
    media = load_media(mapping, base_dir=FIXTURES)
    return RuleContext(objects=objects, media=media)


def test_detects_orphan_media_reference() -> None:
    findings = OrphanMediaObjectRule().evaluate(_ctx(), severity="high")

    # IMG-9 points at object A9, which is not in mapping_objects.csv (A1/A2/A3).
    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule.id == "REF001_ORPHAN_MEDIA_OBJECT"
    assert finding.entity.type == "media"
    assert finding.entity.id == "IMG-9"
    assert finding.evidence[0].value == "A9"


def test_valid_media_references_produce_no_findings() -> None:
    ctx = _ctx()
    # Restrict to only the media that reference existing objects.
    valid_media = [m for m in ctx.media if m.media_id != "IMG-9"]
    findings = OrphanMediaObjectRule().evaluate(
        RuleContext(objects=ctx.objects, media=valid_media), severity="high"
    )

    assert findings == []


def test_media_without_object_id_is_not_an_orphan() -> None:
    ctx = _ctx()
    from collection_integrity.canonical.models import MediaAsset, SourceRef

    no_ref = MediaAsset(
        media_id="IMG-X",
        object_id=None,
        source_ref=SourceRef(
            source_name="t",
            source_file="t.csv",
            source_record_id="IMG-X",
            source_hash="x",
            ingested_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
        ),
    )
    findings = OrphanMediaObjectRule().evaluate(
        RuleContext(objects=ctx.objects, media=[no_ref]), severity="high"
    )

    assert findings == []
