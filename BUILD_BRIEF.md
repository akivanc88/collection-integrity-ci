# Claude Code Build Brief: Collection Integrity CI

This file, `BUILD_BRIEF.md`, is the authoritative product, architecture, scope, safety, testing, and delivery specification for this repository. Do not paste the full specification into Claude Code as a chat message. Instead, paste the short **Kickoff Prompt** below into Claude Code from the root of a new Git repository; it instructs Claude Code to read this file in full before doing anything else.

Suggested repository name: `collection-integrity-ci`

---

## Suggested local setup

```bash
mkdir collection-integrity-ci
cd collection-integrity-ci
git init
claude
```

Follow Anthropic's current official Claude Code setup instructions if `claude` is not already installed. Run `claude doctor` after installation or upgrades.

---

# Kickoff Prompt

Paste this into Claude Code to start the build.

> Read BUILD_BRIEF.md in full before making changes.
>
> Treat it as the authoritative product, architecture, scope, safety, testing, and delivery specification for this repository.
>
> Begin with the Phase 0 and Phase 1 instructions in the brief. Do not stop after producing a plan. Continue immediately into the smallest tested end-to-end implementation.
>
> Follow these operating rules:
>
> - Work autonomously on reversible implementation choices.
> - Ask me only when a decision requires credentials, paid infrastructure, an external account, a download larger than 1 GB, a remote push, or a material scope change.
> - Do not push code or deploy anything without my explicit approval. Publishing the repository and the GitHub Pages showcase is a planned end-of-build step (Phase 7) that requires my sign-off.
> - Do not use paid AI services in the core execution path.
> - Do not modify source collection data.
> - Do not start the web interface until the CLI, deterministic rule engine, reports, benchmark, and tests work.
> - Run tests and inspect outputs before claiming that anything works.
> - Maintain docs/PROGRESS.md with commands run, results, limitations, and the next implementation slice.
> - Make small local commits only after the relevant checks pass.
> - Never weaken or delete tests merely to make the build pass.
>
> Start now by:
>
> - inspecting the repository and Git status
> - creating CLAUDE.md
> - creating the planning and product documents required by the brief
> - scaffolding the Python project
> - implementing the first vertical slice from CSV ingestion through duplicate-accession detection to console and JSON output
> - adding tests
> - running those tests
> - continuing through Phase 1
>
> At the end of this working session, report exactly:
>
> - what was implemented
> - files created or changed
> - commands run
> - test, lint, and type-check results
> - known limitations
> - the next highest-value implementation slice

---

# Specification

You are the lead engineer, technical architect, test engineer, and product-minded implementation partner for a portfolio-quality open-source project called **Collection Integrity CI**.

Your job is not merely to scaffold a demo. Build a credible, testable, evidence-first product that a museum registrar, collections data manager, digital collections manager, archive, historical society, or university collection could evaluate locally.

Work autonomously inside this repository. Make reasonable reversible decisions without repeatedly asking me questions. Ask only when a choice is irreversible, requires credentials or paid infrastructure, would download more than 1 GB, creates an external account, pushes code remotely, or materially changes the product scope.

Do not push to GitHub, deploy cloud infrastructure, purchase services, or expose credentials without explicit approval. Publishing the repository and the GitHub Pages showcase (Phase 7) is a planned, approval-gated step, not a default action. Local commits are allowed after tests pass. Never use `--dangerously-skip-permissions`. Never claim that a feature works until you have run the relevant command or test and inspected the result.

## 1. Product thesis

Museums and cultural heritage organizations often have systems that store object records, media records, rights information, location history, people or maker records, and publication metadata. The practical integrity problem is that these records can disagree with one another.

Collection Integrity CI is a portable quality-assurance layer that checks whether collection records, media, identifiers, rights, dates, and locations agree before data is migrated, published, imported, shared, or released.

The product should feel like:

> GitHub Actions and data quality CI for museum collection records.

It must not attempt to replace a collection management system. It must ingest exported data, run transparent rules, produce evidence-backed findings, and help a human resolve exceptions.

## 2. Target users

Primary users:

1. Museum registrar
2. Collections data manager
3. Digital collections manager
4. Collection management system administrator
5. Archivist or historical society staff member preparing a migration
6. Technical consultant cleaning or validating collection exports

Secondary users:

1. Developers maintaining public collection data
2. Researchers using open museum datasets
3. Data governance and rights-management staff
4. Museum leadership reviewing collection-data readiness

## 3. Core jobs to be done

The product should help users answer:

