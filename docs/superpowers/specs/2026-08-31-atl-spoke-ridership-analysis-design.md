# ATL Spoke Ridership Analysis — Design

**Date:** 2026-08-31
**Inputs:** `ABI Ridership Report June 2026.pdf`, `ABI Ridership Report July 2026.pdf`
**Outputs:** tidy CSVs in `data/`, executed `analysis.ipynb`, HTML artifact

## 1. Subject

ATL Spoke — Atlanta Beltline's autonomous shuttle pilot, operated by Beep.
Phase 1: ~2-mile loop, 4 stops, West End MARTA <-> Lee+White. Four electric
ADA shuttles (ABI-01..04), 12 passengers each, onboard attendant, zero fare.
Funded by a $1.75M Georgia Transportation Efficiency Authority grant over a
12-month pilot. Soft launch 2026-05-31; public launch 2026-06-05.

## 2. Extraction

The PDFs are chart-only: no tables. `pdftotext -layout` returns bar labels in
visual order (staggered by bar height), which would mis-assign values to dates.

Approach: `pdftotext -bbox-layout` emits XHTML with per-word bounding boxes.
Parse with stdlib `xml.etree`, then:

1. Read every `<word>` as (text, x_min, x_max, y_min, y_max).
2. Locate chart bands by anchor text: "Month-over-Month", "Weekly Ridership",
   "Daily Ridership".
3. Within a band classify words as axis ticks (`7/14`, `Wk 2`, `Jun 2026`) or
   values (`^[\d,]+$`). Y-axis gridline numbers sit left of the first tick and
   are dropped by an x-threshold.
4. Join each tick to the value by an order-preserving minimum-cost assignment.
   Tolerance is 0.9x the median tick spacing, not half: renderers nudge colliding
   labels, and June's `102` sits 9.31pt off its own tick, which 0.5x rejects.
   A tick with no label is recorded as MISSING (empty cell + label_present=False),
   never as a zero. 2026-07-26 is such a day.

### Validation gates (assert before writing any CSV)

| Gate | Expected |
|---|---|
| Daily sum == headline total | 1497 June, 1306 July |
| Weekly sum == headline total | June weeks 1525 - May 31's 28 = 1497 |
| Date coverage complete + contiguous | 30 days June, 31 days July |
| Each weekly bar == sum of its own days | narrows the blind spot to one week |
| Cross-report agreement | June's total as reported by each PDF separately |
| Soft-launch bar | May == 28 (one day of service, 2026-05-31) |

The cross-report gate is the only one using outside information: the two PDFs
were generated a month apart and must agree. `monthly_ridership.csv` keeps one
row per (month, reporting PDF) so the comparison is real; collapsing to one row
per month made the check tautological in an earlier version.

What the gates do NOT prove: that each value carries the right date. Sums are
invariant to a swap between two days in the same week. The per-week gate narrows
that window from a month to a week without closing it.

## 3. Data files

CSVs carry extracted facts only. Derived features (weekday, match-day flags,
metrics) are computed in the notebook so the data stays re-derivable.

- `daily_ridership.csv` — date, boardings, report_month, source_pdf
- `weekly_ridership.csv` — report_month, week_label, week_start, boardings, days_covered
- `monthly_ridership.csv` — month, boardings, source_report
- `report_metadata.csv` — report_month, generated_date, service, agency, routes, vehicles
- `peer_benchmarks.csv` — comparator systems and their published metrics

## 4. Assumption register (`src/service_parameters.py`)

Every external input lives here with value, source URL, and confidence. Nothing
derived from these appears in the notebook without tracing back to this file.

| Parameter | Value | Confidence |
|---|---|---|
| Route length (Phase 1) | ~2.0 mi | reported, both months identical |
| Regular service hours | 12:00-22:00 = 10 h/day, 7 days | high |
| Match-day service hours | 08:00-24:00 = 16 h/day | high |
| Atlanta match days | Jun 15,18,21,24,27; Jul 1,7,15 | high |
| Vehicles in service | 3 of 4 (34-min loop @ 12-15 min headway) | LOW — sensitivity 3 vs 4 |
| Grant allocation | $1.75M / 12 mo = $145,833/mo | LOW — includes capital; sensitivity |
| Avg trip length | 0.7 mi assumed | LOW — sensitivity 0.5-1.5 mi |

Route length did NOT change between June and July. The AUC (Phase 2) extension
launched mid-August 2026, after the data window. This is a null result that
rules out route change as a cause of the decline.

## 5. Analysis sections

1. Provenance and data quality — parse validation, the June report's "June 2025"
   chart-title bug, the May 31 straddle.
2. Operational baseline — totals, mean/median daily, peak, near-zero days.
3. Ramp-up from soft launch — cumulative curve, launch to steady state.
4. Day-of-week and weekend patterns.
5. World Cup event attribution — match-day vs non-match-day, in-tournament vs
   post-tournament. Tournament ran Jun 11 - Jul 19, 2026.
6. Transit metrics with sensitivity — cost per trip, cost per revenue hour,
   cost per passenger mile, boardings per revenue hour.
7. Peer benchmarking — MARTA bus, Atlanta Streetcar, AV shuttle pilots.

## 6. Known limits

- n = 2 months, 62 service days. Attribution, not causation. No counterfactual.
- All cost metrics inherit the grant-allocation assumption. Reported as ranges.
- The referenced "Full Ridership" stop-level PDFs are not available, so no
  stop-level or boarding/alighting analysis.
- RESOLVED (confirmed by operator): only `ABI Short` ran in Phase 1, so all
  June and July boardings are ABI Short. `ABI Long` is the AUC-extension pattern,
  present in the report header because it was configured in the reporting system
  ahead of its mid-August 2026 launch.
