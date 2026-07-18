# Kickoff Prompt

Saved for provenance, per `BUILD_BRIEF.md` Section 26A. This is the exact prompt used to start
implementation, copied from `BUILD_BRIEF.md`.

Date first used: 2026-07-18

---

Read BUILD_BRIEF.md in full before making changes.

Treat it as the authoritative product, architecture, scope, safety, testing, and delivery
specification for this repository.

Begin with the Phase 0 and Phase 1 instructions in the brief. Do not stop after producing a plan.
Continue immediately into the smallest tested end-to-end implementation.

Follow these operating rules:

- Work autonomously on reversible implementation choices.
- Ask me only when a decision requires credentials, paid infrastructure, an external account, a
  download larger than 1 GB, a remote push, or a material scope change.
- Do not push code or deploy anything without my explicit approval. Publishing the repository and
  the GitHub Pages showcase is a planned end-of-build step (Phase 7) that requires my sign-off.
- Do not use paid AI services in the core execution path.
- Do not modify source collection data.
- Do not start the web interface until the CLI, deterministic rule engine, reports, benchmark,
  and tests work.
- Run tests and inspect outputs before claiming that anything works.
- Maintain docs/PROGRESS.md with commands run, results, limitations, and the next implementation
  slice.
- Make small local commits only after the relevant checks pass.
- Never weaken or delete tests merely to make the build pass.

Start now by:

- inspecting the repository and Git status
- creating CLAUDE.md
- creating the planning and product documents required by the brief
- scaffolding the Python project
- implementing the first vertical slice from CSV ingestion through duplicate-accession detection
  to console and JSON output
- adding tests
- running those tests
- continuing through Phase 1

At the end of this working session, report exactly:

- what was implemented
- files created or changed
- commands run
- test, lint, and type-check results
- known limitations
- the next highest-value implementation slice
