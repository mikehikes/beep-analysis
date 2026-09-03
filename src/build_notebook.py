"""Generate analysis.ipynb from source cells."""
import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s.strip()))
co = lambda s: C.append(nbf.v4.new_code_cell(s.strip()))

md(r"""
# ATL Spoke ridership, June and July 2026

**The service.** ATL Spoke is the Atlanta Beltline's autonomous shuttle pilot, run by **Beep**.
Four electric ADA-accessible shuttles work a 2-mile, four-stop loop from West End MARTA to the
Beltline Southwest Trail at Lee+White. No fare. A **\$3M** total pilot budget, of which
**\$1.75M** is a Georgia Transportation Efficiency Authority grant, pays for a 12-month pilot.

**The data.** Two chart-only PDF ridership reports, June and July 2026. Neither contains a table.
Every number here was recovered from bar-label coordinates and checked against four gates. See
section 1.

Only **ABI Short** ran in Phase 1, confirmed by the operator, so every boarding below is ABI
Short. ABI Long is the AUC extension pattern. It appears in the report header because the
reporting system had it configured before the mid-August launch.

**The headline.** Ridership fell from **1,497** in June to **1,306** in July, down **12.8%**.
Most of that drop is the FIFA World Cup ending rather than the service getting worse.
""")

co(r"""
import warnings
from datetime import date, timedelta
from pathlib import Path
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import HTML, display

# MathJax typesets rendered output, so any table cell holding two dollar amounts
# would be read as inline maths. This class tells the typesetter to skip it.
NO_MATH = "mathjax_ignore tex2jax_ignore"

sys.path.insert(0, str(Path.cwd() / "src"))
import service_parameters as sp

warnings.filterwarnings("ignore")
pd.set_option("display.width", 120)

# Validated categorical palette (dataviz reference instance).
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
YELLOW, MAGENTA, RED = "#eda100", "#e87ba4", "#e34948"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8983"
SURFACE, GRID = "#fcfcfb", "#e7e6e2"

mpl.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "figure.dpi": 130,
    "font.size": 9, "text.color": INK,
    "axes.labelcolor": INK2, "axes.edgecolor": GRID, "axes.linewidth": 0.8,
    "axes.grid": True, "axes.axisbelow": True,
    "grid.color": GRID, "grid.linewidth": 0.7,
    "xtick.color": INK2, "ytick.color": INK2,
    "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False, "legend.fontsize": 8,
})

def tidy(ax, title=None, sub=None, ylab=None):
    if title:
        ax.set_title(title, loc="left", fontsize=11, color=INK, pad=14 if sub else 8)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=8, color=MUTED)
    ax.set_ylabel(ylab or "", fontsize=8)
    ax.grid(axis="x", visible=False)
    return ax

DATA = Path("data")
daily = pd.read_csv(DATA / "daily_ridership.csv", parse_dates=["date", "report_month"])
# Nullable integer, so 2026-07-26 stays missing rather than becoming a zero.
# Every mean below skips it; every sum treats it as contributing nothing, which
# is what the source's own totals do.
daily["boardings"] = daily.boardings.astype("Int64")
weekly = pd.read_csv(DATA / "weekly_ridership.csv", parse_dates=["report_month", "week_start"])
monthly = pd.read_csv(DATA / "monthly_ridership.csv", parse_dates=["month"])
meta = pd.read_csv(DATA / "report_metadata.csv", parse_dates=["report_month", "generated_date"])
peers = pd.read_csv(DATA / "peer_benchmarks.csv")

n_missing = int(daily.boardings.isna().sum())
print(f"{len(daily)} calendar days | {daily.date.min():%Y-%m-%d} to {daily.date.max():%Y-%m-%d}")
print(f"{len(daily) - n_missing} days with a recorded value, {n_missing} without")
""")

md(r"""
## 1. Where the numbers came from

The PDFs contain **no tables**. Every value is a bar label placed by the chart renderer. The
parser works out which value belongs to which date from x-coordinates and an order-preserving
assignment, not from reading order.

Checks run below, and all pass. Be clear about what they do and do not prove.

They verify **totals**. Each month's daily values sum to its printed headline, each weekly bar
equals the sum of its own days, and the two PDFs agree where they overlap. The cross-report
check is the only one bringing in outside information, since the two PDFs were generated a
month apart and July's month-over-month chart restates June's total.

They do **not** verify that each value carries the right date. A swap between two days inside
the same week leaves every sum unchanged. The per-week gate narrows that blind spot from a
month to a week without closing it.
""")

