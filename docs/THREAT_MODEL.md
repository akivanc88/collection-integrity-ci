# Threat model

This document addresses `BUILD_BRIEF.md` Section 18. It is the evidence artifact for validation
loop **VL-04** (see `docs/VALIDATION_LOOPS.md`): every item below is either pinned by an adversarial
fixture and a passing test, or carries a documented rationale for why it does not apply to the
current feature set.

Design invariants that hold across all items:

- **Ingestion is read-only.** The tool never writes back to source files (CLAUDE.md safety
  constraint). Source content is treated as data, never executed.
- **The core path is offline.** No network calls and no AI providers in `scan`/`benchmark`; the run
  manifest records `network_access_used: false` and `ai_providers_used: false`, and tests assert it.
- **Failure is clean.** Hostile input yields a controlled exit code (2 = invalid input,
  BUILD_BRIEF.md Section 13), never an unhandled traceback (enforced by VL-05).

## Coverage table

| # | Threat (Section 18) | Status | Evidence |
|---|---------------------|--------|----------|
| 1 | Malicious CSV cells / spreadsheet formula injection | **Mitigated** | `reporting/csv_report.py::_neutralize` prefixes any cell leading with `= + - @ TAB CR` with `'` before writing `findings.csv`. Test: `test_formula_injection_neutralized_in_findings_csv` + fixture `tests/fixtures/adversarial/objects_formula_injection.csv`. |
| 2 | Path traversal in media paths | **Mitigated** | `engine/media_files.py::resolve_local_path` resolves against the media root and rejects anything that escapes it (`../…`, absolute paths). Test: `test_media_path_traversal_refused`. |
| 3 | Symlink traversal | **Mitigated** | `resolve_local_path` calls `Path.resolve()` (which follows symlinks) *before* the containment check, so a symlink inside the root pointing outside is refused. Test: `test_media_symlink_escaping_root_refused`. |
| 4 | Extremely large or malformed files | **Mitigated** | Malformed CSV (bad UTF-8, NUL, embedded quotes) → `IngestionError`/`CsvIngestionError` → exit 2 (VL-05 fuzz suite). An oversized single cell hits Python's csv field-size limit and is rejected cleanly. Tests: `tests/property/test_scan_contract_fuzz.py`, `test_oversized_cell_rejected_cleanly`. |
| 5 | Image decompression bombs | **Mitigated** | Image reads go through Pillow, whose decompression-bomb guard raises `DecompressionBombError`; `engine/media_files.py` catches it (and `UnidentifiedImageError`/`OSError`) and returns `None`/`False` rather than decoding. Test: `test_decompression_bomb_image_handled`. |
| 6 | Zip bombs (archive support) | **Not applicable** | No archive/zip ingestion exists. Inputs are plain CSV/JSON files. Revisit if archive support is ever added (tracked as a precondition in `docs/BACKLOG.md`). |
| 7 | Untrusted HTML / script in titles & descriptions | **Mitigated** | The HTML report renders through Jinja2 with `select_autoescape(default=True)`; all source-derived text is escaped, never live markup. Test: `tests/unit/test_html_report.py::test_report_escapes_untrusted_content`. The web viewer is covered separately by `tests/integration/test_viewer_ui.py`. |
| 8 | Prompt injection in collection metadata | **Not applicable** | The core execution path uses no LLM/AI provider (CLAUDE.md safety constraint; manifest asserts `ai_providers_used: false`). Any future AI-assisted rule is an opt-in, disabled-by-default adapter that would carry its own threat entry. |
| 9 | Accidental upload of private collection data | **Mitigated (by design)** | The tool is local-first and offline: no network egress in the core path, and `profile`/`scan` never send data externally. The manifest records `network_access_used: false`, asserted in `tests/integration/test_scan_cli.py::test_scan_writes_all_report_outputs`. |
| 10 | Secrets in configuration | **Mitigated (by design)** | No API keys or secrets are required or read. CI workflows declare no secrets (`.github/workflows/ci.yml`, `permissions: contents: read`). Mapping/ruleset YAML describe columns and thresholds only. |
| 11 | Denial of service from pathological records | **Mitigated** | Rules are deterministic single passes; source sampling is bounded (`ingestion/sampling.py`). A large row count with a within-limit large cell completes cleanly. Test: `test_pathological_row_volume_completes`. |
| 12 | Hashing and provenance integrity | **Mitigated** | `provenance.py::hash_record` gives each record a stable content hash; input files are hashed into the run manifest; finding fingerprints are deterministic and order-invariant (VL-02). Tests: `tests/property/test_fingerprint_determinism.py`, manifest `input_hashes` assertions in `test_scan_cli.py`. |
| 13 | Incorrect legal interpretation of rights fields | **Documented non-goal** | Rights findings are policy-*consistency* checks, not legal advice — stated in the HTML report disclaimer and BUILD_BRIEF.md non-goals (Section 6). The tool is explicitly not a rights/legal authority (CLAUDE.md). |
| 14 | Overconfidence in probabilistic findings | **Not applicable (yet)** | The shipped rules are all deterministic. The optional probabilistic experiment (Phase 6) is disabled by default and, when built, must label findings as probabilistic and keep them out of the failure threshold by default. |
| 15 | Supply-chain dependency risks | **Partially mitigated** | Dependencies are pinned via `uv.lock`; CI installs with `uv sync --locked`. The dependency set is small and mainstream (pydantic, typer, jinja2, pillow, fastapi). A `pip-audit`/dependency-audit CI step is tracked in `docs/BACKLOG.md` as a follow-up. |

## Notes on residual risk

- **Item 15** is the one open hardening item: a scheduled dependency audit (`pip-audit` or
  equivalent) would catch newly disclosed CVEs in pinned dependencies. It is deferred, not ignored,
  and recorded in `docs/BACKLOG.md`.
- **Items 6, 8, 14** are "not applicable" strictly because the corresponding feature (archives,
  LLM calls, probabilistic scoring) does not exist in the core product. If any is added, this table
  must gain a real mitigation and test for it before that feature ships.
