"""Extract ridership data from ABI (ATL Spoke) chart-only PDF reports.

The reports contain no tables -- every number is a bar label positioned by the
chart renderer. `pdftotext -layout` returns those labels in visual order
(staggered by bar height), which silently mis-assigns values to dates. Instead
we use `pdftotext -bbox-layout`, which emits per-word bounding boxes, and
recover the value->tick association geometrically by nearest x-centre.
"""

from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

XHTML = "{http://www.w3.org/1999/xhtml}"

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}
MONTH_FULL = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11,
    "December": 12,
}

NUMERIC = re.compile(r"^[\d,]+$")
DATE_TICK = re.compile(r"^(\d{1,2})/(\d{1,2})$")


@dataclass(frozen=True)
class Word:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    page: int
    line: int

    @property
    def xc(self) -> float:
        return (self.x0 + self.x1) / 2


@dataclass(frozen=True)
class Tick:
    """An x-axis tick, possibly built from several words (e.g. 'Wk' + '4')."""

    label: str
    x0: float
    x1: float

    @property
    def xc(self) -> float:
        return (self.x0 + self.x1) / 2


def parse_words(pdf: Path) -> list[Word]:
    """Run pdftotext -bbox-layout and flatten to words tagged with page/line."""
    out = subprocess.run(
        ["pdftotext", "-bbox-layout", str(pdf), "-"],
        capture_output=True, text=True, check=True,
    ).stdout
    root = ET.fromstring(out)
    words: list[Word] = []
    line_id = 0
    for page_no, page in enumerate(root.iter(f"{XHTML}page")):
        for line in page.iter(f"{XHTML}line"):
            for w in line.iter(f"{XHTML}word"):
                words.append(Word(
                    text=(w.text or "").strip(),
                    x0=float(w.get("xMin")), y0=float(w.get("yMin")),
                    x1=float(w.get("xMax")), y1=float(w.get("yMax")),
                    page=page_no, line=line_id,
                ))
            line_id += 1
    return [w for w in words if w.text]


def numeric_value_words(words: list[Word]) -> list[Word]:
    """Numeric words that sit alone on their line.

    Chart titles ('Daily Ridership - July 2026') contain the numeric token
    '2026' but also non-numeric words, so rejecting mixed lines removes titles
    without hard-coding any y-coordinates.
    """
    by_line: dict[int, list[Word]] = {}
    for w in words:
        by_line.setdefault(w.line, []).append(w)
    return [
        w for line in by_line.values() if all(NUMERIC.match(x.text) for x in line)
        for w in line
    ]


def to_int(text: str) -> int:
    return int(text.replace(",", ""))


def match_values(ticks: list[Tick], values: list[Word]) -> dict[str, tuple[int | None, bool]]:
    """Assign each value label to a tick by an order-preserving minimum-cost match.

    Bar labels and axis ticks are both monotonic in x, so a label may only
    attach to a tick if every label to its left attached further left. Greedy
    nearest-neighbour ignores that and lets one early tick steal a neighbour's
    label, cascading errors down the axis. This dynamic program finds the
    globally cheapest monotone assignment instead.

    A tick with no label is returned as None, meaning NO OBSERVATION. It is not
    a measured zero. The renderer omits the marker and breaks the series line
    for a missing point, and a sum gate cannot tell a missing value from a real
    zero because both contribute nothing to the total. Callers must decide
    explicitly; nothing here guesses.
    """
    ticks = sorted(ticks, key=lambda t: t.xc)
    values = sorted(values, key=lambda v: v.xc)
    n, m = len(ticks), len(values)
    if m > n:
        raise ValueError(f"{m} value labels for only {n} ticks")

    xs = sorted(t.xc for t in ticks)
    spacing = sorted(b - a for a, b in zip(xs, xs[1:])) if n > 1 else [1e9]
    # Generous: renderers nudge colliding labels apart (June's '102' lands 9.3pt
    # off its own tick to clear its neighbour), so distance alone cannot decide.
    # The order-preserving constraint plus the caller's sum gates are what
    # actually verify the match.
    tol = spacing[len(spacing) // 2] * 0.9

    INF = float("inf")
    # dp[i][j]: best cost using the first i ticks to place the first j labels.
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, min(i, m) + 1):
            if dp[i - 1][j] < dp[i][j]:          # leave tick i-1 unlabelled
                dp[i][j], back[i][j] = dp[i - 1][j], "skip"
            d = abs(ticks[i - 1].xc - values[j - 1].xc)
            if d <= tol and dp[i - 1][j - 1] + d < dp[i][j]:
                dp[i][j], back[i][j] = dp[i - 1][j - 1] + d, "take"
    if dp[n][m] == INF:
        raise ValueError("no order-preserving assignment within tolerance")

    result: dict[str, tuple[int, bool]] = {}
    i, j = n, m
    while i > 0:
        if back[i][j] == "take":
            result[ticks[i - 1].label] = (to_int(values[j - 1].text), True)
            i, j = i - 1, j - 1
        else:
            result[ticks[i - 1].label] = (None, False)
            i -= 1
    return result