co(r"""
checks = []

for _, m in meta.iterrows():
    rm = m.report_month
    in_month = daily.loc[
        (daily.date.dt.year == rm.year) & (daily.date.dt.month == rm.month), "boardings"
    ].sum()
    checks.append((f"{rm:%B %Y} daily sum == headline total", in_month, m.total_ridership))

    wk = weekly.loc[weekly.report_month == rm, "boardings"].sum()
    dl = daily.loc[daily.report_month == rm, "boardings"].sum()
    checks.append((f"{rm:%B %Y} weekly sum == daily window sum", wk, dl))

    # Each weekly bar against the sum of its own days. Month-level sums are
    # invariant to a mis-assignment inside one week and cannot catch it.
    for _, row in weekly.loc[weekly.report_month == rm].iterrows():
        end = row.week_start + pd.Timedelta(days=7)
        got = daily.loc[(daily.report_month == rm)
                        & (daily.date >= row.week_start) & (daily.date < end),
                        "boardings"].sum()
        checks.append((f"{rm:%b %Y} {row.week_label} bar == sum of its days",
                       int(got), int(row.boardings)))

# Genuine cross-report check. The June total is reported by both PDFs, and
# monthly_ridership.csv keeps both rows so the two can actually be compared.
jun_rows = monthly.loc[monthly.month == "2026-06-01"]
assert len(jun_rows) == 2, "June should be reported by both PDFs"
by_june = jun_rows.loc[jun_rows.reported_by.str.contains("June"), "boardings"].iat[0]
by_july = jun_rows.loc[jun_rows.reported_by.str.contains("July"), "boardings"].iat[0]
checks.append(("Cross-report: June total as reported by each PDF", by_june, by_july))

# The May bar should be a single day of soft-launch service (2026-05-31).
may_bar = monthly.loc[monthly.month == "2026-05-01", "boardings"].iat[0]
may_daily = int(daily.loc[daily.date == "2026-05-31", "boardings"].iat[0])
checks.append(("May bar == the single 2026-05-31 soft-launch day", may_bar, may_daily))

qa = pd.DataFrame(checks, columns=["check", "value_a", "value_b"])
qa["result"] = ["PASS" if a == b else "FAIL" for a, b in zip(qa.value_a, qa.value_b)]
display(qa)
assert (qa.result == "PASS").all(), "a validation gate failed"
print(f"\n{len(qa)} checks, all pass. They verify totals, not per-day date assignment.")
""")

md(r"""
### Known problems in the source

1. **A labelling bug.** The June PDF titles its weekly and daily charts *"June 2025"* while its
   header reads *June 2026*. The July report is correct. This is a bug in the report generator,
   not in the data. The parser takes the month from the report header, so no values are affected.
2. **One day has no observation.** July has 31 ticks but only 30 rendered points, and the gap is
   **2026-07-26**. Tracing the PDF's vector content shows 30 markers, and the series line is
   drawn as two separate strokes broken at that date. A renderer omits the marker and breaks the
   line for a missing point, not for a zero, and 2026-07-27's value of 1 plots well inside the
   axis, so a zero would have been drawn.

   It is recorded as **missing**, not zero. The observed values still sum to 1,306, but that
   proves nothing either way, because a missing value and a real zero both contribute nothing to
   a total. Every mean here skips the day. Whether the service ran at all on 2026-07-26 is
   unknown, so the service-hour figures still count it as a normal day.
3. **The daily window is not the calendar month.** June's chart starts at **May 31** because the
   window opens on a week boundary. June's displayed days sum to 1,525 and its in-month days sum
   to 1,497. Both are right. The difference is the 28 soft-launch boardings.
4. **No stop-level data.** Both PDFs point to a "Full Ridership" PDF that was not provided, so
   boardings by stop and alightings are out of scope.
5. **Route attribution is settled.** Only `ABI Short` ran in Phase 1, so no boardings need
   splitting between route patterns.
""")

co(r"""
zero_or_missing = daily.loc[~daily.label_present, ["date", "boardings"]]
print("Ticks with no rendered label (read as zero):")
display(zero_or_missing)

jun_window = daily.loc[daily.report_month == "2026-06-01", "boardings"].sum()
jun_in_month = daily.loc[
    (daily.date >= "2026-06-01") & (daily.date <= "2026-06-30"), "boardings"].sum()
print(f"June displayed window (May 31 - Jun 30): {jun_window:,}")
print(f"June in-month only     (Jun 1  - Jun 30): {jun_in_month:,}")
print(f"Difference                              : {jun_window - jun_in_month:,}  "
      f"(the May 31 soft launch)")
""")

md(r"""
## 2. Baseline

62 straight service days, 2026-05-31 through 2026-07-31.
""")

co(r"""
daily = daily.sort_values("date").reset_index(drop=True)
daily["weekday"] = daily.date.dt.day_name()
daily["dow"] = daily.date.dt.dayofweek
daily["is_weekend"] = daily.dow >= 5
daily["month"] = daily.date.dt.to_period("M").dt.to_timestamp()

md_set = set(pd.to_datetime(sp.ATLANTA_MATCH_DAYS))
daily["is_match_day"] = daily.date.isin(md_set)
daily["period"] = pd.cut(
    daily.date,
    bins=[pd.Timestamp("2026-05-30"), pd.Timestamp(sp.WORLD_CUP_START) - pd.Timedelta(days=1),
          pd.Timestamp(sp.WORLD_CUP_END), pd.Timestamp("2026-08-01")],
    labels=["Pre-tournament", "Tournament", "Post-tournament"],
)
daily["service_hours"] = daily.date.dt.date.map(sp.service_hours)
daily["vrh"] = daily.date.dt.date.map(sp.vehicle_revenue_hours)

baseline = daily.groupby(daily.date.dt.to_period("M")).agg(
    days=("boardings", "size"),
    total=("boardings", "sum"),
    mean=("boardings", "mean"),
    median=("boardings", "median"),
    peak=("boardings", "max"),
    low=("boardings", "min"),
).round(1)
baseline.index = baseline.index.astype(str)
display(baseline)

print(f"Peak day : {daily.loc[daily.boardings.idxmax(), 'date']:%Y-%m-%d} "
      f"({daily.boardings.max()} boardings)")
print(f"Lowest   : {daily.loc[daily.boardings.idxmin(), 'date']:%Y-%m-%d} "
      f"({daily.boardings.min()} boardings)")
print(f"Days below 10 boardings: {(daily.boardings < 10).sum()}")
""")