1. Are identifiers unique and stable?
2. Do all media, rights, people, and location references point to valid records?
3. Is an object assigned to exactly one current location when policy requires it?
4. Is media marked for publication while rights data says publication is not permitted or is unresolved?
5. Are required fields missing?
6. Are date ranges internally consistent?
7. Are controlled vocabulary values valid?
8. Are image files present, readable, and linked to the expected object?
9. Are duplicate media files represented as separate assets?
10. What changed between the current scan and the previous scan?
11. Which findings are deterministic facts, which are policy warnings, and which are probabilistic AI suggestions?
12. Can every finding be explained with source location, evidence, rule version, and remediation guidance?
13. Can the results be consumed locally, in CI, and through a simple web interface?

## 4. Product principles

Follow these principles throughout the implementation:

### Evidence over assertion

Every finding must include:

- rule identifier and version
- severity
- verification type
- affected entity and field
- source file and source row or JSON pointer when available
- evidence values
- human-readable explanation
- remediation guidance
- stable fingerprint for deduplication
- run identifier and timestamp

### Deterministic before probabilistic

Use deterministic code for schema, reference, rights-policy, date, vocabulary, file, hash, and dimension checks. Do not use an LLM for a check that can be expressed reliably in code.

### Human authority

Probabilistic findings are suggestions for review. The system must not silently rewrite museum records, determine legal rights, value objects, authenticate objects, attribute artists, or make conservation decisions.

### Local-first and privacy-preserving

The core product must work without network access and without paid API keys. External AI providers must be optional adapters. Do not upload collection images or data by default.

### Source preservation

Never modify source files during a scan. Preserve raw values and provenance. Any future remediation feature must generate a patch or proposed change, not overwrite source data.

### Bounded scope

Build the collection-data QA engine first. Do not build inventory photography, mobile shelf scanning, a complete CMS, public collection search, semantic discovery, generative descriptions, or a rights-management system in the MVP.

### Honest claims

Document limitations. Synthetic benchmark errors are not proof of performance on real institutional errors. A rights-policy conflict is not legal advice. A visual mismatch score is not proof that an image depicts the wrong object.

## 5. MVP scope

The first credible release must provide:

1. A Python package and command-line interface named `collection-ci`
2. CSV and JSON ingestion
3. Configurable mapping from source columns to a canonical model
4. YAML ruleset configuration
5. A deterministic rule engine
6. At least ten implemented rules
7. Structured findings in JSON and CSV
8. A standalone HTML report
9. SARIF output suitable for GitHub code-scanning annotations
10. A run manifest containing configuration, input hashes, software version, and summary counts
11. A clean example dataset
12. A deliberately corrupted example dataset
13. A deterministic error-injection utility and labeled benchmark manifest
14. Unit, integration, property-based, and end-to-end tests
15. GitHub Actions for lint, type checking, tests, package build, and a sample collection scan
16. Documentation, architecture decisions, threat model, data card, benchmark report, and demo script
17. A basic local web viewer only after the CLI and engine are complete and tested

## 6. Explicit non-goals for the MVP

Do not implement these in the first release:

- replacing CollectionSpace, TMS, Axiell, PastPerfect, or another CMS
- automatic editing of source records
- legal conclusions about copyright or ownership
- artwork authentication or valuation
- artist attribution
- facial recognition
- live mobile shelf scanning
- full-text semantic search
- cloud multi-tenancy
- enterprise identity or billing
- downloading the full 158 GB ArtiFact dataset
- training a new vision model
- requiring an Anthropic, OpenAI, or other paid model key
- Kubernetes or unnecessarily complex infrastructure

Create a `docs/FUTURE_SCOPE.md` file for ideas outside the MVP.

## 7. Recommended technology choices

Use the following unless repository constraints make one inappropriate. Record deviations in an architecture decision record.

### Core

- Python 3.12 or the current stable Python version supported by all selected libraries
- `uv` for dependency and environment management
- Pydantic v2 for configuration and domain validation
- Polars for efficient table processing
- DuckDB for local analytical persistence and run history
- Typer for the CLI
- Jinja2 for the standalone HTML report
- PyYAML or `ruamel.yaml` for YAML
- Pillow for image metadata and file validation
- `jsonschema` where useful for external schema validation
- `structlog` or standard structured logging
- `rich` for readable CLI output

### Quality

- pytest
- Hypothesis for property-based tests
- Ruff for lint and formatting
- mypy or pyright for type checking
- coverage.py with a meaningful threshold
- pre-commit
- pip-audit or an equivalent dependency audit

### Web viewer, only after core MVP

Prefer a lightweight architecture. Use FastAPI for the API. A small React and TypeScript client is acceptable, but do not let frontend work delay the core engine. A server-rendered FastAPI, Jinja, and HTMX implementation is also acceptable if it produces a polished accessible interface with less complexity.

### Packaging

- `pyproject.toml`
- reproducible lockfile
- console entry point `collection-ci`
- Dockerfile only after native local setup works
- no runtime dependency on Docker