def chart_words(words: list[Word], page: int, tick_y: float,
                y_top: float, min_tick_x0: float) -> list[Word]:
    """Value labels for one chart: above its tick row, right of the y-axis."""
    return [
        w for w in numeric_value_words(words)
        if w.page == page and y_top < w.y0 < tick_y - 1 and w.x1 > min_tick_x0 - 2
    ]


def group_ticks(rows: list[list[Word]]) -> list[Tick]:
    """Merge stacked tick rows ('Wk 4' over 'Jun 28') into single ticks by x-overlap."""
    primary = sorted(rows[0], key=lambda w: w.x0)
    clusters: list[list[Word]] = []
    for w in primary:
        if clusters and w.x0 - clusters[-1][-1].x1 < 6:
            clusters[-1].append(w)
        else:
            clusters.append([w])
    ticks = []
    for cluster in clusters:
        x0 = min(w.x0 for w in cluster)
        x1 = max(w.x1 for w in cluster)
        parts = [" ".join(w.text for w in cluster)]
        for extra in rows[1:]:
            near = sorted(
                (w for w in extra if w.x1 > x0 - 12 and w.x0 < x1 + 12),
                key=lambda w: w.x0,
            )
            if near:
                parts.append(" ".join(w.text for w in near))
                x0 = min(x0, min(w.x0 for w in near))
                x1 = max(x1, max(w.x1 for w in near))
        ticks.append(Tick(" ".join(parts), x0, x1))
    return ticks


def rows_at(words: list[Word], page: int, y: float, tol: float = 1.0) -> list[Word]:
    return [w for w in words if w.page == page and abs(w.y0 - y) <= tol]


def lines_of(words: list[Word]) -> dict[int, list[Word]]:
    out: dict[int, list[Word]] = {}
    for w in words:
        out.setdefault(w.line, []).append(w)
    for v in out.values():
        v.sort(key=lambda w: w.x0)
    return out


def title_y_above(words: list[Word], page: int, tick_y: float) -> float:
    """y of the chart title (a line containing an em dash) nearest above the ticks."""
    cands = [
        max(w.y1 for w in line)
        for line in lines_of(words).values()
        if line[0].page == page
        and any(w.text == "—" for w in line)
        and max(w.y1 for w in line) < tick_y
    ]
    return max(cands) if cands else 0.0


def extract_daily(words: list[Word], year: int, month: int) -> list[dict]:
    ticks_raw = [w for w in words if DATE_TICK.match(w.text)]
    if not ticks_raw:
        raise ValueError("no daily date ticks found")
    page = ticks_raw[0].page
    tick_y = ticks_raw[0].y0
    ticks_raw = rows_at(words, page, tick_y)
    ticks_raw = [w for w in ticks_raw if DATE_TICK.match(w.text)]
    ticks = [Tick(w.text, w.x0, w.x1) for w in sorted(ticks_raw, key=lambda w: w.x0)]

    min_x0 = min(t.x0 for t in ticks)
    y_top = title_y_above(words, page, tick_y)
    values = chart_words(words, page, tick_y, y_top, min_x0)
    matched = match_values(ticks, values)

    rows = []
    for tick in ticks:
        m, d = (int(x) for x in DATE_TICK.match(tick.label).groups())
        # A leading week can reach back into the previous month (and, at a year
        # boundary, the previous year).
        y = year - 1 if m > month else year
        boardings, labelled = matched[tick.label]
        rows.append({
            "date": date(y, m, d),
            "boardings": boardings,
            "label_present": labelled,
        })
    return rows