md(r"""
## 3. The daily record

The shaded band is the World Cup window. The orange bars are Atlanta's eight match days at
Mercedes-Benz Stadium, when service ran 16 hours instead of 10.
""")

co(r"""
fig, ax = plt.subplots(figsize=(11, 3.6))

ax.axvspan(pd.Timestamp(sp.WORLD_CUP_START), pd.Timestamp(sp.WORLD_CUP_END),
           color=YELLOW, alpha=0.13, lw=0, zorder=0)

colors = [ORANGE if m else BLUE for m in daily.is_match_day]
# astype(float) turns pd.NA into NaN, which matplotlib draws as a gap.
ax.bar(daily.date, daily.boardings.astype(float), color=colors, width=0.78, zorder=2)

ax.set_xlim(daily.date.min() - pd.Timedelta(days=1), daily.date.max() + pd.Timedelta(days=1))
ax.set_ylim(0, 118)

ax.annotate("World Cup window\nJun 11 - Jul 19", xy=(pd.Timestamp("2026-06-24"), 112),
            ha="center", va="top", fontsize=8, color=MUTED)
# The shaded band already marks the tournament end, so only two annotations
# are needed; both are anchored clear of neighbouring bars.
ax.annotate("Soft launch\nMay 31", xy=(pd.Timestamp("2026-05-31"), 30),
            xytext=(pd.Timestamp("2026-06-02"), 74), ha="left", fontsize=7.5, color=INK2,
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7,
                            shrinkA=0, shrinkB=3))
ax.annotate("Peak 103", xy=(pd.Timestamp("2026-07-01"), 103), xytext=(0, 6),
            textcoords="offset points", ha="center", fontsize=7.5, color=INK2)

from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=BLUE, label="Regular day"),
                   Patch(color=ORANGE, label="Atlanta match day (16h service)")],
          loc="upper right", ncol=1)

tidy(ax, "Daily boardings, ATL Spoke",
     "May 31 - Jul 31 2026 | shaded: FIFA World Cup 26", "Boardings")
plt.tight_layout(); plt.show()
""")

md(r"""
## 4. Ramp-up from the soft launch

The service soft-launched on May 31 and opened to the public on June 5. The first ten days ran
at a low base, before the tournament started.
""")

co(r"""
pre_wc = daily[daily.date < pd.Timestamp(sp.WORLD_CUP_START)]
post_wc = daily[daily.date > pd.Timestamp(sp.WORLD_CUP_END)]
during = daily[(daily.date >= pd.Timestamp(sp.WORLD_CUP_START))
               & (daily.date <= pd.Timestamp(sp.WORLD_CUP_END))]

summary = pd.DataFrame({
    "days": [len(pre_wc), len(during), len(post_wc)],
    "boardings": [pre_wc.boardings.sum(), during.boardings.sum(), post_wc.boardings.sum()],
    "per_day": [pre_wc.boardings.mean(), during.boardings.mean(), post_wc.boardings.mean()],
}, index=["Pre-tournament (May 31 - Jun 10)", "Tournament (Jun 11 - Jul 19)",
          "Post-tournament (Jul 20 - Jul 31)"]).round(1)
display(summary)

ratio = during.boardings.mean() / pre_wc.boardings.mean()
recover = post_wc.boardings.mean() / pre_wc.boardings.mean()
print(f"Tournament ran {ratio:.1f}x the pre-tournament daily rate.")
print(f"Post-tournament sits at {recover:.2f}x the pre-tournament rate "
      f"({post_wc.boardings.mean():.1f} vs {pre_wc.boardings.mean():.1f} per day).")
""")

co(r"""
fig, ax = plt.subplots(figsize=(7.2, 3.4))
vals = summary.per_day.values
bars = ax.bar(range(3), vals, color=[BLUE, ORANGE, AQUA], width=0.6)
for i, v in enumerate(vals):
    ax.annotate(f"{v:.1f}", (i, v), xytext=(0, 4), textcoords="offset points",
                ha="center", fontsize=9, color=INK)
ax.set_xticks(range(3))
ax.set_xticklabels(["Pre-tournament\nMay 31 - Jun 10", "Tournament\nJun 11 - Jul 19",
                    "Post-tournament\nJul 20 - Jul 31"], fontsize=8)
ax.set_ylim(0, max(vals) * 1.2)
tidy(ax, "Average daily boardings by period",
     "The post-tournament rate returns to the pre-tournament baseline", "Boardings per day")
plt.tight_layout(); plt.show()
""")

