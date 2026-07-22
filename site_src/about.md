# About the builder

Collection Integrity CI was designed and built by Akash Majumder. It's meant to show technical
product management in practice: not just shipping a working tool, but shipping it with the
discipline, evidence, and scope control the job actually calls for. The artifacts in the repository
are the argument, so here's what they show.

## The problem was framed before the code

The work started with a product requirements document (`docs/PRD.md`) and a full build specification
(`BUILD_BRIEF.md`), written before any engine code. The problem, museum data that quietly disagrees
with itself ahead of a migration or a publication, was framed around a real user (a registrar or
collections data manager) and a real moment when it bites, not around a technology looking for a
use.

## Scope was a decision, not an afterthought

A product is defined as much by what it refuses to do. This one has an explicit list of non-goals,
and they're enforced, not just stated:

- It is not a collection management system.
- It is not a rights or legal authority. Rights findings are consistency warnings, never legal
  advice.
- It never edits source data. Reading is read-only.
- It needs no paid AI service to do its job. The core product runs offline.

Those lines show up as architecture rules, as safety constraints in `CLAUDE.md`, and as tests that
fail if a boundary gets crossed.

## Success is measured

The specification set out success metrics up front, and the build makes them observable. Rule
quality is benchmarked against a labeled synthetic dataset and the number is regenerated on every CI
run. Documentation honesty is a release gate: every README command is run word for word before the
docs are trusted. "Done" is an executable checklist (`scripts/check_dod.sh`) run from a clean
checkout.

## Security was treated as a product concern

A threat model (`docs/THREAT_MODEL.md`) lists fifteen risks, from spreadsheet formula injection to
path traversal to decompression bombs, and ties each to either a test or a written rationale. Two
real vulnerabilities were found and fixed while those tests were being written.

Underneath all of it is one habit: no claim without a command run and its output read, and no test
weakened to make a build pass. The [build case study](how-built.md) has the receipts.

## The short version

Frame a real problem. Decide the scope on purpose. Make success measurable. Build in small,
reviewable, evidence-backed steps, and leave a trail someone else can audit. That's the product
story this project is meant to tell.

---

!!! info "Colophon"
    Built with [Claude Code](https://claude.com/claude-code) using a documented working method. The
    full build log is in `docs/PROGRESS.md`.