## 8. Proposed repository structure

Create a structure close to this:

```text
collection-integrity-ci/
├── CLAUDE.md
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── pyproject.toml
├── uv.lock
├── Makefile
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── mkdocs.yml
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── collection-integrity-demo.yml
│   │   └── pages.yml
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── src/
│   └── collection_integrity/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── logging.py
│       ├── provenance.py
│       ├── canonical/
│       │   ├── models.py
│       │   ├── mappings.py
│       │   └── normalization.py
│       ├── ingestion/
│       │   ├── base.py
│       │   ├── csv_adapter.py
│       │   ├── json_adapter.py
│       │   ├── met_adapter.py
│       │   ├── cleveland_adapter.py
│       │   └── nga_adapter.py
│       ├── rules/
│       │   ├── base.py
│       │   ├── registry.py
│       │   ├── schema_rules.py
│       │   ├── reference_rules.py
│       │   ├── rights_rules.py
│       │   ├── location_rules.py
│       │   ├── date_rules.py
│       │   ├── vocabulary_rules.py
│       │   └── media_rules.py
│       ├── engine/
│       │   ├── scanner.py
│       │   ├── planner.py
│       │   ├── findings.py
│       │   ├── fingerprints.py
│       │   ├── baselines.py
│       │   └── run_store.py
│       ├── reporting/
│       │   ├── console.py
│       │   ├── json_report.py
│       │   ├── csv_report.py
│       │   ├── html_report.py
│       │   └── sarif_report.py
│       ├── benchmark/
│       │   ├── injectors.py
│       │   ├── evaluator.py
│       │   └── metrics.py
│       └── api/
│           ├── app.py
│           ├── routes.py
│           └── schemas.py
├── schemas/
│   ├── collection-config.schema.json
│   ├── ruleset.schema.json
│   ├── finding.schema.json
│   └── run-manifest.schema.json
├── rulesets/
│   ├── core.yaml
│   └── example-small-museum.yaml
├── examples/
│   ├── clean/
│   ├── dirty/
│   ├── mappings/
│   └── expected/
├── benchmarks/
│   ├── mini/
│   ├── manifests/
│   └── reports/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── property/
│   ├── e2e/
│   └── fixtures/
└── docs/
    ├── index.md
    ├── built.md
    ├── about.md
    ├── PRD.md
    ├── BUILD_PLAN.md
    ├── BACKLOG.md
    ├── PROGRESS.md
    ├── DOMAIN_MODEL.md
    ├── RULE_AUTHORING.md
    ├── DATA_SOURCES.md
    ├── BENCHMARK.md
    ├── THREAT_MODEL.md
    ├── DATA_CARD.md
    ├── MODEL_CARD.md
    ├── DEMO.md
    ├── FUTURE_SCOPE.md
    ├── LOOP_ENGINEERING.md
    ├── prompts/
    └── adr/
```

`docs/index.md`, `docs/built.md`, and `docs/about.md` are the three MkDocs pages for the Phase 7 showcase site (product-led home, "How this was built", and "About the builder", respectively); `mkdocs.yml` sets `docs_dir: docs` so the same `docs/` directory serves both the engineering documentation and the published site. `docs/prompts/` holds the Kickoff Prompt for provenance, per Section 26A.

Modify the structure when implementation evidence warrants it, but keep boundaries clear.

## 9. Canonical data model

Create Pydantic domain models that preserve source provenance.

### SourceRef

Fields:

- `source_name`
- `source_file`
- `source_record_id`
- `source_row_number`, optional
- `json_pointer`, optional
- `source_hash`
- `ingested_at`
- `raw_fields`, optional or separately persisted

### CollectionObject

Minimum fields:

- `object_id`
- `accession_number`
- `title`
- `object_name`
- `description`
- `maker_ids`
- `production_start_date`
- `production_end_date`
- `materials`
- `techniques`
- `department`
- `culture`
- `current_location_id`
- `rights_id`
- `media_ids`
- `publication_status`
- `source_ref`

### MediaAsset

Minimum fields:

- `media_id`
- `object_id`
- `path_or_url`
- `media_type`
- `mime_type`
- `width`
- `height`
- `file_size`
- `checksum`
- `is_primary`
- `publication_status`
- `rights_id`
- `source_ref`

### RightsRecord

Minimum fields:

- `rights_id`
- `rights_status`
- `copyright_holder`
- `license_uri`
- `credit_line`
- `publication_allowed`
- `review_required`
- `expiry_date`
- `source_ref`

### LocationRecord

Minimum fields:

- `location_id`
- `name`
- `parent_location_id`
- `is_current`
- `effective_start`
- `effective_end`
- `source_ref`

### AgentOrMaker

Minimum fields:

- `agent_id`
- `preferred_name`
- `alternate_names`
- `birth_date`
- `death_date`
- `nationality`
- `external_identifiers`
- `source_ref`

Not every input must supply every field. Mapping configuration must describe which fields exist and which are required by policy.

## 10. Configuration design

Use two clear configuration layers.

### Dataset mapping

Example:

```yaml
version: 1
dataset:
  name: example-small-museum
  format: csv
  base_path: ./examples/clean

entities:
  objects:
    file: objects.csv
    primary_key: object_id
    fields:
      object_id: object_id
      accession_number: accession_number
      title: title
      object_name: object_name
      production_start_date: date_start
      production_end_date: date_end
      current_location_id: current_location_id
      rights_id: rights_id
      media_ids:
        source: media_ids
        transform: split_pipe

  media:
    file: media.csv
    primary_key: media_id
    fields:
      media_id: media_id
      object_id: object_id
      path_or_url: path
      width: width
      height: height
      publication_status: publication_status
      rights_id: rights_id

  rights:
    file: rights.csv
    primary_key: rights_id
    fields:
      rights_id: rights_id
      rights_status: rights_status
      publication_allowed: publication_allowed
      review_required: review_required

  locations:
    file: locations.csv
    primary_key: location_id
    fields:
      location_id: location_id
      name: name
      parent_location_id: parent_location_id
      is_current: is_current
```

### Ruleset

Example:

```yaml
version: 1
profile: small-museum-core

defaults:
  fail_on_severity: high
  enabled: true

controlled_vocabularies:
  publication_status:
    - private
    - internal
    - public
  rights_status:
    - public_domain
    - institution_owned
    - licensed
    - restricted
    - unknown
    - review_required

rules:
  - id: CORE001
    type: unique
    entity: objects
    field: accession_number
    severity: critical

  - id: CORE002
    type: required
    entity: objects
    fields:
      - object_id
      - accession_number
      - object_name
    severity: high

  - id: REF001
    type: foreign_key
    from:
      entity: media
      field: object_id
    to:
      entity: objects
      field: object_id
    severity: high

  - id: RIGHTS001
    type: publication_rights_conflict
    severity: critical
    options:
      public_values:
        - public
      allowed_rights_values:
        - public_domain
        - institution_owned
        - licensed
```

Validate all configuration against published JSON Schemas. Return actionable configuration errors with line and field context where possible.

## 11. Initial deterministic rules

Implement and test at least these rules. Use stable rule IDs and documented versions.

1. `CORE001_DUPLICATE_ACCESSION_NUMBER`
   - Detect duplicate non-empty accession numbers.
   - Include all affected records as evidence.

2. `CORE002_REQUIRED_FIELD_MISSING`
   - Required fields are ruleset-specific.
   - Treat whitespace-only strings as missing.

3. `SCHEMA001_INVALID_FIELD_TYPE`
   - Detect values that cannot be parsed according to the mapping or canonical field type.
   - Preserve the raw value.

4. `REF001_ORPHAN_MEDIA_OBJECT`
   - A media record references an object that does not exist.

5. `REF002_ORPHAN_RIGHTS_REFERENCE`
   - An object or media record references a missing rights record.

6. `LOC001_MULTIPLE_CURRENT_LOCATIONS`
   - An object has more than one location marked current when the profile requires a single current location.

7. `LOC002_INVALID_LOCATION_HIERARCHY`
   - Detect missing parents and cycles in location hierarchy.

8. `RIGHTS001_PUBLICATION_CONFLICT`
   - A public object or media asset is linked to a rights record that says publication is not allowed, unknown, restricted, or requires review according to configured policy.
   - This is a policy consistency check, not legal advice.

9. `DATE001_INVERTED_DATE_RANGE`
   - Production start date is after production end date.

10. `DATE002_IMPOSSIBLE_AGENT_LIFESPAN_CONFLICT`
    - Optional policy rule only when maker and production dates are sufficiently precise.
    - Flag impossible relationships conservatively and explain assumptions.
    - Do not overstate uncertain historical dates.

11. `VOCAB001_UNKNOWN_CONTROLLED_VALUE`
    - Value is outside the configured vocabulary.

12. `MEDIA001_LOCAL_FILE_MISSING`
    - A configured local media path does not exist.

13. `MEDIA002_DUPLICATE_FILE_HASH`
    - Two media IDs resolve to identical content.
    - This is a duplicate-file warning, not proof that one record should be deleted.

14. `MEDIA003_IMAGE_BELOW_MINIMUM_DIMENSIONS`
    - Dimensions fail configured publication requirements.

15. `MEDIA004_UNREADABLE_IMAGE`
    - File exists but cannot be decoded or is not the declared media type.

The engine must support enabling, disabling, and changing severity per rule.

## 12. Finding model