md(r"""
## 5. Day of week

Match days are not spread evenly across the week. Three of the eight fell on a Wednesday, so
the raw weekday average carries a World Cup effect inside it. Both series are shown below.
""")

co(r"""
order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
regular = daily[~daily.is_match_day]
dow = pd.DataFrame({
    "all days": daily.groupby("weekday").boardings.mean().reindex(order),
    "excl. match days": regular.groupby("weekday").boardings.mean().reindex(order),
    "match days on this weekday": daily[daily.is_match_day].groupby("weekday")
                                       .size().reindex(order).fillna(0).astype(int),
}).round(1)
display(dow)

fig, ax = plt.subplots(figsize=(8.4, 3.2))
x = range(7)
ax.bar([i - 0.19 for i in x], dow["all days"], width=0.36, color=BLUE, label="All days")
ax.bar([i + 0.19 for i in x], dow["excl. match days"], width=0.36, color=AQUA,
       label="Excluding World Cup match days")
for i, v in enumerate(dow["excl. match days"]):
    ax.annotate(f"{v:.0f}", (i + 0.19, v), xytext=(0, 4), textcoords="offset points",
                ha="center", fontsize=8, color=INK)
ax.set_xticks(list(x)); ax.set_xticklabels([d[:3] for d in order])
ax.set_ylim(0, dow["all days"].max() * 1.25)
ax.legend(loc="upper left")
tidy(ax, "Average boardings by day of week", "62 service days", "Boardings per day")
plt.tight_layout(); plt.show()

for label, df in [("all days", daily), ("excluding match days", regular)]:
    wk = df[~df.is_weekend].boardings.mean()
    we = df[df.is_weekend].boardings.mean()
    print(f"{label:22s} weekday {wk:5.1f}  weekend {we:5.1f}  ({we / wk - 1:+.1%})")
""")

md(r"""
## 6. Where the decline came from

Both months sold about the same amount of service. Longer match-day hours in June offset July's
extra calendar day. So this is a demand story, not a supply story.
""")

co(r"""
per_month = daily[daily.date >= "2026-06-01"].groupby("month").agg(
    boardings=("boardings", "sum"),
    days=("boardings", "size"),
    match_days=("is_match_day", "sum"),
    service_hours=("service_hours", "sum"),
    vrh=("vrh", "sum"),
)
per_month["boardings_per_day"] = (per_month.boardings / per_month.days).round(1)
per_month["boardings_per_vrh"] = (per_month.boardings / per_month.vrh).round(3)
per_month.index = per_month.index.strftime("%B %Y")
display(per_month)

jun, jul = per_month.iloc[0], per_month.iloc[1]
print(f"Ridership      {jun.boardings:>6,.0f} -> {jul.boardings:>6,.0f}  "
      f"({jul.boardings/jun.boardings - 1:+.1%})")
print(f"Revenue hours  {jun.vrh:>6,.0f} -> {jul.vrh:>6,.0f}  "
      f"({jul.vrh/jun.vrh - 1:+.1%})")
print(f"Productivity   {jun.boardings_per_vrh:>6.2f} -> {jul.boardings_per_vrh:>6.2f}  "
      f"boardings per vehicle revenue hour ({jul.boardings_per_vrh/jun.boardings_per_vrh - 1:+.1%})")
""")

