#!/usr/bin/env python3
"""Fetch or extract a BOUNDED sample of a museum open-data export.

Phase 4 tooling (BUILD_BRIEF.md Section 24) with the Section 20 safety rule baked in: this never
downloads a whole dataset. Every path is bounded by --limit through
`collection_integrity.ingestion.sampling.take_bounded_lines`, and you must explicitly pass either a
local --from path or an explicit --url. There is no default remote and nothing is fetched
automatically.

Metadata for all three sources is CC0 (see docs/DATA_SOURCES.md); read the licenses before
redistributing. Do not fetch images with this tool.

Examples:
    # Bound a local Met export you already downloaded to 500 rows.
    python scripts/fetch_sample.py --source met --from MetObjects.csv --limit 500 \\
        --output samples/met_sample.csv

    # Bounded network sample (streams and stops after --limit rows).
    python scripts/fetch_sample.py --source cleveland --limit 200 \\
        --url <explicit-openaccess.csv-url> --output samples/cleveland_sample.csv

    # NGA is relational: --from a directory of the objects/constituents/link CSVs.
    python scripts/fetch_sample.py --source nga --from nga_opendata/ --limit 300 \\
        --output samples/nga/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from a checkout without installing.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from collection_integrity.ingestion.sampling import (  # noqa: E402
    bound_nga_directory,
    take_bounded_lines,
)

# Reference URLs only — never fetched unless the user passes --url explicitly.
KNOWN_SOURCES = {
    "met": "https://github.com/metmuseum/openaccess (MetObjects.csv, CC0)",
    "cleveland": "https://github.com/ClevelandMuseumArt/openaccess (openaccess.csv, CC0)",
    "nga": "https://github.com/NationalGalleryOfArt/opendata (objects/constituents CSVs, CC0)",
}

# Absolute safety ceiling regardless of --limit, so a typo can't request millions of rows.
MAX_LIMIT = 100_000


def _stream_url_lines(url: str, limit: int) -> list[str]:
    import urllib.request

    with urllib.request.urlopen(url) as response:  # noqa: S310 - user-supplied explicit URL
        text_lines = (line.decode("utf-8", errors="replace").rstrip("\n") for line in response)
        return take_bounded_lines(text_lines, limit)


def _bound_single_file(args: argparse.Namespace, limit: int) -> None:
    if args.from_path is not None:
        lines = Path(args.from_path).read_text(encoding="utf-8").splitlines()
        kept = take_bounded_lines(lines, limit)
    else:
        kept = _stream_url_lines(args.url, limit)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    print(f"Wrote {max(len(kept) - 1, 0)} data row(s) to {out}")


def _bound_nga(args: argparse.Namespace, limit: int) -> None:
    if args.from_path is None:
        raise SystemExit("nga sampling requires --from <directory> (relational, multi-file)")
    counts = bound_nga_directory(Path(args.from_path), Path(args.output), limit)
    print(f"Wrote NGA sample to {args.output}: {counts}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--source", required=True, choices=sorted(KNOWN_SOURCES))
    parser.add_argument(
        "--from", dest="from_path", help="Local source file (or directory for nga)."
    )
    parser.add_argument("--url", help="Explicit source URL to stream a bounded sample from.")
    parser.add_argument("--limit", type=int, required=True, help="Max records (data rows/objects).")
    parser.add_argument("--output", required=True, help="Output file (or directory for nga).")
    args = parser.parse_args(argv)

    if (args.from_path is None) == (args.url is None):
        parser.error("provide exactly one of --from (local) or --url (explicit remote)")
    if args.limit < 0 or args.limit > MAX_LIMIT:
        parser.error(f"--limit must be between 0 and {MAX_LIMIT}")

    if args.source == "nga":
        _bound_nga(args, args.limit)
    else:
        _bound_single_file(args, args.limit)


if __name__ == "__main__":
    main()
