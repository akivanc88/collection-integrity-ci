"""Media-file rules (BUILD_BRIEF.md Section 11, items 12-15).

These read local media files and are inactive unless the run enables media-file checks and sets a
media root (RuleContext.check_media_files / media_root). Remote URLs and paths that escape the
media root are skipped, not followed.

- MEDIA001: a configured local media path does not exist.
- MEDIA002: two media resolve to identical file content (duplicate-file warning, not a delete
  instruction).
- MEDIA003: an image's dimensions are below the configured publication minimum.
- MEDIA004: a file exists but cannot be decoded as an image.
"""

from __future__ import annotations

from collections import defaultdict

from collection_integrity.engine.findings import (
    EntityRef,
    EvidenceItem,
    Finding,
    RuleRef,
    Severity,
)
from collection_integrity.engine.media_files import (
    is_readable_image,
    read_image_size,
    resolve_local_path,
)
from collection_integrity.provenance import hash_file
from collection_integrity.rules.base import Rule, RuleContext


def _active(ctx: RuleContext) -> bool:
    return ctx.check_media_files and ctx.media_root is not None


class LocalMediaFileMissingRule(Rule):
    """MEDIA001: a local media path does not exist."""

    rule = RuleRef(
        id="MEDIA001_LOCAL_FILE_MISSING", name="Local media file missing", version="1.0.0"
    )
    default_severity: Severity = "high"

    def evaluate(self, ctx: RuleContext, severity: Severity) -> list[Finding]:
        if not _active(ctx):
            return []
        assert ctx.media_root is not None
        findings: list[Finding] = []
        for media in sorted(ctx.media, key=lambda m: m.media_id):
            if not media.path_or_url:
                continue
            path = resolve_local_path(media.path_or_url, ctx.media_root)
            if path is None or path.exists():
                continue
            findings.append(
                self.make_finding(
                    severity=severity,
                    entity=EntityRef(type="media", id=media.media_id, field="path_or_url"),
                    entity_id_for_fingerprint=media.media_id,
                    evidence_keys=[media.path_or_url],
                    summary=f"Media {media.media_id} references a file that is missing.",
                    explanation=(
                        f"Media {media.media_id} has path_or_url={media.path_or_url!r}, but no "
                        f"file exists at that location under the media root."
                    ),
                    recommendation="Restore the file or correct the media path.",
                    evidence=[_ev(media, "path_or_url", media.path_or_url)],
                )
            )
        return findings


class DuplicateFileHashRule(Rule):
    """MEDIA002: two media resolve to identical content."""

    rule = RuleRef(id="MEDIA002_DUPLICATE_FILE_HASH", name="Duplicate media file", version="1.0.0")
    default_severity: Severity = "medium"

    def evaluate(self, ctx: RuleContext, severity: Severity) -> list[Finding]:
        if not _active(ctx):
            return []
        assert ctx.media_root is not None
        by_hash: dict[str, list[str]] = defaultdict(list)
        media_by_id = {m.media_id: m for m in ctx.media}
        for media in ctx.media:
            if not media.path_or_url:
                continue
            path = resolve_local_path(media.path_or_url, ctx.media_root)
            if path is None or not path.is_file():
                continue
            by_hash[hash_file(path)].append(media.media_id)

        findings: list[Finding] = []
        for digest, ids in by_hash.items():
            if len(ids) < 2:
                continue
            ordered = sorted(ids)
            anchor = media_by_id[ordered[0]]
            findings.append(
                self.make_finding(
                    severity=severity,
                    entity=EntityRef(type="media", id=ordered[0], field="checksum"),
                    entity_id_for_fingerprint=digest,
                    evidence_keys=ordered,
                    summary=f"Media {', '.join(ordered)} share identical file content.",
                    explanation=(
                        f"Media {', '.join(ordered)} resolve to byte-identical files. This is a "
                        f"duplicate-file warning, not proof that any record should be deleted."
                    ),
                    recommendation=(
                        "Confirm whether these are genuinely separate assets or accidental "
                        "duplicates, and consolidate if appropriate."
                    ),
                    evidence=[_ev(anchor, "path_or_url", anchor.path_or_url)],
                )
            )
        return findings


class ImageBelowMinimumDimensionsRule(Rule):
    """MEDIA003: an image is smaller than the configured publication minimum."""

    rule = RuleRef(
        id="MEDIA003_IMAGE_BELOW_MINIMUM_DIMENSIONS",
        name="Image below minimum dimensions",
        version="1.0.0",
    )
    default_severity: Severity = "medium"

    def evaluate(self, ctx: RuleContext, severity: Severity) -> list[Finding]:
        if not _active(ctx) or (ctx.min_image_width <= 0 and ctx.min_image_height <= 0):
            return []
        assert ctx.media_root is not None
        findings: list[Finding] = []
        for media in sorted(ctx.media, key=lambda m: m.media_id):
            if not media.path_or_url:
                continue
            path = resolve_local_path(media.path_or_url, ctx.media_root)
            if path is None or not path.is_file():
                continue
            size = read_image_size(path)
            if size is None:
                continue  # unreadable images are MEDIA004's concern
            width, height = size
            if width >= ctx.min_image_width and height >= ctx.min_image_height:
                continue
            findings.append(
                self.make_finding(
                    severity=severity,
                    entity=EntityRef(type="media", id=media.media_id, field="width"),
                    entity_id_for_fingerprint=media.media_id,
                    evidence_keys=[f"{width}x{height}"],
                    summary=(
                        f"Media {media.media_id} is {width}x{height}, below the required "
                        f"{ctx.min_image_width}x{ctx.min_image_height}."
                    ),
                    explanation=(
                        f"Media {media.media_id} has dimensions {width}x{height}, which is smaller "
                        f"than the configured minimum {ctx.min_image_width}x{ctx.min_image_height}."
                    ),
                    recommendation="Supply a higher-resolution image or relax the minimum.",
                    evidence=[_ev(media, "dimensions", f"{width}x{height}")],
                )
            )
        return findings


class UnreadableImageRule(Rule):
    """MEDIA004: a file exists but cannot be decoded as an image."""

    rule = RuleRef(id="MEDIA004_UNREADABLE_IMAGE", name="Unreadable image", version="1.0.0")
    default_severity: Severity = "high"

    def evaluate(self, ctx: RuleContext, severity: Severity) -> list[Finding]:
        if not _active(ctx):
            return []
        assert ctx.media_root is not None
        findings: list[Finding] = []
        for media in sorted(ctx.media, key=lambda m: m.media_id):
            if not media.path_or_url:
                continue
            path = resolve_local_path(media.path_or_url, ctx.media_root)
            if path is None or not path.is_file() or is_readable_image(path):
                continue
            findings.append(
                self.make_finding(
                    severity=severity,
                    entity=EntityRef(type="media", id=media.media_id, field="path_or_url"),
                    entity_id_for_fingerprint=media.media_id,
                    evidence_keys=[media.path_or_url],
                    summary=f"Media {media.media_id} exists but cannot be decoded as an image.",
                    explanation=(
                        f"The file for media {media.media_id} at {media.path_or_url!r} exists but "
                        f"could not be opened as a valid image."
                    ),
                    recommendation="Replace the corrupt file or correct the media type.",
                    evidence=[_ev(media, "path_or_url", media.path_or_url)],
                )
            )
        return findings


def _ev(media: object, field: str, value: str | None) -> EvidenceItem:
    ref = media.source_ref  # type: ignore[attr-defined]
    return EvidenceItem(
        source_file=ref.source_file,
        source_row=ref.source_row_number,
        field=field,
        value=value,
    )