co(r"""
# Shift-share decomposition. June and July hold different numbers of tournament
# days (20 vs 19) and non-tournament days (10 vs 12), so differencing the totals
# would confound a change in day MIX with a change in the RATE on those days.
# Holding one fixed at a time separates them, and the parts sum to the whole.
jun_d = daily[(daily.date >= "2026-06-01") & (daily.date <= "2026-06-30")]
jul_d = daily[daily.date >= "2026-07-01"]

def split(df):
    wc = df[df.period == "Tournament"]
    non = df[df.period != "Tournament"]
    return (wc.boardings.count(), wc.boardings.mean(),
            non.boardings.count(), non.boardings.mean())

n_jw, r_jw, n_jn, r_jn = split(jun_d)
n_lw, r_lw, n_ln, r_ln = split(jul_d)

profile = pd.DataFrame({
    "June days observed": [n_jw, n_jn],
    "June per day": [round(r_jw, 1), round(r_jn, 1)],
    "July days observed": [n_lw, n_ln],
    "July per day": [round(r_lw, 1), round(r_ln, 1)],
}, index=["Inside tournament window", "Outside tournament window"])
display(profile)

mix = (n_lw - n_jw) * r_jw + (n_ln - n_jn) * r_jn
rate_wc = n_lw * (r_lw - r_jw)     # tournament days got quieter
rate_non = n_ln * (r_ln - r_jn)    # non-tournament days got busier
observed = jul_d.boardings.sum() - jun_d.boardings.sum()

# The rate term is reported split. Quoting only its net would describe a large
# negative and a large positive as one number, and would contradict the growth
# result on the line below it.
print(f"Observed change               : {observed:+,.0f} boardings")
print(f"  day-mix effect              : {mix:+,.1f}")
print(f"  rate on tournament days     : {rate_wc:+,.1f}")
print(f"  rate on non-tournament days : {rate_non:+,.1f}")
print(f"  sum of the three components : {mix + rate_wc + rate_non:+,.1f}")
print()
print(f"Tournament-day rate fell {r_jw:.1f} to {r_lw:.1f} per day ({r_lw / r_jw - 1:+.1%}). "
      f"Atlanta hosted 5 matches in June and 3 in July.")
print(f"Non-tournament rate rose {r_jn:.1f} to {r_ln:.1f} per day ({r_ln / r_jn - 1:+.1%}), "
      f"offsetting part of that fall.")

match_mean = daily[daily.is_match_day].boardings.mean()
nonmatch_in = during[~during.is_match_day].boardings.mean()
print(f"\nMatch days average {match_mean:.1f} boardings vs "
      f"{nonmatch_in:.1f} on non-match days inside the window "
      f"({match_mean / nonmatch_in - 1:+.0%}).")

# That gap was previously reported without a test. With 8 match days in a
# 39-day window it needs one, and it needs to survive day-of-week, since three
# of the eight matches fell on a Wednesday.
rng = np.random.default_rng(0)
win = during.dropna(subset=["boardings"]).copy()
vals = win.boardings.to_numpy(dtype=float)
k = int(win.is_match_day.sum())
obs = vals[win.is_match_day].mean() - vals[~win.is_match_day].mean()

win["dow"] = win.date.dt.dayofweek
resid = (win.boardings.astype(float)
         - win.groupby("dow").boardings.transform("mean").astype(float)).to_numpy()
obs_adj = resid[win.is_match_day].mean() - resid[~win.is_match_day].mean()

def perm_p(x, observed, draws=20000):
    hits = 0
    for _ in range(draws):
        i = rng.permutation(len(x))
        if x[i[:k]].mean() - x[i[k:]].mean() >= observed:
            hits += 1
    return hits / draws

print(f"\nPermutation test, {k} match days in a {len(win)}-day window, 20k draws")
print(f"  raw gap                      {obs:+6.2f} boardings/day   p = {perm_p(vals, obs):.4f}")
print(f"  after removing day-of-week   {obs_adj:+6.2f} boardings/day   p = {perm_p(resid, obs_adj):.4f}")

rank = win.sort_values("boardings", ascending=False).reset_index(drop=True)
top = rank.head(3)[["date", "boardings", "is_match_day"]]
print("\nBusiest days inside the window:")
for r in top.itertuples():
    print(f"  {r.date:%Y-%m-%d %a}  {int(r.boardings):3d}  "
          f"{'Atlanta match day' if r.is_match_day else 'NOT a match day'}")
""")

md(r"""
## 7. Transit metrics

The PDFs carry no cost and no service-hour data, so every figure below rests on the assumption
register in `src/service_parameters.py`.

**The cost basis is now the full \$3M project total, not just the \$1.75M state grant.** The
Beltline board approved a \$3M pilot budget in May 2025; the \$1.75M GTEA grant is the state's
share of that, about 58%, matching AJC's reporting that the state covers "more than half the
costs." The remaining ~\$1.25M is attributed to "BeltLine / in-kind" by the one source that
breaks it down, with no further detail on what it consists of. Given the roughly 13-month gap
between board approval and launch, it plausibly covers pre-launch capital and integration cost
rather than 12-month operating spend, but no source confirms that split. We use the full \$3M as
the operating-cost basis on the more conservative assumption that it is not separable from
ongoing cost. All vehicles are leased, so lease payments sit inside op-ex, and capital spend
beyond the pilot's own budget is limited to signage and other small items. That makes
**\$250,000 a month a cost estimate rather than a ceiling**.

Two things are still unknown and are carried as ranges instead.

- **`spend_profile`** is not reported. The base case assumes level monthly spend. June and July
  are months 1 to 3 of the pilot, so a front-loaded profile would make them *more* expensive than
  average, not less.
- **`vehicles_in_service`** is not reported. It is inferred as 3 of 4 from a 34-minute loop at 12
  to 15 minute headway. This only affects the per-revenue-hour figures.

`avg_trip_length_mi` is also assumed at 0.7 mi, and it only affects cost per passenger mile.
""")

co(r"""
COST = sp.PARAMS["monthly_cost_usd"].value
TRIP_MI = sp.PARAMS["avg_trip_length_mi"].value

met = per_month.copy()
met["passenger_miles"] = met.boardings * TRIP_MI
met["cost_per_trip"] = (COST / met.boardings).round(2)
met["cost_per_operating_hour"] = (COST / met.service_hours).round(2)
met["cost_per_revenue_hour"] = (COST / met.vrh).round(2)
met["cost_per_passenger_mile"] = (COST / met.passenger_miles).round(2)

out = met[["boardings", "service_hours", "vrh", "passenger_miles", "boardings_per_vrh",
           "cost_per_trip", "cost_per_operating_hour", "cost_per_revenue_hour",
           "cost_per_passenger_mile"]]
display(out.T)

print(f"Monthly operating cost ${COST:,.0f}  (= $3M / 12, all op-ex, leased fleet)")
print("cost_per_operating_hour uses wall-clock hours the service is open.")
print("cost_per_revenue_hour multiplies those hours by vehicles in service "
      f"({sp.PARAMS['vehicles_in_service'].value}).")
""")