def extract_weekly(words: list[Word]) -> list[dict]:
    wk = [w for w in words if w.text == "Wk"]
    if not wk:
        raise ValueError("no weekly ticks found")
    page, tick_y = wk[0].page, wk[0].y0
    row1 = rows_at(words, page, tick_y)
    below = sorted({w.y0 for w in words if w.page == page and w.y0 > tick_y + 1})
    row2 = rows_at(words, page, below[0]) if below else []
    ticks = group_ticks([row1, row2])

    min_x0 = min(t.x0 for t in ticks)
    y_top = title_y_above(words, page, tick_y)
    values = chart_words(words, page, tick_y, y_top, min_x0)
    matched = match_values(ticks, values)
    return [
        {"week_label": t.label, "boardings": matched[t.label][0],
         "label_present": matched[t.label][1]}
        for t in ticks
    ]


def extract_monthly(words: list[Word]) -> list[dict]:
    mons = [w for w in words if w.text in MONTHS]
    if not mons:
        raise ValueError("no month ticks found")
    page, tick_y = mons[0].page, mons[0].y0
    row1 = [w for w in rows_at(words, page, tick_y) if w.text in MONTHS]
    below = sorted({w.y0 for w in words if w.page == page and w.y0 > tick_y + 1})
    row2 = rows_at(words, page, below[0]) if below else []
    ticks = group_ticks([row1, row2])

    min_x0 = min(t.x0 for t in ticks)
    y_top = title_y_above(words, page, tick_y)
    values = chart_words(words, page, tick_y, y_top, min_x0)
    matched = match_values(ticks, values)

    rows = []
    for t in ticks:
        mon, yr = t.label.split()
        rows.append({
            "month": date(int(yr), MONTHS[mon], 1),
            "boardings": matched[t.label][0],
        })
    return rows


def extract_metadata(words: list[Word]) -> dict:
    lines = lines_of(words)
    meta: dict[str, object] = {}

    for line in lines.values():
        txt = " ".join(w.text for w in line)
        if m := re.match(r"^(\w+) (\d{4}) \(Month (\d+)\)$", txt):
            meta["report_month"] = date(int(m[2]), MONTH_FULL[m[1]], 1)
        elif m := re.match(r"^Generated: (\w+) (\d{1,2}), (\d{4})$", txt):
            meta["generated_date"] = date(int(m[3]), MONTH_FULL[m[1]], int(m[2]))

    # Field labels sit on one visual row but pdftotext emits each as its own
    # block, so group by y-coordinate rather than by line. Values land on the
    # next row down and are split using each label's x-position.
    by_row: dict[tuple[int, float], list[Word]] = {}
    for w in words:
        by_row.setdefault((w.page, round(w.y0, 1)), []).append(w)

    for (page, y), row in sorted(by_row.items()):
        labels = [w for w in row if w.text.endswith(":")]
        names = {w.text.rstrip(":").lower() for w in labels}
        if not names >= {"service", "agency", "routes", "vehicles"}:
            continue
        below = [k for k in by_row if k[0] == page and k[1] > y]
        if not below:
            continue
        value_row = sorted(by_row[min(below, key=lambda k: k[1])], key=lambda w: w.x0)
        bounds = sorted((w.text.rstrip(":").lower(), w.x0) for w in labels)
        bounds.sort(key=lambda b: b[1])
        for i, (name, x0) in enumerate(bounds):
            hi = bounds[i + 1][1] if i + 1 < len(bounds) else 1e9
            meta[name] = " ".join(w.text for w in value_row if x0 - 2 <= w.x0 < hi)
        break

    for line in lines.values():
        if " ".join(w.text for w in line).startswith("Total Ridership"):
            above = [
                l for l in lines.values()
                if l[0].page == line[0].page and l[0].y0 < line[0].y0
                and all(NUMERIC.match(w.text) for w in l)
            ]
            meta["total_ridership"] = to_int(max(above, key=lambda l: l[0].y0)[0].text)
            break

    return meta


WEEK_START = re.compile(r"(\w{3}) (\d{1,2})$")


