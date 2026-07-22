# Validated on real museum data

Does this catch real problems, or only the synthetic ones it was built to find? To answer that,
the scanner was pointed at real, public open-access data from two major museums. The exercise was
thorough enough that it found two bugs in the tool before it produced a single finding worth
trusting.

!!! note "Sources (real, public, CC0 metadata)"
    - The Metropolitan Museum of Art Open Access, `MetObjects.csv`
    - The Cleveland Museum of Art Open Access, `data.csv`

    Bounded samples of roughly 44,000 Met and 20,000 Cleveland objects, streamed and capped by the
    built-in `fetch_sample.py`. The tool never downloads a whole dataset.

## Real data found real bugs in the tool first

Running against real exports immediately exposed two problems that synthetic fixtures would never
have shown. Both are fixed now, with regression tests.

The first was a byte-order mark. The Met and Cleveland CSVs, like most files Excel produces, start
with a UTF-8 BOM. That mark was attaching itself to the first column name and breaking the
accession-number mapping, which made the scanner report every single object as missing its accession
number. Decoding with `utf-8-sig` fixed it.

The second was the date parser. It only accepted four-digit years, so legitimate early dates like
year 185 or year 50, which encyclopedic collections record all the time, were being flagged as
invalid. It now accepts any year from 1 to 9999 CE.

That's the whole reason to test against real data. It surfaces what a clean synthetic suite can't.

## What it actually caught

After the fixes, the scanner flagged 10 Cleveland objects (and one Met object) whose production end
year comes before the start year. These are all checkable against the museums' own published data:

| Cleveland accession | Title | earliest | latest |
|---------------------|-------|:--------:|:------:|
| 1917.425 | Storage Basket | 1985 | 1905 |
| 1924.650 | Peasant Leaning on His Doorway | 1648 | 1558 |
| 1926.479 | Cornelis Claesz Anslo, Mennonite Preacher | 1641 | 1631 |
| 1929.894 | The Watering Hole (Horses Bathing) | 1906 | 1903 |
| 1932.417 | Morning Glories | 1921 | 1911 |
| 1922.523 | The Horrors of War: What Courage! | 1810 | 186 (truncated) |
| 1915.403 | Buckle (Tang dynasty) | 918 | 907 |
| 1917.601 | Figures from the Four Continents | 1755 | 1665 |

Each one is a genuine inconsistency: an end year earlier than the start, or a year that's clearly
been truncated (186, 14). You'd never spot these scrolling a spreadsheet of 20,000 rows, but the
scanner finds them in seconds and shows the object, the values, and a fix. These exact rows are
committed as a test fixture, so the claim is checked on every CI run and anyone can reproduce it.

## What it correctly left alone

Most of the remaining raw findings are BCE and year-0 dates, like a Roman coin dated 50 BCE. The
tool's calendar model can't represent pre-year-1 dates yet, so it leaves them unset and flags them.
Those aren't data errors, they're a known limitation, and they're deliberately kept out of the count
above. Being clear about that difference is what separates an honest tool from a scary number.

## What this adds up to

It works on real, name-brand museum data, offline, in seconds, with no setup. It caught 10 real
inverted-date errors in Cleveland's data and one in the Met's, the kind a registrar wants fixed
before publishing. It also found the identity data clean, with no duplicate or missing accession
numbers.

One caveat worth repeating: the raw finding counts are dominated by BCE dates, which are a known
limitation and not errors. Lead with the real inverted-date errors, not the big number.

---

To reproduce: fetch a bounded Cleveland sample with `scripts/fetch_sample.py`, run
`collection-ci scan --source cleveland --input <sample> --output-dir build/cleveland`, and open
`build/cleveland/report.html`. The exact commands and licensing are in
[`docs/DATA_SOURCES.md`](https://github.com/akivanc88/collection-integrity-ci/blob/main/docs/DATA_SOURCES.md).