co(r"""
# With the cost basis fixed, the live unknowns are spend timing and fleet count.
rows = []
for frac, flabel in [(1.0, "Level spend (base)"), (1.25, "Front-loaded +25%"),
                     (0.75, "Back-loaded -25%")]:
    for veh in (3, 4):
        c = COST * frac
        vrh = sum(sp.vehicle_revenue_hours(d.date(), veh) for d in jul_d.date)
        hrs = jul_d.service_hours.sum()
        rows.append({
            "spend profile": flabel, "vehicles": veh,
            "cost/trip": round(c / jul_d.boardings.sum(), 2),
            "cost/operating hr": round(c / hrs, 2),
            "cost/revenue hr": round(c / vrh, 2),
        })
sens = pd.DataFrame(rows)
print("July 2026 sensitivity")
display(sens)

tl = pd.DataFrame({
    "avg trip length (mi)": [0.5, 0.7, 1.0, 1.5],
    "cost per passenger mile": [round(COST / (jul_d.boardings.sum() * m), 2)
                                for m in (0.5, 0.7, 1.0, 1.5)],
})
print("July cost per passenger mile across trip-length assumptions")
display(tl)
""")

md(r"""
## 8. Comparisons

Cost per boarding is the one metric with directly comparable published figures across Atlanta
systems. MARTA's own scorecard gives a consistent May 2026 snapshot.
""")

co(r"""
cpt = peers[peers.metric == "cost_per_trip"].copy()
atl = pd.DataFrame([{
    "system": "ATL Spoke (July 2026)", "value": met.cost_per_trip.iloc[1],
    "period": "assumption-driven", "mode": "AV shuttle",
}])
comp = pd.concat([cpt[["system", "value", "period", "mode"]], atl]).sort_values("value")

fig, ax = plt.subplots(figsize=(8.4, 4.0))
cols = [RED if s.startswith("ATL Spoke") else BLUE for s in comp.system]
ax.barh(range(len(comp)), comp.value, color=cols, height=0.62)
for i, v in enumerate(comp.value):
    ax.annotate(f"${v:,.2f}", (v, i), xytext=(5, 0), textcoords="offset points",
                va="center", fontsize=8, color=INK)
ax.set_yticks(range(len(comp)))
ax.set_yticklabels([f"{r.system}\n{r.period}" for r in comp.itertuples()], fontsize=7.5)
ax.set_xlim(0, comp.value.max() * 1.25)
ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
tidy(ax, "Operating cost per boarding", "ATL Spoke figure is assumption-driven - see section 7")
plt.tight_layout(); plt.show()

marta_bus = comp.loc[comp.system == "MARTA Bus", "value"].max()
print(f"ATL Spoke July cost/trip is {met.cost_per_trip.iloc[1]/marta_bus:.1f}x "
      f"MARTA Bus at its May 2026 rate (${marta_bus:.2f}).")
""")

co(r"""
cph = peers[peers.metric == "cost_per_revenue_hour"].copy()
atl_h = pd.DataFrame([{"system": "ATL Spoke (July 2026)",
                       "value": met.cost_per_revenue_hour.iloc[1], "period": "assumption-driven"}])
comph = pd.concat([cph[["system", "value", "period"]], atl_h]).sort_values("value")

fig, ax = plt.subplots(figsize=(8.4, 3.2))
cols = [RED if s.startswith("ATL Spoke") else BLUE for s in comph.system]
ax.barh(range(len(comph)), comph.value, color=cols, height=0.6)
for i, v in enumerate(comph.value):
    ax.annotate(f"${v:,.0f}", (v, i), xytext=(5, 0), textcoords="offset points",
                va="center", fontsize=8, color=INK)
ax.set_yticks(range(len(comph)))
ax.set_yticklabels([f"{r.system}\n{r.period}" for r in comph.itertuples()], fontsize=7.5)
ax.set_xlim(0, comph.value.max() * 1.25)
ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
tidy(ax, "Operating cost per vehicle revenue hour", "Mixed vintages - directional only")
plt.tight_layout(); plt.show()
""")

