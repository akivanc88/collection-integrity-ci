# About the builder

Collection Integrity CI was designed and built by **Akash Majumder** as a demonstration of
**technical product management** — not just shipping a working tool, but doing it with the
discipline, evidence, and scope control that product leadership requires.

The artifacts in this repository are the argument. Here is what they show.

## Product thinking, written down first

The project began with a **Product Requirements Document** (`docs/PRD.md`) and a full build
specification (`BUILD_BRIEF.md`) before a line of engine code was written. The problem — collection
data that silently disagrees with itself ahead of a migration or publication — was framed around a
real user (a registrar or collections data manager) and a concrete moment of need, not around a
technology looking for a use.

## Scope discipline

A product is defined as much by what it refuses to do. This one has an explicit **non-goals**
section, and it is enforced throughout:

- It is **not** a collection management system.
- It is **not** a rights or legal authority — rights findings are consistency warnings, never legal
  advice.
- It **never edits source data** — ingestion is strictly read-only.
- It requires **no paid AI service** in the core path; the product works fully offline.

Those boundaries are not aspirational footnotes. They show up as architecture rules, as safety
constraints in `CLAUDE.md`, and as tests that fail if the boundary is crossed.

## Success measured, not claimed

The specification defines success metrics up front, and the build makes them observable:

- Rule quality is **benchmarked** (precision/recall/F1 against a labeled synthetic dataset), not
  assumed — and the number is regenerated on every CI run.
- Documentation honesty is a **release gate**: every command in the README is executed verbatim
  before the docs are trusted.
- "Done" is an **executable checklist** (`scripts/check_dod.sh`), run from a clean checkout.

## Threat-model and evidence-first instincts

Security was treated as a first-class product concern, not a late add-on. A
[threat model](how-built.md) enumerates fifteen risk items — from spreadsheet formula injection to
path traversal to decompression bombs — and maps each to either an adversarial test or a documented
rationale. Two real vulnerabilities were found and fixed *by building those tests*.

Above all, the working method is **evidence-first**: no claim without a command run and its output
inspected; no test weakened to make a build pass. The [loop-engineering case study](how-built.md)
shows the receipts.

## The through-line

Frame a real problem → constrain scope deliberately → define success measurably → build in small,
reviewable, evidence-backed increments → and let the process leave a trail anyone can audit. That is
the product-management story this project is meant to tell.

---

!!! info "Colophon"
    This project was built with [Claude Code](https://claude.com/claude-code) using a documented
    loop-engineering working method. The complete build log lives in `docs/PROGRESS.md`.
