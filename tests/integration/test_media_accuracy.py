"""Slice G accuracy validation: MEDIA001-004 on AI-generated image files.

Builds a set of valid PNG images and a media table (clean = no findings), then injects missing
files, duplicate content, undersized images, and corrupt files, and confirms each rule recovers
exactly its injected errors at precision = recall = 1.0.
"""

from pathlib import Path

from PIL import Image

from collection_integrity.benchmark.injectors import InjectedError, InjectionManifest
from collection_integrity.benchmark.metrics import score
from collection_integrity.canonical.models import MediaAsset, SourceRef
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.registry import RuleRegistry

MIN_W = MIN_H = 300


def _ref(mid: str) -> SourceRef:
    return SourceRef(
        source_name="bench",
        source_file="media.csv",
        source_record_id=mid,
        source_hash="x",
        ingested_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
    )


def _media(mid: str, path: str) -> MediaAsset:
    return MediaAsset(media_id=mid, path_or_url=path, source_ref=_ref(mid))


def _png(path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, "PNG")


def _scan(tmp_path: Path, media: list[MediaAsset]) -> list:  # type: ignore[type-arg]
    ctx = RuleContext(
        objects=[],
        media=media,
        check_media_files=True,
        media_root=tmp_path,
        min_image_width=MIN_W,
        min_image_height=MIN_H,
    )
    return RuleRegistry.with_defaults().evaluate(ctx)


def _clean_media(tmp_path: Path, count: int) -> list[MediaAsset]:
    media = []
    for i in range(1, count + 1):
        name = f"img_{i:03d}.png"
        # Distinct colors keep content unique; all comfortably above the minimum size.
        _png(tmp_path / name, (400, 400), (i % 200 + 30, (i * 3) % 200 + 30, (i * 7) % 200 + 30))
        media.append(_media(f"M{i:03d}", name))
    return media


def test_clean_media_has_no_findings(tmp_path: Path) -> None:
    media = _clean_media(tmp_path, 20)

    findings = _scan(tmp_path, media)

    assert findings == [], [f.summary for f in findings]


def test_injected_media_errors_detected_with_perfect_precision_recall(tmp_path: Path) -> None:
    media = _clean_media(tmp_path, 20)
    errors: list[InjectedError] = []

    def err(rule_id: str, entity_id: str) -> InjectedError:
        return InjectedError(
            error_id=f"{rule_id}:{entity_id}",
            expected_rule_id=rule_id,
            entity_type="media",
            entity_id=entity_id,
            field="path_or_url",
            before_value="",
            after_value="",
        )

    # MEDIA001: reference files that do not exist.
    for i in (101, 102, 103):
        media.append(_media(f"M{i}", f"missing_{i}.png"))
        errors.append(err("MEDIA001_LOCAL_FILE_MISSING", f"M{i}"))

    # MEDIA002: two media pointing at byte-identical content (anchor = lexicographically first id).
    _png(tmp_path / "dup_a.png", (400, 400), (123, 45, 67))
    _png(tmp_path / "dup_b.png", (400, 400), (123, 45, 67))
    media.append(_media("M201", "dup_a.png"))
    media.append(_media("M202", "dup_b.png"))
    errors.append(err("MEDIA002_DUPLICATE_FILE_HASH", "M201"))

    # MEDIA003: undersized images.
    for i in (301, 302):
        _png(tmp_path / f"small_{i}.png", (100, 100), (i % 200, 10, 10))
        media.append(_media(f"M{i}", f"small_{i}.png"))
        errors.append(err("MEDIA003_IMAGE_BELOW_MINIMUM_DIMENSIONS", f"M{i}"))

    # MEDIA004: corrupt files (distinct bytes so they are not also MEDIA002 duplicates).
    for i in (401, 402):
        (tmp_path / f"corrupt_{i}.png").write_bytes(f"not an image {i}".encode())
        media.append(_media(f"M{i}", f"corrupt_{i}.png"))
        errors.append(err("MEDIA004_UNREADABLE_IMAGE", f"M{i}"))

    manifest = InjectionManifest(seed=0, errors=errors)
    findings = _scan(tmp_path, media)
    metrics = score(findings, manifest)

    for rule_id in (
        "MEDIA001_LOCAL_FILE_MISSING",
        "MEDIA002_DUPLICATE_FILE_HASH",
        "MEDIA003_IMAGE_BELOW_MINIMUM_DIMENSIONS",
        "MEDIA004_UNREADABLE_IMAGE",
    ):
        m = metrics[rule_id]
        assert m.precision == 1.0, (rule_id, m)
        assert m.recall == 1.0, (rule_id, m)
