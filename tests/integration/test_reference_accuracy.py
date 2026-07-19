"""REF001 accuracy validation on the AI-generated multi-entity dataset.

Generates objects + media, confirms zero findings on the clean pair, then injects orphan-media
references and confirms REF001 recovers exactly those, at precision = recall = 1.0.
"""

from pathlib import Path

from collection_integrity.benchmark.dataset import write_objects_csv
from collection_integrity.benchmark.injectors import (
    InjectionManifest,
    inject_orphan_media,
)
from collection_integrity.benchmark.metrics import score
from collection_integrity.benchmark.synthetic import (
    MEDIA_COLUMNS,
    OBJECT_COLUMNS,
    generate_clean_media,
    generate_clean_objects,
)
from collection_integrity.ingestion.mapper import load_mapping, load_media, load_objects
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.registry import RuleRegistry

MAPPING = """version: 1
dataset:
  name: bench-media
  format: csv
  base_path: .
entities:
  objects:
    file: objects.csv
    primary_key: object_id
    fields:
      object_id: object_id
      accession_number: accession_number
      object_name: object_name
      title: title
  media:
    file: media.csv
    primary_key: media_id
    fields:
      media_id: media_id
      object_id: object_id
      path_or_url: path_or_url
"""


def _scan(tmp_path: Path) -> list:  # type: ignore[type-arg]
    (tmp_path / "map.yaml").write_text(MAPPING, encoding="utf-8")
    mapping = load_mapping(tmp_path / "map.yaml")
    objects = load_objects(mapping, base_dir=tmp_path)
    media = load_media(mapping, base_dir=tmp_path)
    ctx = RuleContext(objects=objects, media=media, required_fields=["accession_number"])
    return RuleRegistry.with_defaults().evaluate(ctx)


def test_clean_object_media_pair_has_no_ref001(tmp_path: Path) -> None:
    objects = generate_clean_objects(count=40, seed=7)
    media = generate_clean_media(objects, seed=13)
    write_objects_csv(objects, tmp_path / "objects.csv", OBJECT_COLUMNS)
    write_objects_csv(media, tmp_path / "media.csv", MEDIA_COLUMNS)

    findings = _scan(tmp_path)

    assert [f for f in findings if f.rule.id == "REF001_ORPHAN_MEDIA_OBJECT"] == []


def test_injected_orphans_detected_with_perfect_precision_recall(tmp_path: Path) -> None:
    objects = generate_clean_objects(count=40, seed=7)
    media = generate_clean_media(objects, seed=13)
    object_ids = {o["object_id"] for o in objects}

    dirty_media, errors = inject_orphan_media(media, object_ids, seed=21, num_orphan=5)
    manifest = InjectionManifest(seed=21, errors=errors)

    write_objects_csv(objects, tmp_path / "objects.csv", OBJECT_COLUMNS)
    write_objects_csv(dirty_media, tmp_path / "media.csv", MEDIA_COLUMNS)

    findings = _scan(tmp_path)
    m = score(findings, manifest)["REF001_ORPHAN_MEDIA_OBJECT"]

    assert m.precision == 1.0, m
    assert m.recall == 1.0, m
    assert m.true_positives == 5, m


def test_orphan_injection_does_not_mutate_input() -> None:
    objects = generate_clean_objects(count=20, seed=1)
    media = generate_clean_media(objects, seed=2)
    snapshot = [dict(r) for r in media]

    inject_orphan_media(media, {o["object_id"] for o in objects}, seed=3, num_orphan=2)

    assert media == snapshot
