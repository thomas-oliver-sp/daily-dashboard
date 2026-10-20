"""Render the opportunity position as a single offline page."""

from __future__ import annotations

import html
from datetime import date

from psdesk.load import Table
from psdesk.scorecard import QuoteGroup, Scorecard, ServiceOpportunity

CONVERTED = "Converted currency, as exported"


def render(scorecard: Scorecard, opps: Table, quotes: Table, as_of: date | None) -> str:
    title_date = _as_of_label(opps, quotes, as_of)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>APJ PS opportunities · {esc(title_date)}</title>
<style>
:root {{
  --ink: #1c1915;
  --muted: #5f584e;
  --line: #e3dcd0;
  --paper: #f6f3ec;
  --card: #fffdf9;
  --flag: #8d2f2a;
  --flag-bg: #f8ecea;
  --watch: #8a5a12;
  --watch-bg: #f8f1e3;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 15px/1.45 "Segoe UI", system-ui, sans-serif;
}}
.wrap {{ max-width: 1180px; margin: 0 auto; padding: 36px 24px 72px; }}
.kicker {{
  margin: 0 0 6px;
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}}
h1 {{
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 34px;
  font-weight: 500;
  letter-spacing: -0.03em;
}}
.lead {{ max-width: 68ch; margin: 14px 0 0; font-size: 17px; }}
.sources {{ margin: 10px 0 0; color: var(--muted); font-size: 13px; }}
.stats {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 28px 0 8px;
}}
.stat {{
  background: var(--card);
  border: 1px solid var(--line);
  padding: 14px 16px 12px;
}}
.stat b {{
  display: block;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 28px;
  font-weight: 500;
  letter-spacing: -0.03em;
}}
.stat span {{ display: block; margin-top: 4px; color: var(--muted); font-size: 12px; }}
.stat.flag b {{ color: var(--flag); }}
.stat.watch b {{ color: var(--watch); }}
h2 {{
  margin: 36px 0 8px;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 22px;
  font-weight: 500;
}}
.note {{ margin: 0 0 12px; color: var(--muted); max-width: 78ch; }}
.scroll {{ overflow-x: auto; border: 1px solid var(--line); background: var(--card); }}
table {{ width: 100%; border-collapse: collapse; }}
th {{
  text-align: left;
  font-size: 11px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
  padding: 9px 10px;
  border-bottom: 1px solid var(--line);
  white-space: nowrap;
}}
td {{
  padding: 9px 10px;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
}}
tr.flag td {{ background: var(--flag-bg); }}
tr.watch td {{ background: var(--watch-bg); }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.when {{ white-space: nowrap; }}
.prose {{ white-space: normal; min-width: 12rem; max-width: 22rem; }}
.tag {{
  display: inline-block;
  margin-top: 4px;
  padding: 0 6px;
  border: 1px solid currentColor;
  font-size: 11px;
  letter-spacing: 0.02em;
}}
.tag.flag {{ color: var(--flag); }}
.tag.watch {{ color: var(--watch); }}
.empty {{ padding: 14px 16px; color: var(--muted); background: var(--card); border: 1px solid var(--line); }}
.lines {{ margin: 6px 0 0; color: var(--muted); font-size: 13px; }}
footer {{ margin-top: 36px; color: var(--muted); font-size: 13px; max-width: 78ch; }}
@media (max-width: 800px) {{
  .stats {{ grid-template-columns: 1fr 1fr; }}
  h1 {{ font-size: 28px; }}
}}
@media print {{
  body {{ background: white; }}
  .wrap {{ padding: 0; }}
}}
</style>
</head>
<body>
<div class="wrap">
<p class="kicker">APJ professional services</p>
<h1>Opportunity position</h1>
<p class="lead">{esc(_lead(scorecard))}</p>
<p class="sources">{_sources(opps, quotes, title_date)}</p>
{_stats(scorecard)}
<h2>By boat</h2>
<p class="note">Boat is the quote-line Territory, with the APJ- prefix removed. The closing export has no territory column, so a services opportunity with no quote lines stays Unassigned.</p>
{_sheet_warning(quotes, scorecard)}
{_boats(scorecard)}
<h2>No quote yet</h2>
<p class="note">A services opportunity in the closing export with no Services rows in the quote-line export. That is the missing primary quote.</p>
{_missing(scorecard)}
<h2>PS on a license or renewal quote</h2>
<p class="note">Direct License and Renewal are sales quotes that carry a PS product. They are not expected to have a services opportunity. Several lines on one opportunity are kept together.</p>
{_groups(scorecard.shadow, shadow=True)}
<h2>Services opportunities closing in this export</h2>
<p class="note">Joined to Services quote lines on Opportunity Name. Line amounts are summed.</p>
{_services(scorecard)}
<h2>Services quotes outside this closing export</h2>
<p class="note">Services quote lines whose opportunity is not in the closing file. The quote export is open lines, so these are often later periods rather than errors.</p>
{_groups(scorecard.outside_quarter, shadow=False)}
{_other(scorecard)}
<footer>
<p>Join key is Opportunity Name. These two exports do not include an opportunity id, so two opportunities with the same name would share quote lines.</p>
<p>Money uses the converted columns already on the reports. Nothing is revalued. {(esc(CONVERTED))}.</p>
<p>{_commit_note(scorecard)}</p>
</footer>
</div>
</body>
</html>
"""


def _lead(scorecard: Scorecard) -> str:
    count = len(scorecard.services)
    noun = "opportunity" if count == 1 else "opportunities"
    missing = scorecard.missing_quotes
    missing_verb = "has" if missing == 1 else "have"
    periods = ", ".join(scorecard.fiscal_periods)
    period_bit = f" Fiscal period {periods}." if periods else ""
    return (
        f"{count} services {noun} in the closing export, "
        f"{_money(scorecard.services_value)} services value "
        f"and {_money(scorecard.weighted)} weighted. "
        f"{missing} {missing_verb} no quote lines. "
        f"License and renewal quotes carry {_money(scorecard.shadow_value)} of PS.{period_bit}"
    )


def _stats(scorecard: Scorecard) -> str:
    cards = [
        (_money(scorecard.services_value), "Services value in the closing export", ""),
        (_money(scorecard.weighted), "Weighted revenue, as exported", ""),
        (str(scorecard.missing_quotes), "Services opportunities with no quote", "flag" if scorecard.missing_quotes else ""),
        (_money(scorecard.shadow_value), "PS on license and renewal quotes", "watch" if scorecard.shadow_value else ""),
    ]
    body = "".join(
        f'<div class="stat {kind}"><b>{esc(value)}</b><span>{esc(label)}</span></div>'
        for value, label, kind in cards
    )
    return f'<div class="stats">{body}</div>'


def _boats(scorecard: Scorecard) -> str:
    if not scorecard.boats:
        return '<p class="empty">No boats in this export.</p>'
    rows = []
    for boat in scorecard.boats:
        rows.append(
            "<tr>"
            f"<td>{esc(boat.boat)}</td>"
            f'<td class="num">{esc(_money_or_blank(boat.services_value))}</td>'
            f'<td class="num">{boat.opportunities}</td>'
            f'<td class="num">{boat.missing_quotes}</td>'
            f'<td class="num">{esc(_money_or_blank(boat.shadow_value))}</td>'
            f'<td class="num">{esc(_money_or_blank(boat.outside_value))}</td>'
            "</tr>"
        )
    return _table(
        [
            "Boat",
            "Closing services value",
            "Opportunities",
            "No quote",
            "PS on license or renewal",
            "Services quotes outside this file",
        ],
        rows,
        numeric={1, 2, 3, 4, 5},
    )


def _missing(scorecard: Scorecard) -> str:
    rows = [row for row in scorecard.services if row.missing_quote]
    if not rows:
        return '<p class="empty">Every services opportunity in this export has at least one quote line.</p>'
    body = []
    for row in rows:
        body.append(
            '<tr class="flag">'
            f"<td>{esc(row.account)}<div class='tag flag'>No quote</div></td>"
            f"<td>{esc(row.name)}</td>"
            f"<td>{esc(row.stage)}</td>"
            f'<td class="when">{esc(_date(row))}</td>'
            f"<td>{esc(row.fiscal_period)}</td>"
            f'<td class="num">{esc(_money(row.services_value))}</td>'
            f'<td class="num">{esc(_pct(row.probability))}</td>'
            f"<td>{esc(row.owner)}</td>"
            f'<td class="prose">{esc(row.status_note)}</td>'
            "</tr>"
        )
    return _table(
        ["Account", "Opportunity", "Stage", "Close", "Fiscal period", "Services value", "Probability", "Owner", "Status note"],
        body,
        numeric={5, 6},
    )


def _services(scorecard: Scorecard) -> str:
    if not scorecard.services:
        return '<p class="empty">The closing export has no opportunity rows.</p>'
    body = []
    for row in scorecard.services:
        klass = ' class="flag"' if row.missing_quote else ""
        quote_cell = "None" if row.missing_quote else _line_summary(row.lines, row.quote_total)
        dup = "<div class='tag flag'>Name is not unique</div>" if row.duplicate_name else ""
        body.append(
            f"<tr{klass}>"
            f"<td>{esc(row.account)}</td>"
            f"<td>{esc(row.name)}{dup}</td>"
            f"<td>{esc(row.boat)}</td>"
            f"<td>{esc(row.stage)}</td>"
            f'<td class="when">{esc(_date(row))}</td>'
            f"<td>{esc(row.fiscal_period)}</td>"
            f'<td class="num">{esc(_money(row.amount))}</td>'
            f'<td class="num">{esc(_money(row.services_value))}</td>'
            f'<td class="num">{esc(_money(row.weighted))}</td>'
            f"<td>{quote_cell}</td>"
            f"<td>{esc(row.owner)}</td>"
            "</tr>"
        )
    return _table(
        ["Account", "Opportunity", "Boat", "Stage", "Close", "Fiscal period", "Amount", "Services value", "Weighted", "Quote lines", "Owner"],
        body,
        numeric={6, 7, 8},
    )


def _groups(groups: list[QuoteGroup], shadow: bool) -> str:
    if not groups:
        message = (
            "No Direct License or Renewal PS lines in this export."
            if shadow
            else "Every Services quote line matches an opportunity in the closing export."
        )
        return f'<p class="empty">{esc(message)}</p>'
    body = []
    for group in groups:
        klass = ' class="watch"' if shadow else ""
        tags = []
        if shadow and group.in_services_book:
            tags.append("<div class='tag watch'>Also in the services book</div>")
        if group.negative_discount:
            tags.append("<div class='tag watch'>Negative discount</div>")
        body.append(
            f"<tr{klass}>"
            f"<td>{esc(group.record_type)}</td>"
            f"<td>{esc(group.account)}</td>"
            f"<td>{esc(group.name)}{''.join(tags)}</td>"
            f"<td>{esc(group.boat)}</td>"
            f"<td>{esc(group.stage)}</td>"
            f'<td class="when">{esc(_group_date(group))}</td>'
            f"<td>{esc(', '.join(group.quotes))}</td>"
            f'<td class="num">{esc(_money(group.net_total))}</td>'
            f"<td>{_line_summary(group.lines, None)}</td>"
            f"<td>{esc(group.owner)}</td>"
            "</tr>"
        )
    return _table(
        ["Record type", "Account", "Opportunity", "Boat", "Stage", "Close", "Quote", "Net total", "Lines", "Owner"],
        body,
        numeric={7},
    )


def _other(scorecard: Scorecard) -> str:
    if not scorecard.other:
        return ""
    types = ", ".join(sorted({group.record_type for group in scorecard.other}))
    return (
        "<h2>Other quote record types</h2>"
        f"<p class='note'>These record types are neither Services nor Direct License nor Renewal: {esc(types)}. They are listed so a new type is not dropped.</p>"
        + _groups(scorecard.other, shadow=False)
    )


def _line_summary(lines, total: float | None) -> str:
    bits = []
    for line in lines:
        discount = ""
        if line.discount is not None:
            discount = f" · {_pct(line.discount)} discount"
        family = f" · {line.family}" if line.family else ""
        bits.append(f"{esc(line.product_code)}{esc(family)}{esc(discount)} ({esc(line.line_name)})")
    detail = "<br>".join(bits)
    if total is None:
        return f'<div class="lines">{len(lines)} · {detail}</div>'
    return f'{esc(_money(total))}<div class="lines">{len(lines)} · {detail}</div>'


def _table(headers: list[str], rows: list[str], numeric: set[int]) -> str:
    head = "".join(
        f'<th class="{"num" if i in numeric else ""}">{esc(header)}</th>'
        for i, header in enumerate(headers)
    )
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def _sources(opps: Table, quotes: Table, title_date: str) -> str:
    opp_noun = "opportunity" if len(opps.rows) == 1 else "opportunities"
    line_noun = "line" if len(quotes.rows) == 1 else "lines"
    return (
        f"Closing export {esc(opps.path.name)} · sheet {esc(opps.sheet)} · {len(opps.rows)} {opp_noun}. "
        f"Quote lines {esc(quotes.path.name)} · sheet {esc(quotes.sheet)} · {len(quotes.rows)} {line_noun}. "
        f"Report date {esc(title_date)}."
    )


def _as_of_label(opps: Table, quotes: Table, as_of: date | None) -> str:
    if as_of is not None:
        return f"{as_of.day} {as_of.strftime('%b %Y')}"
    for table in (opps, quotes):
        found = _date_in_name(table.path.name)
        if found:
            return f"{found.day} {found.strftime('%b %Y')}"
    return "undated export"


def _date_in_name(name: str) -> date | None:
    import re

    match = re.search(r"(20\d{2})-(\d{2})-(\d{2})", name)
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


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


def _commit_note(scorecard: Scorecard) -> str:
    if scorecard.commit_values:
        listed = ", ".join(scorecard.commit_values)
        return f"The old commit column has values: {listed}. It is not used as the forecast split."
    return "The column “(old) Commit?” is blank on every closing row, so this export cannot split commit and upside."


def _date(row: ServiceOpportunity) -> str:
    if row.close is not None:
        return f"{row.close.day} {row.close.strftime('%b %Y')}"
    return row.close_raw or "—"


def _group_date(group: QuoteGroup) -> str:
    if group.close is not None:
        return f"{group.close.day} {group.close.strftime('%b %Y')}"
    return group.close_raw or "—"


def _money(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:,.2f}"


def _money_or_blank(value: float | None) -> str:
    if not value:
        return "—"
    return _money(value)


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%"


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)
