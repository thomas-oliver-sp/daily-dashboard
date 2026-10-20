"""JSON the dashboard reads. Names stay display-only; the join already happened."""

from __future__ import annotations

import re
from datetime import date

from psdesk.attention import SOON_DAYS, close_timing, status_age, status_band, status_fresh, status_limit
from psdesk.load import Table
from psdesk.scorecard import QuoteGroup, QuoteLine, Scorecard, ServiceOpportunity, _parse_date


def to_payload(scorecard: Scorecard, opps: Table, quotes: Table, as_of: date | None) -> dict:
    clock = _report_date(opps, quotes, as_of)
    return {
        "asOf": _as_of_label(clock),
        "asOfIso": clock.isoformat(),
        "soonDays": SOON_DAYS,
        "currency": scorecard.currency,
        "sources": _sources(opps, quotes),
        "agreement": scorecard.agreement_types[0] if len(scorecard.agreement_types) == 1 else "",
        "services": [_service(row, clock) for row in scorecard.services],
        "shadow": [_group(row, clock) for row in scorecard.shadow],
        "outside": [_group(row, clock) for row in scorecard.outside_quarter],
        "other": [_group(row, clock) for row in scorecard.other],
    }


def _service(row: ServiceOpportunity, as_of: date) -> dict:
    if row.missing_quote:
        coverage = "missing"
    elif row.unlisted_quote:
        coverage = "unlisted"
    else:
        coverage = "linked"
    status = _parse_date(row.status_date)
    band = status_band(row.services_value)
    return {
        "id": row.opportunity_id,
        "account": row.account,
        "name": row.name,
        "owner": row.owner,
        "boat": row.boat,
        "stage": row.stage,
        "band": row.band,
        "fiscal": row.fiscal_period,
        "close": _close(row.close, row.close_raw),
        "closeIso": row.close.isoformat() if row.close else "",
        "closeTiming": close_timing(row.close, as_of),
        "servicesValue": row.services_value,
        "weighted": row.weighted,
        "probability": row.probability,
        "servicesType": row.services_type,
        "statusNote": row.status_note,
        "statusDate": _close(status, row.status_date),
        "statusIso": status.isoformat() if status else "",
        "statusAge": status_age(status, as_of),
        "statusBand": band,
        "statusLimit": status_limit(band),
        "statusFresh": status_fresh(row.services_value, status, as_of),
        "age": row.age,
        "primaryQuote": row.primary_quote,
        "quoteTotal": row.quote_total,
        "coverage": coverage,
        "duplicateId": row.duplicate_id,
        "quoteMismatch": row.quote_mismatch,
        "lines": [_line(line) for line in row.lines],
    }


def _group(row: QuoteGroup, as_of: date) -> dict:
    fiscals = []
    for line in row.lines:
        if line.fiscal_period and line.fiscal_period not in fiscals:
            fiscals.append(line.fiscal_period)
    return {
        "id": row.opportunity_id,
        "recordType": row.record_type,
        "account": row.account,
        "name": row.name,
        "owner": row.owner,
        "boat": row.boat,
        "stage": row.stage,
        "fiscal": fiscals[0] if len(fiscals) == 1 else ", ".join(fiscals),
        "close": _close(row.close, row.close_raw),
        "closeIso": row.close.isoformat() if row.close else "",
        "closeTiming": close_timing(row.close, as_of),
        "net": row.net_total,
        "quotes": row.quotes,
        "inServicesBook": row.in_services_book,
        "negativeDiscount": row.negative_discount,
        "lines": [_line(line) for line in row.lines],
    }


def _line(line: QuoteLine) -> dict:
    return {
        "product": line.product_code,
        "family": line.family,
        "line": line.line_name,
        "quote": line.quote,
        "net": line.net_total,
        "discount": line.discount,
        "qty": line.quantity,
    }


def _close(value: date | None, raw: str) -> str:
    if value is not None:
        return f"{value.day} {value.strftime('%b %Y')}"
    return raw or ""


def _sources(opps: Table, quotes: Table) -> str:
    opp_noun = "opportunity" if len(opps.rows) == 1 else "opportunities"
    line_noun = "line" if len(quotes.rows) == 1 else "lines"
    return (
        f"{opps.path.name} · {opps.sheet} · {len(opps.rows)} {opp_noun}. "
        f"{quotes.path.name} · {quotes.sheet} · {len(quotes.rows)} {line_noun}."
    )


def _report_date(opps: Table, quotes: Table, as_of: date | None) -> date:
    if as_of is not None:
        return as_of
    for table in (opps, quotes):
        found = _date_in_name(table.path.name)
        if found:
            return found
    return date.today()


def _as_of_label(clock: date) -> str:
    return f"{clock.day} {clock.strftime('%b %Y')}"


def _date_in_name(name: str) -> date | None:
    match = re.search(r"(20\d{2})-(\d{2})-(\d{2})", name)
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None
