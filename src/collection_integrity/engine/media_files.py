"""Local media-file helpers for the MEDIA rules (BUILD_BRIEF.md Section 11, items 12-15).

All file access is read-only and guarded: a media path that escapes the configured media root (via
`..` or an absolute path) is rejected rather than followed, addressing the path-traversal item in
the threat model. Image reading is bounded by Pillow's own decompression-bomb protection.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError

REMOTE_PREFIXES = ("http://", "https://", "ftp://", "s3://")


def resolve_local_path(path_or_url: str, media_root: Path) -> Path | None:
    """Resolve a media reference to a file under `media_root`, or None if not a safe local path.

    Returns None for remote URLs and for any path that resolves outside `media_root`.
    """
    if not path_or_url or path_or_url.startswith(REMOTE_PREFIXES):
        return None

    root = media_root.resolve()
    candidate = (root / path_or_url).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None  # path traversal attempt; refuse to follow it
    return candidate


def read_image_size(path: Path) -> tuple[int, int] | None:
    """Return (width, height) for a readable image, or None if it cannot be decoded."""
    try:
        with Image.open(path) as img:
            return int(img.width), int(img.height)
    except (UnidentifiedImageError, OSError, ValueError):
        return None


def is_readable_image(path: Path) -> bool:
    """True if the file can be opened and verified as an image."""
    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except (UnidentifiedImageError, OSError, ValueError):
        return False
