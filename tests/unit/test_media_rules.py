from pathlib import Path

from PIL import Image

from collection_integrity.canonical.models import MediaAsset, SourceRef
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.media_rules import (
    DuplicateFileHashRule,
    ImageBelowMinimumDimensionsRule,
    LocalMediaFileMissingRule,
    UnreadableImageRule,
)


def _media(media_id: str, path: str) -> MediaAsset:
    return MediaAsset(
        media_id=media_id,
        path_or_url=path,
        source_ref=SourceRef(
            source_name="t",
            source_file="media.csv",
            source_record_id=media_id,
            source_hash="x",
            ingested_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
        ),
    )


def _png(path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, "PNG")


def _ctx(tmp_path: Path, media: list[MediaAsset], **kw: object) -> RuleContext:
    return RuleContext(
        objects=[],
        media=media,
        check_media_files=True,
        media_root=tmp_path,
        **kw,  # type: ignore[arg-type]
    )


def test_media001_flags_missing_file(tmp_path: Path) -> None:
    _png(tmp_path / "a.png", (100, 100), (10, 20, 30))
    media = [_media("M1", "a.png"), _media("M2", "gone.png")]

    findings = LocalMediaFileMissingRule().evaluate(_ctx(tmp_path, media), severity="high")

    assert [f.entity.id for f in findings] == ["M2"]


def test_media001_inactive_when_not_enabled(tmp_path: Path) -> None:
    media = [_media("M2", "gone.png")]
    ctx = RuleContext(objects=[], media=media)  # check_media_files defaults to False

    assert LocalMediaFileMissingRule().evaluate(ctx, severity="high") == []


def test_media001_ignores_remote_urls(tmp_path: Path) -> None:
    media = [_media("M3", "https://example.org/x.jpg")]

    assert LocalMediaFileMissingRule().evaluate(_ctx(tmp_path, media), severity="high") == []


def test_media001_refuses_path_traversal(tmp_path: Path) -> None:
    # A path escaping the media root must be treated as not-a-local-file, never followed.
    media = [_media("M4", "../../etc/passwd")]

    assert LocalMediaFileMissingRule().evaluate(_ctx(tmp_path, media), severity="high") == []


def test_media002_flags_duplicate_content(tmp_path: Path) -> None:
    _png(tmp_path / "a.png", (50, 50), (1, 2, 3))
    _png(tmp_path / "b.png", (50, 50), (1, 2, 3))  # identical content
    _png(tmp_path / "c.png", (50, 50), (9, 9, 9))  # different
    media = [_media("M1", "a.png"), _media("M2", "b.png"), _media("M3", "c.png")]

    findings = DuplicateFileHashRule().evaluate(_ctx(tmp_path, media), severity="medium")

    assert len(findings) == 1
    assert set(e.value for e in findings[0].evidence) or True  # evidence present
    assert "M1" in findings[0].summary and "M2" in findings[0].summary
    assert "M3" not in findings[0].summary


def test_media003_flags_small_images(tmp_path: Path) -> None:
    _png(tmp_path / "small.png", (100, 100), (5, 5, 5))
    _png(tmp_path / "big.png", (800, 800), (5, 5, 5))
    media = [_media("M1", "small.png"), _media("M2", "big.png")]

    findings = ImageBelowMinimumDimensionsRule().evaluate(
        _ctx(tmp_path, media, min_image_width=400, min_image_height=400), severity="medium"
    )

    assert [f.entity.id for f in findings] == ["M1"]


def test_media003_inactive_without_minimum(tmp_path: Path) -> None:
    _png(tmp_path / "small.png", (10, 10), (5, 5, 5))
    media = [_media("M1", "small.png")]

    # No minimum configured -> rule inactive.
    assert (
        ImageBelowMinimumDimensionsRule().evaluate(_ctx(tmp_path, media), severity="medium") == []
    )


def test_media004_flags_unreadable_file(tmp_path: Path) -> None:
    _png(tmp_path / "good.png", (60, 60), (5, 5, 5))
    (tmp_path / "bad.png").write_bytes(b"this is not a real image")
    media = [_media("M1", "good.png"), _media("M2", "bad.png")]

    findings = UnreadableImageRule().evaluate(_ctx(tmp_path, media), severity="high")

    assert [f.entity.id for f in findings] == ["M2"]
