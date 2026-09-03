"""Assumption register for ATL Spoke transit metrics.

Every external input the analysis depends on lives here with its value, its
source, and an honest confidence rating. Nothing derived from these numbers
appears in the notebook without tracing back to this file.

Cost basis. The full $3M project budget is treated as operating expense, not
just the $1.75M state grant that makes up 58% of it. Vehicles are leased, so
lease payments sit inside op-ex, and capital spend is limited to signage and
other minor items. That makes $3M / 12 = $250,000 the monthly operating cost.

The report also presents a grant-only basis ($1.75M / 12 = $145,833) alongside
it, because the ~$1.25M non-grant share is never broken down publicly and may be
partly in-kind. See total_project_cost_usd.

Two unknowns remain. Spend may not be level across the pilot, and the number of
vehicles actually in service is not reported. Both are carried as sensitivity
ranges rather than folded into the headline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Param:
    value: object
    unit: str
    confidence: str  # high | medium | low
    source: str
    note: str = ""


# --- Service definition -----------------------------------------------------

SERVICE = "ATL Spoke"
OPERATOR = "Beep"
SPONSOR = "Atlanta Beltline, Inc. (ABI)"

BELTLINE = "https://beltline.org/atl-spoke/"
LAUNCH_BLOG = ("https://beltline.org/blog/"
               "atl-spoke-launches-as-atlanta-s-first-autonomous-public-transit-service/")
SAPORTA = ("https://saportareport.com/atlanta-debuts-its-new-automated-shuttle-"
           "atl-spoke-connecting-marta-to-the-beltline/sections/reports/mark-lannaman/")
MASSTRANSIT = ("https://www.masstransitmag.com/alt-mobility/autonomous-vehicles/news/"
               "55383618/atlanta-beltline-inc-atlanta-beltline-launches-atl-spoke-"
               "autonomous-shuttle-pilot-service")

PARAMS: dict[str, Param] = {
    "route_length_mi": Param(
        2.0, "miles", "medium", BELTLINE,
        "Phase 1 loop, reported as 'approximately two miles'. Identical in "
        "June and July -- the AUC extension opened mid-August 2026, after the "
        "data window, so route length is NOT a candidate explanation for the "
        "month-over-month change."),
    "routes_in_service": Param(
        "ABI Short", "route", "high", "confirmed by service operator",
        "RESOLVED. The PDF header lists 'ABI Short | ABI Long', but only "
        "ABI Short operated during Phase 1 -- so all June and July boardings "
        "are ABI Short. ABI Long is the AUC-extension pattern, configured in "
        "the reporting system ahead of its mid-August 2026 launch."),
    "fleet_size": Param(
        4, "vehicles", "high", BELTLINE,
        "ABI-01..04, matching the vehicle list in the PDF headers."),
    "vehicle_capacity": Param(
        12, "passengers", "high", BELTLINE, ""),
    "vehicles_in_service": Param(
        3, "vehicles", "low", BELTLINE,
        "NOT REPORTED. Inferred: a 34-minute loop at 12-15 minute headway "
        "needs ceil(34/13) = 3 vehicles in service, leaving one spare. "
        "Sensitivity is run at 3 and 4 -- a 33% swing in revenue hours."),
    "loop_cycle_min": Param(
        34, "minutes", "medium", "https://transitapp.com/en/region/atlanta/atl-spoke/bus-spoke",
        "End-to-end loop time shown in Transit app trip planning."),
    "headway_min": Param(
        (12, 15), "minutes", "high", BELTLINE, ""),
    "regular_hours_per_day": Param(
        10.0, "hours", "high", BELTLINE,
        "Noon to 10:00 PM, seven days a week."),
    "matchday_hours_per_day": Param(
        16.0, "hours", "high", LAUNCH_BLOG,
        "8:00 AM to midnight on FIFA World Cup 26 match days at Mercedes-Benz "
        "Stadium. This is why June and July have near-identical revenue hours "
        "despite different ridership."),
    "fare": Param(
        0.0, "USD", "high", BELTLINE,
        "Zero fare for the full 12-month pilot, so farebox recovery is 0% by "
        "design and no fare-based metric is meaningful."),
    "grant_total_usd": Param(
        1_750_000.0, "USD", "high", MASSTRANSIT,
        "Georgia Transportation Efficiency Authority award. This is the STATE "
        "share only, roughly 58% of the total project cost -- see "
        "total_project_cost_usd. Kept as its own parameter because it is the "
        "figure most press coverage reports in isolation."),
    "total_project_cost_usd": Param(
        3_000_000.0, "USD", "medium", "AJC, BeepThroat, Civic Atlanta",
        "The Beltline board approved a $3M total pilot budget in May 2025, "
        "roughly a year before the June 2026 launch; the $1.75M GTEA grant "
        "covers the state's share of that total. Corroborated three ways: AJC "
        "reports the state covering 'more than half the costs' (1.75/3.00 = "
        "58%, consistent); Civic Atlanta cites '$3 million' directly; "
        "BeepThroat, an open-records project, cites a specific board document "
        "(its DOC-015, 'Beep AV pilot approval, $3M, 5/2025') and attributes "
        "the remaining ~$1.25M to 'BeltLine / in-kind'. "
        "UNRESOLVED: what the $1.25M gap actually consists of -- no source "
        "breaks it down. Given the ~13-month gap between the May 2025 board "
        "approval and the June 2026 launch, it plausibly covers pre-launch "
        "capital and integration cost (vehicle procurement, technology setup) "
        "rather than 12-month operating spend, but this is inference, not a "
        "confirmed source. We use the full $3M as the operating-cost basis "
        "below on the more conservative assumption that it is NOT separable "
        "from ongoing cost. See monthly_cost_usd."),
    "pilot_months": Param(
        12, "months", "high", BELTLINE, ""),
    "monthly_cost_usd": Param(
        3_000_000.0 / 12, "USD/month", "medium", "AJC, BeepThroat, Civic Atlanta",
        "Even 1/12 split of the $3M total project cost (not just the $1.75M "
        "GTEA grant -- see total_project_cost_usd for why), treated as fully "
        "operating expense per the operator's direction. Vehicles are leased "
        "so lease cost is op-ex, and capital spend is limited to signage and "
        "similar minor items. This is a cost estimate, not a ceiling. Two open "
        "questions: timing, since pilot spend is often front-loaded, and "
        "whether the ~$1.25M non-GTEA share is really operating cost at all "
        "rather than pre-launch capital -- see total_project_cost_usd. "
        "Sensitivity runs a level profile against front-loaded and "
        "back-loaded variants at +/- 25%."),
    "capex_treatment": Param(
        "leased fleet, minor capex only", "n/a", "high",
        "operator direction",
        "Vehicles are leased rather than purchased. Capital spend is limited to "
        "signage and other small items, so no capital amortisation is separated "
        "out of the monthly figure."),
    "spend_profile": Param(
        1.0, "multiplier", "low", "",
        "NOT REPORTED. Base case assumes level monthly spend across the pilot. "
        "June and July are months 1 to 3, so a front-loaded profile would make "
        "them more expensive than the average, not less. Sensitivity runs 0.75, "
        "1.0 and 1.25."),
    "avg_trip_length_mi": Param(
        0.7, "miles", "low", "",
        "NOT REPORTED. Assumed from a 2-mile, 4-stop loop where the dominant "
        "movement is West End MARTA <-> Lee+White. Sensitivity 0.5-1.5 mi. "
        "Passenger-mile metrics inherit this uncertainty entirely."),
}

# --- Calendar ---------------------------------------------------------------

SOFT_LAUNCH = date(2026, 5, 31)      # 28 boardings; matches the May bar exactly
PUBLIC_LAUNCH = date(2026, 6, 5)

# Phase 2 (AUC extension): confirmed by multiple same-day reports, timed to the
# start of the AUC fall semester. Fleet, hours (noon-10pm) and fare unchanged.
PHASE2_START = date(2026, 8, 19)
PHASE2_STOPS = (
    "Clark Atlanta University", "Morehouse College",
    "Morehouse School of Medicine", "Spelman College",
)
PHASE2_SOURCE = ("https://roughdraftatlanta.com/2026/08/19/atl-spoke-expands-auc-route/",
                 "https://www.atlantanewsfirst.com/2026/08/19/"
                 "citys-first-autonomous-shuttle-adds-atlanta-university-center-stop/",
                 "https://atlanta.urbanize.city/post/"
                 "atl-spoke-beltline-expands-autonomous-shuttle-system-starting-today")
# No source publishes the added route mileage for the AUC leg as of this writing,
# so route_length_mi below still reflects Phase 1 only and is NOT extended to
# cover Phase 2. Do not use it to compute post-August cost-per-mile figures.

WORLD_CUP_START = date(2026, 6, 11)
WORLD_CUP_END = date(2026, 7, 19)

# Eight matches at Mercedes-Benz Stadium ("Atlanta Stadium" during the
# tournament). Service extended to 16 hours on each of these days.
ATLANTA_MATCH_DAYS: list[date] = [
    date(2026, 6, 15),   # Spain v Cabo Verde
    date(2026, 6, 18),   # South Africa v Czechia
    date(2026, 6, 21),   # Spain v Saudi Arabia
    date(2026, 6, 24),   # Morocco v Haiti
    date(2026, 6, 27),   # Uzbekistan v DR Congo
    date(2026, 7, 1),    # Round of 32
    date(2026, 7, 7),    # Round of 16
    date(2026, 7, 15),   # Semifinal
]
MATCH_SOURCE = ("https://www.wsbtv.com/news/local/2026-fifa-world-cup-atlanta-match-"
                "schedule-which-countries-will-play-mercedes-benz-stadium/"
                "2HYNPLL32FDSZMMSCVCREYPVZU/")


def service_hours(day: date) -> float:
    """Wall-clock hours the service is open on a given day."""
    if day < SOFT_LAUNCH:
        return 0.0
    if day in ATLANTA_MATCH_DAYS:
        return PARAMS["matchday_hours_per_day"].value
    return PARAMS["regular_hours_per_day"].value


def vehicle_revenue_hours(day: date, vehicles: int | None = None) -> float:
    """Vehicle revenue hours: open hours multiplied by vehicles in service."""
    n = PARAMS["vehicles_in_service"].value if vehicles is None else vehicles
    return service_hours(day) * n


def register_rows() -> list[dict]:
    """The register as tabular rows, for display in the notebook."""
    return [
        {"parameter": k, "value": p.value, "unit": p.unit,
         "confidence": p.confidence, "note": p.note, "source": p.source}
        for k, p in PARAMS.items()
    ]