md(r"""
### The closest comparison is Beep's own Cumberland Hopper

The nearest comparator is **the same operator running the same kind of pilot twelve miles
away**. Beep ran the *Cumberland Hopper* for the Cumberland CID in Cobb County.
Two routes linked Cobb Galleria to The Battery across the I-285 pedestrian bridge. Free fare,
onboard attendant, 8-passenger vehicles at 10 to 15 mph.

It matches ATL Spoke on structure and on what drove demand. The Hopper was built around **Atlanta
Braves game nights**. ATL Spoke was built around World Cup match days. Both are event-led pilots
rather than commute services.

| | Cumberland Hopper | ATL Spoke |
|---|---|---|
| Operator | Beep | Beep |
| Period | Jul 2023 to Dec 2024 | Jun 2026, ongoing |
| Fare | free | free |
| Demand anchor | Braves home games | World Cup match days |
| Disclosed funding | \$400K phase 1 plus ~\$130K phase 2 | \$3M over 12 months (incl. \$1.75M GTEA grant) |
| Riders | 11,000+ total | 1,306 in July alone |
| **Cost per boarding** | **~\$48** | **\$191.42** |

So ATL Spoke costs about 4.0 times the Hopper per rider.

Two things qualify that. The Hopper's cost basis is the CID's disclosed investment, and its rider
total spans two phases whose month counts are reported inconsistently across sources.

The bigger qualifier is service supplied. The Hopper ran mostly on event evenings plus some
weekdays. ATL Spoke runs seven days a week for 10 to 16 hours. Per boarding the Hopper is cheaper.
Per hour of service available it may not be. The Hopper's revenue hours were never published, so
that comparison cannot be made.
""")

md(r"""
### Cost per passenger mile

Cobb County publishes passenger-mile costs for both its on-demand and fixed-route service, which
gives this metric a local anchor. ATL Spoke's figure carries the assumed 0.7-mile average trip and
moves inversely with it.
""")

co(r"""
pm = peers[peers.metric == "cost_per_passenger_mile"].copy()
atl_pm = pd.DataFrame([{"system": "ATL Spoke (July 2026)",
                        "value": met.cost_per_passenger_mile.iloc[1], "period": "assumption-driven"}])
comppm = pd.concat([pm[["system", "value", "period"]], atl_pm]).sort_values("value")

fig, ax = plt.subplots(figsize=(8.0, 2.6))
cols = [RED if s.startswith("ATL Spoke") else BLUE for s in comppm.system]
ax.barh(range(len(comppm)), comppm.value, color=cols, height=0.58)
for i, v in enumerate(comppm.value):
    ax.annotate(f"${v:,.2f}", (v, i), xytext=(5, 0), textcoords="offset points",
                va="center", fontsize=8, color=INK)
ax.set_yticks(range(len(comppm)))
ax.set_yticklabels([f"{r.system}\n{r.period}" for r in comppm.itertuples()], fontsize=7.5)
ax.set_xlim(0, comppm.value.max() * 1.25)
ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
tidy(ax, "Operating cost per passenger mile", "Log-scale difference - note the axis range")
plt.tight_layout(); plt.show()

cobb_go = comppm.loc[comppm.system == "CobbLinc Go microtransit", "value"].iat[0]
print(f"ATL Spoke runs {met.cost_per_passenger_mile.iloc[1]/cobb_go:.0f}x CobbLinc Go on-demand "
      f"(${cobb_go:.2f}) and {met.cost_per_passenger_mile.iloc[1]/5.66:.0f}x CobbLinc fixed-route bus.")
""")

md(r"""
### What a rideshare would cost for the same trip

A fair question for a two-mile shuttle is what it would cost to just buy every rider a Lyft.

**These are not the same kind of number.** ATL Spoke's figure is *public cost per boarding*. A
rideshare fare is *the price the passenger pays*. It leaves out the driver's unreimbursed costs
and any public subsidy, and it buys no ADA guarantee, no zero fare, and no fixed-route
reliability. Read the chart as a rough sanity check on a short fixed loop, not as an equivalence.
""")

co(r"""
rs = peers[peers.metric.isin(["fare_2mi_equivalent", "fare_avg_trip"])].copy()
# The note column carries dollar amounts, so render it with MathJax disabled.
display(HTML(rs[["system", "value", "value_low", "value_high", "period", "note"]]
             .rename(columns={"value": "USD"})
             .to_html(classes=NO_MATH, index=False)))

uber_2mi = rs.loc[rs.system == "Uber (Atlanta)", "value"].iat[0]
lyft_2mi = rs.loc[rs.system == "Lyft (Atlanta)", "value"].iat[0]
jul_cpt = met.cost_per_trip.iloc[1]

fig, ax = plt.subplots(figsize=(8.0, 2.9))
rows = [("ATL Spoke, level spend", jul_cpt, RED),
        ("ATL Spoke, back-loaded spend", 143.57, ORANGE),
        ("US average rideshare fare", 23.66, BLUE),
        ("Uber, Atlanta 2-mile equivalent", uber_2mi, BLUE),
        ("Lyft, Atlanta 2-mile equivalent", lyft_2mi, BLUE)]
labels = [r[0] for r in rows][::-1]
vals = [r[1] for r in rows][::-1]
cols = [r[2] for r in rows][::-1]
ax.barh(range(len(rows)), vals, color=cols, height=0.6)
for i, v in enumerate(vals):
    ax.annotate(f"${v:,.2f}", (v, i), xytext=(5, 0), textcoords="offset points",
                va="center", fontsize=8, color=INK)
ax.set_yticks(range(len(rows))); ax.set_yticklabels(labels, fontsize=7.5)
ax.set_xlim(0, max(vals) * 1.28)
ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
tidy(ax, "Public cost per boarding vs rideshare price per trip",
     "Different kinds of number - see the note above")
plt.tight_layout(); plt.show()

print(f"One ATL Spoke boarding costs {jul_cpt/lyft_2mi:.0f}x a Lyft fare for the same "
      f"2-mile trip, and {jul_cpt/uber_2mi:.0f}x an Uber fare.")
print()
print("What that leaves out. Guaranteed ADA service, no fare at the point of use, and")
print("fixed-route reliability. A pilot built to test the technology is also not")
print("procured to minimise cost per rider.")
""")

