"""Render the opportunity position as one offline page the dashboard script drives."""

from __future__ import annotations

import html
import json
from datetime import date
from pathlib import Path

from psdesk.attention import SOON_DAYS
from psdesk.load import Table
from psdesk.payload import to_payload
from psdesk.scorecard import Scorecard

HERE = Path(__file__).resolve().parent
CONVERTED = "Converted currency, as exported"


def render(scorecard: Scorecard, opps: Table, quotes: Table, as_of: date | None) -> str:
    payload = to_payload(scorecard, opps, quotes, as_of)
    data = json.dumps(payload, ensure_ascii=False).replace("<", r"\u003c")
    css = (HERE / "dashboard.css").read_text(encoding="utf-8")
    script = (HERE / "dashboard.js").read_text(encoding="utf-8")
    title = payload["asOf"]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>APJ PS opportunities · {esc(title)}</title>
<style>
{css}
</style>
</head>
<body>
<div class="wrap">
<p class="kicker">APJ professional services</p>
<h1>Opportunities</h1>
<p class="asof" id="asof">{esc(title)}</p>
<p class="lead" id="lead">{esc(_lead(scorecard, payload))}</p>
<p class="sources">{esc(payload["sources"])}</p>
<div class="books" id="books"></div>
<div class="boats" id="boats"></div>
<div class="filters" id="filters"></div>
<div id="summary"></div>
<div class="stats" id="stats"></div>
<div class="charts">
<div id="chart-boat"></div>
<div id="chart-fiscal"></div>
</div>
<div class="table-head" id="table-head"></div>
<div id="table"></div>
<footer>
<p>Joined on opportunity id. A blank primary quote means no quote yet. A primary quote with no services lines is not in this quote-line export. Several lines on one id stay on that opportunity. Direct license and renewal lines are the PS package on a sales quote.</p>
<p>Money uses the converted columns already on the reports. Nothing is revalued. {esc(_money_note(scorecard))}.</p>
{_sheet_warning(quotes, scorecard)}
{_extra_notes(scorecard)}
</footer>
</div>
<script id="ps-data" type="application/json">{data}</script>
<script>
{script}
</script>
</body>
</html>
"""


def _lead(scorecard: Scorecard, payload: dict) -> str:
    count = len(scorecard.services)
    noun = "opportunity" if count == 1 else "opportunities"
    missing = scorecard.missing_quotes
    missing_verb = "has" if missing == 1 else "have"
    unlisted = scorecard.unlisted_quotes
    unlisted_verb = "has" if unlisted == 1 else "have"
    services = payload["services"]
    due = sum(1 for row in services if row["closeTiming"] == "due")
    soon = sum(1 for row in services if row["closeTiming"] == "soon")
    stale = sum(1 for row in services if row["statusFresh"] is False)
    forecast = [row for row in services if row["band"] == "forecast"]
    pipeline = [row for row in services if row["band"] == "pipeline"]
    periods = len(scorecard.fiscal_periods)
    period_bit = f" Across {periods} fiscal {'period' if periods == 1 else 'periods'}." if periods else ""
    return (
        f"{count} services {noun} in the closing export, "
        f"{_money(scorecard.services_value)} services value "
        f"and {_money(scorecard.weighted)} weighted. "
        f"Forecast, stage 80 and above, is {_money(sum(row['servicesValue'] or 0 for row in forecast))} "
        f"across {len(forecast)}. "
        f"Pipeline is {_money(sum(row['servicesValue'] or 0 for row in pipeline))} across {len(pipeline)}. "
        f"{missing} {missing_verb} no primary quote. "
        f"{unlisted} {unlisted_verb} a primary quote with no lines in the quote-line export. "
        f"{due} close today or earlier. "
        f"{soon} close in the next {payload['soonDays']} days. "
        f"{stale} need a status. "
        f"License and renewal quotes carry {_money(scorecard.shadow_value)} of PS.{period_bit}"
    )


def _sheet_warning(quotes: Table, scorecard: Scorecard) -> str:
    boats = [row.boat for row in scorecard.boats if row.boat not in {"Unassigned", "Mixed"}]
    mentioned = [boat for boat in boats if boat.casefold() in quotes.sheet.casefold()]
    others = [boat for boat in boats if boat not in mentioned]
    if not mentioned or not others:
        return ""
    listed = ", ".join(others)
    return (
        f'<p class="note">The quote sheet is named “{esc(quotes.sheet)}” and also contains {esc(listed)}.</p>'
    )


def _money_note(scorecard: Scorecard) -> str:
    if scorecard.currency:
        return f"Currency on these exports is {scorecard.currency}"
    return CONVERTED


def _extra_notes(scorecard: Scorecard) -> str:
    notes = [
        "Close dates use the report date. A close on that date or earlier is due. "
        f"A close in the next {SOON_DAYS} days is coming up. "
        "On this services book, status is weekly above 100,000, fortnightly above 50,000 through 100,000, "
        "and monthly from 0 through 50,000. A missing status date counts as overdue.",
        "Stage 80 and above is forecast. A lower stage is pipeline.",
        "Boat on a services opportunity comes from the closing file's Territory column, or a Boat column if that is the header. "
        "APJ-ANZ displays as ANZ. A blank cell falls back to the quote-line territory.",
    ]
    outside = len(scorecard.outside_quarter)
    if outside == 1:
        notes.append("1 services quote is not in the closing file, so it is left off this page.")
    elif outside:
        notes.append(f"{outside} services quotes are not in the closing file, so they are left off this page.")
    if scorecard.commit_column:
        if scorecard.commit_values:
            listed = ", ".join(scorecard.commit_values)
            notes.append(f"The old commit column has values: {listed}. It is not used as the forecast split.")
        else:
            notes.append("The column “(old) Commit?” is blank on every closing row, so this export cannot split commit and upside.")
    if len(scorecard.agreement_types) == 1:
        notes.append(f"Agreement type on every closing row is {scorecard.agreement_types[0]}.")
    if scorecard.other:
        types = ", ".join(_unique(row.record_type for row in scorecard.other))
        notes.append(f"Other record types kept in the last book: {types}.")
    return "".join(f"<p>{esc(note)}</p>" for note in notes)


def _unique(values) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen


def _money(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:,.2f}"


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)
