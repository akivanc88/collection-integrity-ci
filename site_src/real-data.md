# Validated on real museum data

Does this catch real problems, or just synthetic ones it was built to find? To answer that honestly,
the scanner was run against **real, public open-access data** from two major museums — and the
exercise was rigorous enough to find (and fix) two bugs in the tool itself before it produced a
single trustworthy finding.

!!! note "Sources (real, public, CC0 metadata)"
    - The Metropolitan Museum of Art Open Access — `MetObjects.csv`
    - The Cleveland Museum of Art Open Access — `data.csv`

    Bounded samples of ~44,000 Met and 20,000 Cleveland objects, streamed and capped by the built-in
    `fetch_sample.py` (the tool never downloads a whole dataset).

## Real data found real bugs in the tool first

Pointing the scanner at real exports immediately exposed two robustness gaps that synthetic fixtures
never would. Both are now fixed, with regression tests:

1. **UTF-8 byte-order marks.** The Met and Cleveland CSVs — like most Excel exports — begin with a
   BOM, which bound to the first column name and broke the accession-number mapping, falsely flagging
   *every* object as missing its accession number. Fixed by decoding with `utf-8-sig`.
2. **Short CE years.** The date parser accepted only 4-digit years, wrongly flagging the ancient and
   early-CE dates (year 185, 50, …) that encyclopedic collections routinely record. Fixed to accept
   any year 1–9999 CE.

*This is the entire point of validating against real data: it surfaces what a clean synthetic test
suite cannot.*

## The genuine findings

### Real catalog errors: production end-date before start-date

After the fixes, the scanner flagged **10 Cleveland objects** (and one Met object) whose production
*end* year precedes the *start* year — verifiable in the museums' own published data:

| Cleveland accession | Title | earliest | latest |
|---------------------|-------|:--------:|:------:|
| 1917.425 | Storage Basket | 1985 | **1905** |
| 1924.650 | Peasant Leaning on His Doorway | 1648 | **1558** |
| 1926.479 | Cornelis Claesz Anslo, Mennonite Preacher | 1641 | **1631** |
| 1929.894 | The Watering Hole (Horses Bathing) | 1906 | **1903** |
| 1932.417 | Morning Glories | 1921 | **1911** |
| 1922.523 | The Horrors of War: What Courage! | 1810 | **186** (truncated) |
| 1915.403 | Buckle (Tang dynasty) | 918 | **907** |
| 1917.601 | Figures from the Four Continents | 1755 | **1665** |

Each is a real internal inconsistency — an end year before the start, or a clearly truncated year
(`186`). Invisible in a spreadsheet of 20,000 rows; caught in seconds here, with the exact object,
values, and a remediation. These exact rows are committed as a test fixture, so this claim is
verified on every CI run and reproducible by anyone.

### Correctly *not* flagged as errors — a documented limitation

The bulk of the remaining raw findings are **BCE and year-0 dates** (e.g. a Roman coin dated 50 BCE).
The tool's calendar model can't yet represent pre-year-1 dates, so it leaves them unset and flags
them. **These are not data errors** — they are a known, documented limitation, and are deliberately
kept out of the "real errors" count above. Being explicit about this is the difference between an
honest tool and a scary number.

## The honest bottom line

- ✅ Works on real, name-brand museum data — offline, no setup, in seconds.
- ✅ Caught **11 genuine, verifiable catalog errors** across the Met and Cleveland.
- ✅ Found the identity data clean — zero duplicate or missing accession numbers.
- ⚠️ The raw finding counts are dominated by BCE dates (a known limitation), which are excluded from
  the real-error count on purpose.

That combination — real proof, plus honesty about what *isn't* a finding — is the point.

---

*Reproduce it:* fetch a bounded Cleveland sample with `scripts/fetch_sample.py`, then
`collection-ci scan --source cleveland --input <sample> --output-dir build/cleveland` and open
`build/cleveland/report.html`. See
[`docs/DATA_SOURCES.md`](https://github.com/akivanc88/collection-integrity-ci/blob/main/docs/DATA_SOURCES.md)
in the repository for the exact commands and licensing.