Create a versioned finding schema resembling:

```json
{
  "schema_version": "1.0",
  "finding_id": "run-specific-id",
  "fingerprint": "stable-cross-run-hash",
  "rule": {
    "id": "RIGHTS001",
    "name": "Publication rights conflict",
    "version": "1.0.0"
  },
  "severity": "critical",
  "verification_type": "deterministic",
  "status": "open",
  "entity": {
    "type": "media",
    "id": "IMG-4417",
    "field": "publication_status"
  },
  "summary": "Public media is linked to a rights record that does not permit publication.",
  "explanation": "Media IMG-4417 has publication_status=public while rights record R-18 has publication_allowed=false.",
  "evidence": [
    {
      "source_file": "media.csv",
      "source_row": 42,
      "field": "publication_status",
      "value": "public"
    },
    {
      "source_file": "rights.csv",
      "source_row": 19,
      "field": "publication_allowed",
      "value": false
    }
  ],
  "recommendation": "Send the record for rights review or change publication status according to institutional policy.",
  "confidence": 1.0,
  "created_at": "ISO-8601 timestamp"
}
```

Stable fingerprints should be based on normalized rule ID, entity identity, affected field, and stable evidence keys, not the run timestamp.

Support future finding statuses:

- open
- acknowledged
- accepted_risk
- false_positive
- resolved
- suppressed

Do not implement a complex workflow in the first CLI release, but design the schema for it.

## 13. CLI specification

Implement these commands.

### Initialize a project

```bash
collection-ci init ./my-collection
```

Creates example mapping, ruleset, directories, and explanatory comments without overwriting existing files.

### Profile inputs

```bash
collection-ci profile \
  --mapping config/mapping.yaml \
  --output build/profile.json
```

Reports row counts, columns, inferred types, missingness, candidate keys, duplicate rates, and sample values. Do not send data externally.

### Run a scan

```bash
collection-ci scan \
  --mapping config/mapping.yaml \
  --rules rulesets/core.yaml \
  --output-dir build/scan
```

Expected outputs:

- `findings.json`
- `findings.csv`
- `report.html`
- `results.sarif`
- `run_manifest.json`
- `summary.json`

Support:

- `--fail-on critical|high|medium|low|none`
- `--baseline path/to/findings.json`
- `--only-new`
- `--rule RULE_ID`
- `--entity ENTITY_TYPE`
- `--no-media-files`
- `--format console|json`

Exit codes:

- 0: scan completed and failure threshold not reached
- 1: failure threshold reached
- 2: invalid configuration or input
- 3: internal execution failure

Document exact semantics.

### Explain a finding or rule

```bash
collection-ci explain RIGHTS001
collection-ci explain --finding build/scan/findings.json --id <finding-id>
```

### Inject benchmark errors

```bash
collection-ci inject-errors \
  --input examples/clean \
  --output benchmarks/generated/dirty \
  --manifest benchmarks/manifests/generated.json \
  --seed 42
```

The injector must be deterministic by seed and must not mutate its input.

### Benchmark

```bash
collection-ci benchmark \
  --mapping benchmarks/generated/mapping.yaml \
  --rules rulesets/core.yaml \
  --labels benchmarks/manifests/generated.json \
  --output benchmarks/reports/latest
```

Report precision, recall, F1, counts, runtime, and per-rule results.

### Serve reports

```bash
collection-ci serve --run-dir build/scan
```

Initially this may serve the generated HTML report. A richer local viewer can follow later.

## 14. Reporting requirements

### Console

Provide a concise summary, severity counts, top rules, input counts, elapsed time, and output paths.

### JSON

Strictly validate against the finding schema.

### CSV

Flatten useful columns while keeping a JSON evidence column where needed.

### HTML

Produce a standalone, accessible HTML file that can be opened without a server. It must include:

- run summary
- severity distribution
- filterable findings table
- rule descriptions
- evidence details
- input and configuration provenance
- limitations and disclaimers

Do not use externally hosted JavaScript or CSS in the standalone report.

### SARIF

Produce valid SARIF 2.1.0. Map findings to source files and lines when available. Include rule metadata, severity, help text, and stable fingerprints. Add a test that validates the SARIF structure.

### Run manifest

Include:

- software version
- command
- run ID
- start and end timestamps
- input file hashes
- mapping hash
- ruleset hash
- enabled rules and versions
- environment information that is safe to record
- counts and elapsed time
- whether network access or AI providers were used
- warnings and skipped checks

## 15. Baselines and regression behavior

Support a baseline findings file.

The scan should classify findings as:

- new
- unchanged
- resolved since baseline

`--only-new` should cause the threshold decision to consider only new findings.

Document that a baseline suppresses noise for CI but does not make existing issues disappear from the full report.

