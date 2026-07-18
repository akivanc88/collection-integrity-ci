"""Hashing helpers used to build provenance records (BUILD_BRIEF.md Section 9)."""

from __future__ import annotations

import hashlib
from pathlib import Path


def hash_file(path: Path) -> str:
    """Return a stable sha256 hex digest of a file's contents."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_record(fields: dict[str, str]) -> str:
    """Return a stable sha256 hex digest of a row's raw field values.

    Keys are sorted so the hash does not depend on column order.
    """
    digest = hashlib.sha256()
    for key in sorted(fields):
        digest.update(key.encode("utf-8"))
        digest.update(b"\0")
        digest.update((fields[key] or "").encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()