def build_report(pdf: Path) -> dict:
    """Extract one PDF and assert every internal consistency gate."""
    words = parse_words(pdf)
    meta = extract_metadata(words)
    rm: date = meta["report_month"]
    total: int = meta["total_ridership"]

    daily = extract_daily(words, rm.year, rm.month)
    weekly = extract_weekly(words)
    monthly = extract_monthly(words)

    # Missing days count as zero here only because the source's own totals do
    # the same: the observed values sum to the printed headline exactly. That
    # makes the totals consistent; it does NOT make a missing day a zero.
    def tot(rows):
        return sum(r["boardings"] or 0 for r in rows)

    in_month = tot([r for r in daily
                    if (r["date"].year, r["date"].month) == (rm.year, rm.month)])
    all_days = tot(daily)
    week_sum = tot(weekly)

    # The displayed daily window starts at a week boundary, so it can reach back
    # into the previous month; only the in-month days should equal the headline.
    assert in_month == total, f"{pdf.name}: in-month {in_month} != headline {total}"
    assert week_sum == all_days, f"{pdf.name}: weekly {week_sum} != daily {all_days}"

    dates = sorted(r["date"] for r in daily)
    assert (dates[-1] - dates[0]).days + 1 == len(dates), f"{pdf.name}: gap in dates"
    assert dates[-1].month == rm.month, f"{pdf.name}: window does not end in report month"

    mom = {r["month"]: r["boardings"] for r in monthly}
    assert mom[rm] == total, f"{pdf.name}: month-over-month bar != headline"

    # Attach the week-start date parsed from the second tick row.
    for row in weekly:
        m = WEEK_START.search(row["week_label"])
        mon, day = MONTHS[m[1]], int(m[2])
        row["week_start"] = date(rm.year - 1 if mon > rm.month else rm.year, mon, day)
    for row in weekly:
        row["days_covered"] = sum(
            1 for d in daily
            if row["week_start"] <= d["date"] < row["week_start"] + timedelta(days=7)
        )

    # Per-week gate. The month-level sums are invariant to any mis-assignment
    # inside a single week, so they cannot catch one. Checking each week against
    # its own days narrows that blind spot to swaps within one week.
    for row in weekly:
        end = row["week_start"] + timedelta(days=7)
        days = [d for d in daily if row["week_start"] <= d["date"] < end]
        got = sum(d["boardings"] or 0 for d in days)
        assert got == row["boardings"], (
            f"{pdf.name}: week of {row['week_start']} sums to {got}, "
            f"but its weekly bar reads {row['boardings']}")

    return {"meta": meta, "daily": daily, "weekly": weekly, "monthly": monthly,
            "source": pdf.name}


def main() -> None:
    import csv

    root = Path(__file__).resolve().parent.parent
    out = root / "data"
    out.mkdir(exist_ok=True)
    reports = [build_report(p) for p in sorted(root.glob("*.pdf"))]

    # Cross-report gate: the two PDFs were generated a month apart and their
    # month-over-month bars must agree with each other's headline totals.
    seen: dict[date, tuple[int, str]] = {}
    for rep in reports:
        for row in rep["monthly"]:
            prev = seen.get(row["month"])
            assert prev is None or prev[0] == row["boardings"], (
                f"cross-report disagreement for {row['month']}: "
                f"{prev[1]} says {prev[0]}, {rep['source']} says {row['boardings']}"
            )
            seen[row["month"]] = (row["boardings"], rep["source"])

    with (out / "daily_ridership.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "boardings", "label_present", "report_month", "source_pdf"])
        for rep in reports:
            for r in rep["daily"]:
                w.writerow([r["date"],
                            "" if r["boardings"] is None else r["boardings"],
                            r["label_present"], rep["meta"]["report_month"],
                            rep["source"]])

    with (out / "weekly_ridership.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["report_month", "week_label", "week_start", "days_covered",
                    "boardings", "source_pdf"])
        for rep in reports:
            for r in rep["weekly"]:
                w.writerow([rep["meta"]["report_month"], r["week_label"],
                            r["week_start"], r["days_covered"], r["boardings"],
                            rep["source"]])

    # One row per (month, reporting PDF). Collapsing to one row per month would
    # destroy the provenance a genuine cross-report check needs.
    with (out / "monthly_ridership.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["month", "boardings", "reported_by"])
        rows = sorted(((r["month"], r["boardings"], rep["source"])
                       for rep in reports for r in rep["monthly"]),
                      key=lambda t: (t[0], t[2]))
        for month, boardings, source in rows:
            w.writerow([month, boardings, source])

    with (out / "report_metadata.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["report_month", "generated_date", "service", "agency", "routes",
                    "vehicles", "total_ridership", "source_pdf"])
        for rep in reports:
            m = rep["meta"]
            w.writerow([m["report_month"], m["generated_date"], m["service"],
                        m["agency"], m["routes"], m["vehicles"],
                        m["total_ridership"], rep["source"]])

    print(f"{len(reports)} reports -> {out}/  (all validation gates passed)")


if __name__ == "__main__":
    main()