Add tests for fingerprint stability, baseline matching, and resolved findings.

## 16. Benchmark design

Create a small, reproducible benchmark that ships with the repository.

### Clean fixture

Build a synthetic but realistic small collection with:

- at least 250 objects
- at least 350 media records
- at least 20 locations
- at least 100 agent or maker records
- at least 30 rights records
- local generated placeholder images for a subset

Do not copy protected collection images into the repository. Generate simple local test images with labels and shapes, or use explicitly permitted tiny fixtures with attribution.

### Error injection

Implement injectors for each deterministic rule. The manifest must record:

- injected error ID
- rule expected to detect it
- affected entity and field
- before value
- after value
- random seed
- injection timestamp
- whether multiple rules may validly detect it

Avoid label leakage into fields scanned by the engine.

### Metrics

For deterministic injected errors, target:

- exact detection of the expected entity and rule
- precision and recall near 1.0
- zero findings on the clean golden dataset except explicitly documented warnings

When results differ, fix the implementation or document why the expected label was wrong.

### ArtiFact extension

After the local benchmark works, add documentation and an optional adapter or evaluation script for a small sampled subset of the ArtiFact dataset.

Important constraints:

- The full ArtiFact dataset is very large. Do not download it without my explicit approval.
- The dirty split contains synthetic injected errors and does not represent claims about source museums.
- Inspect the dataset card and paper before mapping error categories. Do not invent the seven categories.
- Store only scripts and manifests in the repository, not large downloaded data.
- Provide checksum and provenance instructions.
- Keep deterministic and multimodal benchmark results separate.

## 17. Optional probabilistic rule interface

Design, but do not require, an interface for future AI-assisted rules.

Example protocol:

```python
class ProbabilisticRule(Protocol):
    rule_id: str
    version: str

    def evaluate(
        self,
        entity: CanonicalEntity,
        context: EvaluationContext,
    ) -> list[Finding]:
        ...
```

Potential future rules:

- image-to-description mismatch
- material visible in image conflicts with catalogued material
- probable duplicate maker identity
- object type inconsistency
- possible temporal or material anachronism

Requirements:

- provider abstraction
- local mock provider for tests
- structured output validation
- recorded model identifier, prompt version, and parameters
- evidence images or text references
- confidence
- human-review requirement
- caching keyed by input hashes
- cost and latency tracking
- prompt-injection resistance
- no agentic tool use triggered by collection metadata
- no automatic record edits

Do not enable probabilistic rules by default.

## 18. Security and threat model

Create `docs/THREAT_MODEL.md` and address:

1. Malicious CSV cells and spreadsheet formula injection
2. Path traversal in media paths
3. Symlink traversal
4. Extremely large or malformed files
5. Image decompression bombs
6. Zip bombs if archive support is later added
7. Untrusted HTML or script content in titles and descriptions
8. Prompt injection in collection metadata
9. Accidental upload of private collection data
10. Secrets in configuration
11. Denial of service from pathological records
12. Hashing and provenance integrity
13. Incorrect legal interpretation of rights fields
14. Overconfidence in probabilistic findings
15. Supply-chain dependency risks

Sanitize HTML output. Never execute source content. Disable network access in tests. Add file-size and image-dimension safeguards.

## 19. Licensing and data ethics

Create `docs/DATA_SOURCES.md` and `docs/DATA_CARD.md`.

For every external dataset:

- record source URL
- license or terms
- access date
- fields used
- transformations
- whether records or images are redistributed
- attribution requirements
- known limitations
- statement that the source institution does not endorse this project

Keep the repository's generated fixtures separate from museum data.

Do not represent synthetic benchmark corruption as a source-museum error.

Choose an appropriate permissive software license, preferably Apache-2.0, unless dependency or project considerations justify another choice. Explain the choice.

## 20. GitHub workflow

Create a CI workflow that runs:

1. dependency installation from lockfile
2. Ruff
3. type checking
4. unit and integration tests
5. coverage
6. package build
7. dependency audit
8. sample collection scan
9. SARIF validation
10. upload of the sample HTML report as a workflow artifact

Create a second demonstration workflow that scans `examples/dirty` and uploads SARIF. Configure the workflow so intentional findings do not incorrectly make the software CI appear broken. Clearly distinguish software test failure from expected collection-data findings.

Do not require secrets for the default workflows.

## 21. Documentation deliverables

### README

The README must include:

- one-sentence value proposition
- problem statement
- screenshot or terminal demo after available
- quick start
- supported inputs
- sample output
- rules
- architecture diagram using Mermaid
- benchmark summary
- limitations
- roadmap
- contributing instructions
- data and licensing statement

### PRD

Create `docs/PRD.md` with:

- target users
- problem
- evidence
- goals
- non-goals
- user journeys
- requirements
- success metrics
- risks
- open questions