md(r"""
## 9. Findings

1. **The July decline tracks the World Cup, not any sign of service decay.** Ridership follows
   the tournament window. A low base before it, a sharp lift from June 11, then a fall as the
   tournament wound down. The largest single component is the rate on tournament days, worth
   -287.9 boardings, which fell because Atlanta hosted three matches in July against five in
   June. This is attribution from a 62-day series, not a causal estimate. See the limits below.

2. **Demand outside the tournament rose 59%.** The local market grew between June and July even
   as the headline number fell, which is the opposite of what the monthly total suggests.

3. **Productivity fell further than ridership did.** Longer match-day hours held revenue hours
   flat, so July bought the same service for fewer riders. Boardings per revenue hour went from
   1.51 to 1.33.

4. **Match days average well above other tournament-window days, and the gap survives a test.**
   78.0 boardings against 51.2. A permutation test gives p = 0.001 raw and p = 0.020 after
   removing day-of-week means, so the effect is real rather than a Wednesday artifact. With 8
   match days and a post-hoc comparison, treat p = 0.02 as meaningful rather than decisive.

   Match days are not the busiest days outright. 2026-06-13 (102) and 2026-06-14 (98) are the two
   busiest days in the window and neither is a match day. Both fall on the tournament's opening
   weekend. Mercedes-Benz Stadium is not on this route either, so match demand reaches the shuttle
   only indirectly, through the rail line and through Lee+White as a destination. Atlanta matches
   are one driver of peak demand, not the only one.

5. **The route did not change.** Both months ran the 2-mile Phase 1 loop as ABI Short. The AUC
   extension opened in mid-August 2026, after this window. So route change is ruled out.

6. **There is no reliable weekday or weekend pattern in 62 days.** An earlier version of this
   finding claimed a weekday lean. It does not survive scrutiny. Two separate problems: three of
   the eight match days fell on a Wednesday, inflating the weekday average, and the single
   unobserved day (2026-07-26) is a Sunday. Excluding match days and the missing day, weekends
   run slightly *above* weekdays. With 8 or 9 observations per weekday, one missing day moves the
   answer, so treat day-of-week as unresolved.

7. **July cost \$191.42 per boarding.** With the full \$3M project cost treated as operating
   expense and the fleet leased, that is an estimate rather than a ceiling. It is 13.0 times
   MARTA Bus at its May 2026 rate and 25 times CobbLinc Go per passenger mile.

8. **ATL Spoke costs about 4.0 times the Cumberland Hopper per boarding.** The Hopper was the
   same operator running the same kind of pilot. It ran less service, so the gap per hour of
   service available is probably smaller. Its revenue hours were never published.

9. **What is still uncertain is timing and fleet count, not the cost basis.** A front-loaded
   spend profile would make June and July more expensive than average, since they are months 1 to
   3 of the pilot. Running 4 vehicles instead of 3 would cut cost per revenue hour by a quarter.

### Limits

- **62 days, two months, one service.** This is attribution, not causation. There is no
  counterfactual and no control, so nothing here estimates what ridership would have been
  without the tournament.
- **The launch ramp and the tournament overlap.** Public launch was June 5; the tournament
  started June 11. The 11-day "pre-tournament" base is the first days of a brand new service,
  including its two lowest non-outage days. The lift from that base and the later growth outside
  the window are both inseparable from ordinary ramp-up.
- **Confounds not measured.** Weather, school calendar, marketing, novelty decay and Beltline
  event programming are all unobserved and none can be ruled out.
- **One day has no observation** (2026-07-26) and one more looks like a partial outage
  (2026-07-27 records a single boarding between days of 23 and 20).
- **All cost figures rest on assumptions**, not on reported cost or service-hour data.
- **The extended-hours rule is ambiguous in the source.** One passage says hours extended "on
  FIFA World Cup 26 game days" and another says "on Atlanta's eight match days". There were
  matches somewhere in North America on most group-stage days. This analysis models 16 hours on
  Atlanta's eight days only. If the operator extended hours more widely, revenue hours are
  understated in both months and the productivity comparison shifts.

### What would sharpen this

- The **"Full Ridership"** stop-level PDFs would allow boarding and alighting analysis by stop.
- **Monthly spend actuals** from Beep or ABI would replace the level-spend assumption, which is
  now the largest single unknown.
- **Vehicle assignment records** would settle whether 3 or 4 vehicles ran.
- **Cumberland Hopper revenue hours** would make that comparison fair on service supplied rather
  than only on riders carried.
- **August reports onward** would separate the AUC extension from post-tournament drift, and would
  let ABI Long be measured on its own.
""")

nb["cells"] = C
nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
Path("analysis.ipynb").write_text(nbf.writes(nb))
print(f"analysis.ipynb written: {len(C)} cells")
