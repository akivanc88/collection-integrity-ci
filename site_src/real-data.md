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

## What it caught, and what happened next

After the fixes, the scanner flagged 10 Cleveland objects (and one Met object) whose production end
year came before the start year. Some were transposed or mistyped, and a couple had a year that had
clearly lost a digit (186, 188).

These were reported to the Cleveland Museum of Art on their open-data issue tracker
([issue #14](https://github.com/ClevelandMuseumArt/openaccess/issues/14)). The museum confirmed all
ten as real errors, corrected them, and their collection data analyst found and fixed a few more. A
new data file was pushed the same week.

!!! quote "The Cleveland Museum of Art responded the next day"
    "Nice catch! These are indeed erroneous records and have been corrected and an update pushed.
    Our collection data analyst found a few more and she's fixing them and we'll do another push.
    Thanks for alerting us to this and thanks for using our collection!"

    Cleveland Museum of Art, on
    [open-data issue #14](https://github.com/ClevelandMuseumArt/openaccess/issues/14)

All ten corrections are now live in Cleveland's API, and the table below shows the flagged value
next to what it was corrected to:

| Cleveland accession | Title | flagged (earliest / latest) | corrected to |
|---------------------|-------|:---------------------------:|:------------:|
| 1917.425 | Storage Basket | 1985 / 1905 | 1885 / 1905 |
| 1924.650 | Peasant Leaning on His Doorway | 1648 / 1558 | 1648 / 1658 |
| 1926.479 | Cornelis Claesz Anslo, Mennonite Preacher | 1641 / 1631 | 1641 / 1641 |
| 1929.894 | The Watering Hole (Horses Bathing) | 1906 / 1903 | 1906 / 1913 |
| 1932.417 | Morning Glories | 1921 / 1911 | 1911 / 1921 |
| 1922.523 | The Horrors of War: What Courage! | 1810 / 186 | 1810 / 1863 |
| 1915.403 | Buckle (Tang dynasty) | 918 / 907 | 618 / 907 |
| 1917.601 | Figures from the Four Continents | 1755 / 1665 | 1755 / 1765 |

You'd never spot these scrolling a spreadsheet of 20,000 rows, but the scanner found them in seconds
and showed the object, the values, and a suggested fix. The exact rows as originally flagged are
committed as a dated test fixture, so the finding is reproducible on every CI run even now that
Cleveland's live data is corrected.

## What it correctly left alone

Most of the remaining raw findings are BCE and year-0 dates, like a Roman coin dated 50 BCE. The
tool's calendar model can't represent pre-year-1 dates yet, so it leaves them unset and flags them.
Those aren't data errors, they're a known limitation, and they're deliberately kept out of the count
above. Being clear about that difference is what separates an honest tool from a scary number.

## What this adds up to

It works on real, name-brand museum data, offline, in seconds, with no setup. It caught 10 real
inverted-date errors in Cleveland's data and one in the Met's, the museum confirmed every one, and
they were corrected in the published dataset. It also found the identity data clean, with no
duplicate or missing accession numbers.

One caveat worth repeating: the raw finding counts are dominated by BCE dates, which are a known
limitation and not errors. Lead with the real inverted-date errors, not the big number.

---

To reproduce: fetch a bounded Cleveland sample with `scripts/fetch_sample.py`, run
`collection-ci scan --source cleveland --input <sample> --output-dir build/cleveland`, and open
`build/cleveland/report.html`. The exact commands and licensing are in
[`docs/DATA_SOURCES.md`](https://github.com/akivanc88/collection-integrity-ci/blob/main/docs/DATA_SOURCES.md).