### ADRs

At minimum:

- ADR 001: local-first architecture
- ADR 002: canonical model plus configurable mappings
- ADR 003: deterministic rule engine before AI
- ADR 004: stable finding fingerprints and baselines
- ADR 005: SARIF as CI integration format
- ADR 006: benchmark methodology
- ADR 007: web-viewer architecture, when implemented

### Rule authoring guide

Explain how to add a rule, write tests, define evidence, version a rule, and avoid breaking fingerprints.

### Demo guide

Provide a reproducible five-minute demo:

1. scan clean data
2. scan dirty data
3. open the HTML report
4. inspect one rights conflict and one orphan reference
5. run with a baseline and `--only-new`
6. show SARIF in a GitHub workflow
7. run the benchmark

## 22. Success metrics

Instrument or calculate:

- records processed per second
- total scan duration
- peak memory for benchmark runs when practical
- findings by severity and rule
- percentage of findings with exact source location
- deterministic benchmark precision, recall, and F1
- clean-dataset false-positive count
- fingerprint stability across identical runs
- incremental scan difference against baseline
- report-generation time
- optional AI cost and latency, only when AI is enabled

Do not invent user time-savings numbers without a study.

## 23. Accessibility and UX

For any web or HTML interface:

- meet basic WCAG 2.2 AA practices
- support keyboard navigation
- use semantic HTML
- label controls
- do not rely only on color for severity
- provide readable evidence and source locations
- make deterministic versus probabilistic findings visually explicit
- include empty, loading, error, and no-findings states
- do not use dark patterns
- do not hide uncertainty

## 24. Build sequence

Follow this order. Do not start the web UI before Phase 3 passes.

### Phase 0: Research and planning

1. Inspect the repository.
2. Create `CLAUDE.md`.
3. Create `docs/PRD.md`, `docs/BUILD_PLAN.md`, `docs/BACKLOG.md`, and `docs/PROGRESS.md`.
4. Record assumptions and open questions.
5. Read the linked primary resources in the resource section when network access is available.
6. Do not stop after planning. Continue into Phase 1.

### Phase 1: Foundation

1. Set up Python package, uv, linting, typing, testing, logging, and CLI entry point.
2. Implement configuration schemas.
3. Implement canonical models and provenance.
4. Create minimal clean fixtures.
5. Add CI.
6. Run all checks.

### Phase 2: Ingestion and deterministic engine

1. CSV and JSON adapters
2. mapping engine
3. rule base class and registry
4. initial rules
5. finding model and fingerprints
6. run store
7. console and JSON output
8. comprehensive tests

### Phase 3: Reports, baselines, and benchmark

1. CSV, HTML, SARIF, and manifest outputs
2. baseline comparison
3. full clean and dirty examples
4. deterministic error injection
5. benchmark metrics and report
6. end-to-end tests
7. demo workflow

### Phase 4: Source adapters

1. Met CSV adapter
2. Cleveland CSV or JSON adapter
3. National Gallery of Art adapter
4. sample scripts that download a bounded subset or accept a local file
5. provenance and attribution documentation

Never download an entire large dataset automatically. Provide `--limit` and explicit paths.

### Phase 5: Local viewer

Build a polished local findings viewer only after the engine and reports are stable.

### Phase 6: Optional ArtiFact and multimodal experiment

Add an opt-in benchmark adapter and one carefully scoped probabilistic rule. Keep it experimental and disabled by default.

### Phase 7: Public showcase (GitHub Pages)

Only begin this phase after the Definition of Done (Section 25) passes, and only push or enable Pages after my explicit approval.

1. Build a static documentation site (recommend MkDocs Material) with a standard `gh-pages` GitHub Actions deploy workflow. No paid infrastructure and no secrets, consistent with Section 20.
2. Structure the site as a dual story:
   - A product-led home page: value proposition, problem statement, demo screenshots or terminal recording of the HTML report, the Mermaid architecture diagram, benchmark summary, and honest limitations, sourced from the README, PRD, and BENCHMARK docs.
   - A "How this was built" page: a loop-engineering case study connecting the working method in Section 26 and Section 26A to concrete evidence in the repository (the PROGRESS.md loop log, ADRs, CI runs, benchmark results).
   - An "About the builder" page: positions the author as a technical product manager, referencing PRD authorship, scope discipline (the non-goals in Section 6), success metrics (Section 22), and threat-model and evidence-first thinking (Section 18).
3. Add a link or badge to the Pages site in the README, with a one-line note that the project was built with Claude Code using a documented loop-engineering working method.
4. Verify `mkdocs build` succeeds locally before asking for approval to publish.

## 25. Definition of done for the first release

The first release is done only when all of the following are true:

- `uv sync` succeeds from a clean checkout
- `uv run ruff check .` succeeds
- formatting check succeeds
- type checking succeeds
- tests succeed
- package builds
- clean example scan completes with expected results
- dirty example scan produces the expected labeled findings
- benchmark command produces metrics
- HTML report opens without external assets
- SARIF validates
- GitHub workflows do not require secrets
- README quick start has been executed exactly as written
- no paid model is required
- no source data is modified
- limitations and non-goals are documented
- `docs/PROGRESS.md` accurately states what works and what remains
- a five-minute demo script is reproducible
- optionally, once the above are true: the showcase site builds locally (`mkdocs build`) and the Pages deploy workflow is ready, pending my approval to publish

## 26. Working method

Use a loop:

1. inspect current state
2. select the smallest vertical slice
3. implement
4. run focused tests
5. run broader checks
6. inspect outputs
7. update documentation and progress
8. commit locally with a clear message after the slice passes
9. repeat

Keep changes small and reviewable.

Before every claim of completion, include the commands actually run and their outcomes in `docs/PROGRESS.md`.

When a test fails, diagnose it rather than weakening the assertion.

Do not delete tests to make the build pass.

Avoid placeholders in production paths. TODOs are acceptable only when recorded in `docs/BACKLOG.md` with rationale and priority.

Prefer clear code over clever abstractions.

## 26A. Build narrative and loop-engineering evidence

This project doubles as a public showcase (Phase 7) of a documented loop-engineering working method. From Phase 0 onward, capture the evidence for that showcase as a byproduct of normal work — do not fabricate or backfill it later.

1. Save the Kickoff Prompt from this brief into `docs/prompts/` for provenance.
2. Extend `docs/PROGRESS.md` so each entry records one full loop iteration from Section 26: the slice chosen, the commands run, the verification evidence (test output, inspected results), and the resulting decision or commit. This is the raw material for the "How this was built" showcase page.
3. Create `docs/LOOP_ENGINEERING.md` mapping this repository's concrete artifacts to loop-engineering primitives: automations (the GitHub Actions workflows in Section 20), skills, sub-agents, memory (`CLAUDE.md` and `docs/PROGRESS.md`), and any others actually used. Only claim a primitive that this repository actually demonstrates; do not describe unused capabilities for effect.

## 27. Initial actions to take now

Start immediately:

1. Print the current directory tree and git status.
2. Create a concise implementation plan in `docs/BUILD_PLAN.md`.
3. Create `CLAUDE.md` containing project purpose, commands, architecture boundaries, safety constraints, and the current phase.
4. Scaffold Phase 1.
5. Implement the smallest end-to-end slice:
   - read one objects CSV
   - map it to canonical records
   - detect duplicate accession numbers
   - emit console and JSON findings
   - test the full path
6. Run the tests and show the exact results.
7. Continue through Phase 1 without waiting for another prompt unless a defined escalation condition is reached.

At the end of the session, provide:

- what was implemented
- files changed
- commands run
- test and lint results
- current limitations
- next highest-value slice

---

# Primary resources

Claude Code:

- Official setup: https://docs.anthropic.com/en/docs/claude-code/getting-started
- CLI reference: https://docs.anthropic.com/en/docs/claude-code/cli-usage
- Project memory and `CLAUDE.md`: https://docs.anthropic.com/en/docs/claude-code/memory
- Model Context Protocol overview: https://docs.anthropic.com/en/docs/mcp

Problem evidence and open issues:

- MoMA collection repository issues: https://github.com/MuseumofModernArt/collection/issues
- Met Open Access issue about image availability inconsistency: https://github.com/metmuseum/openaccess/issues/52

Open museum data:

- Metropolitan Museum of Art Open Access: https://github.com/metmuseum/openaccess
- Cleveland Museum of Art Open Access: https://github.com/ClevelandMuseumArt/openaccess
- National Gallery of Art Open Data: https://github.com/NationalGalleryOfArt/opendata
- Art Institute of Chicago API: https://api.artic.edu/docs/
- Rijksmuseum data services: https://data.rijksmuseum.nl/docs/

Benchmark:

- ArtiFact paper: https://arxiv.org/abs/2606.09648
- ArtiFact dataset card: https://huggingface.co/datasets/deem-data/ArtiFact
- ArtiFact project repository referenced by the dataset card: https://github.com/OlgaOvcharenko/ArtiFact

Domain and adjacent tooling:

- CollectionSpace documentation: https://collectionspace.org/documentation/
- CollectionSpace staff interface and object-record overview: https://collectionspace.org/staff-interface/
- OpenRefine reconciliation documentation: https://openrefine.org/docs/manual/reconciling

Read licenses and usage conditions before downloading or redistributing data or images. Keep bounded sample-download scripts separate from test fixtures.
