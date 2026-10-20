"""Turn the two exports into the opportunity position.

Services opportunities come from the closing report. Quote lines join to them
on Opportunity ID. Names are display-only, because a sanitized extract can
obscure the same deal differently in each file.

A services opportunity with a blank Primary Quote has no primary quote yet.
One whose Primary Quote is set, but which has no Services lines in the
quote-line export, has a quote the line report does not contain.
Direct License and Renewal lines are PS sold on a license quote. Several
lines on one opportunity id are one deal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

from psdesk.columns import (
    OPP_ACCOUNT,
    OPP_AGE,
    OPP_AGREEMENT,
    OPP_AMOUNT,
    OPP_BOAT,
    OPP_CLOSE,
    OPP_COMMIT,
    OPP_FISCAL,
    OPP_ID,
    OPP_NAME,
    OPP_OWNER,
    OPP_PRIMARY,
    OPP_PROBABILITY,
    OPP_RECURRING,
    OPP_RENEWAL,
    OPP_SERVICES_CURRENCY,
    OPP_SERVICES_TYPE,
    OPP_SERVICES_VALUE,
    OPP_STAGE,
    OPP_STATUS,
    OPP_STATUS_DATE,
    OPP_TERRITORY,
    OPP_WEIGHTED,
    QUOTE_ACCOUNT,
    QUOTE_CLOSE,
    QUOTE_DISCOUNT,
    QUOTE_FAMILY,
    QUOTE_FISCAL,
    QUOTE_LINE,
    QUOTE_NAME,
    QUOTE_NET,
    QUOTE_NET_CURRENCY,
    QUOTE_NUMBER,
    QUOTE_OPP_ID,
    QUOTE_OPP_STATUS,
    QUOTE_OWNER,
    QUOTE_PRODUCT,
    QUOTE_QTY,
    QUOTE_RECORD_TYPE,
    QUOTE_SERVICES_TERRITORY,
    QUOTE_STAGE,
    QUOTE_TERRITORY,
    SERVICES_RECORD_TYPE,
    SHADOW_RECORD_TYPES,
)
from psdesk.load import Table

UNASSIGNED = "Unassigned"


@dataclass
class QuoteLine:
    record_type: str
    account: str
    opportunity: str
    owner: str
    quote: str
    line_name: str
    product_code: str
    family: str
    quantity: float | None
    net_total: float | None
    discount: float | None
    stage: str
    close: date | None
    close_raw: str
    territory: str
    services_territory: str
    opportunity_status: str
    opportunity_id: str
    currency: str
    fiscal_period: str


@dataclass
class ServiceOpportunity:
    account: str
    name: str
    owner: str
    stage: str
    fiscal_period: str
    close: date | None
    close_raw: str
    amount: float | None
    services_value: float | None
    weighted: float | None
    probability: float | None
    services_type: str
    status_note: str
    status_date: str
    age: str
    commit: str
    recurring: str
    renewal: str
    opportunity_id: str
    primary_quote: str
    currency: str
    agreement_type: str
    territory: str
    lines: list[QuoteLine] = field(default_factory=list)
    duplicate_id: bool = False

    @property
    def missing_quote(self) -> bool:
        return not self.primary_quote and not self.lines

    @property
    def unlisted_quote(self) -> bool:
        return bool(self.primary_quote) and not self.lines

    @property
    def quote_mismatch(self) -> bool:
        if not self.primary_quote or not self.lines:
            return False
        return any(line.quote and line.quote != self.primary_quote for line in self.lines)

    @property
    def quote_total(self) -> float:
        return sum(line.net_total or 0 for line in self.lines)

    @property
    def boat(self) -> str:
        own = boat_label(self.territory)
        if own != UNASSIGNED:
            return own
        return _boat_of(self.lines)

    @property
    def band(self) -> str:
        return stage_band(self.stage)


@dataclass
class QuoteGroup:
    """Quote lines that share an opportunity id and record type."""

    record_type: str
    account: str
    name: str
    owner: str
    opportunity_id: str
    lines: list[QuoteLine]
    in_services_book: bool = False

    @property
    def net_total(self) -> float:
        return sum(line.net_total or 0 for line in self.lines)

    @property
    def boat(self) -> str:
        return _boat_of(self.lines)

    @property
    def stage(self) -> str:
        return _first(self.lines, "stage")

    @property
    def close(self) -> date | None:
        dated = [line.close for line in self.lines if line.close is not None]
        return min(dated) if dated else None

    @property
    def close_raw(self) -> str:
        return _first(self.lines, "close_raw")

    @property
    def quotes(self) -> list[str]:
        seen: list[str] = []
        for line in self.lines:
            if line.quote and line.quote not in seen:
                seen.append(line.quote)
        return seen

    @property
    def negative_discount(self) -> bool:
        return any(line.discount is not None and line.discount < 0 for line in self.lines)


@dataclass
class BoatRollup:
    boat: str
    services_value: float
    opportunities: int
    missing_quotes: int
    unlisted_quotes: int
    shadow_value: float
    outside_value: float


@dataclass
class Scorecard:
    services: list[ServiceOpportunity]
    shadow: list[QuoteGroup]
    outside_quarter: list[QuoteGroup]
    other: list[QuoteGroup]
    commit_values: list[str]
    commit_column: bool
    agreement_types: list[str]
    currency: str
    boats: list[BoatRollup]

    @property
    def services_value(self) -> float:
        return sum(row.services_value or 0 for row in self.services)

    @property
    def weighted(self) -> float:
        return sum(row.weighted or 0 for row in self.services)

    @property
    def amount(self) -> float:
        return sum(row.amount or 0 for row in self.services)

    @property
    def missing_quotes(self) -> int:
        return sum(1 for row in self.services if row.missing_quote)

    @property
    def unlisted_quotes(self) -> int:
        return sum(1 for row in self.services if row.unlisted_quote)

    @property
    def shadow_value(self) -> float:
        return sum(row.net_total for row in self.shadow)

    @property
    def fiscal_periods(self) -> list[str]:
        return _unique(row.fiscal_period for row in self.services if row.fiscal_period)


def build_scorecard(opps: Table, quotes: Table) -> Scorecard:
    quote_lines = [_quote_line(row) for row in quotes.rows]
    services_lines: dict[str, list[QuoteLine]] = {}
    buckets: dict[tuple[str, str], list[QuoteLine]] = {}
    for line in quote_lines:
        key = line.opportunity_id or f"(no id) {line.line_name}"
        buckets.setdefault((line.record_type, key), []).append(line)
        if line.record_type == SERVICES_RECORD_TYPE and line.opportunity_id:
            services_lines.setdefault(line.opportunity_id, []).append(line)

    id_counts: dict[str, int] = {}
    for row in opps.rows:
        opp_id = _text(row.get(OPP_ID))
        if opp_id:
            id_counts[opp_id] = id_counts.get(opp_id, 0) + 1

    services: list[ServiceOpportunity] = []
    service_ids: set[str] = set()
    for row in opps.rows:
        item = _service_opp(row)
        if item.opportunity_id:
            item.lines = list(services_lines.get(item.opportunity_id, []))
            item.duplicate_id = id_counts.get(item.opportunity_id, 0) > 1
            service_ids.add(item.opportunity_id)
        services.append(item)

    shadow: list[QuoteGroup] = []
    outside: list[QuoteGroup] = []
    other: list[QuoteGroup] = []
    for (record_type, opp_id), lines in buckets.items():
        group = QuoteGroup(
            record_type=record_type,
            account=_first(lines, "account"),
            name=_first(lines, "opportunity"),
            owner=_first(lines, "owner"),
            opportunity_id=opp_id,
            lines=lines,
            in_services_book=opp_id in service_ids,
        )
        if record_type in SHADOW_RECORD_TYPES:
            shadow.append(group)
        elif record_type == SERVICES_RECORD_TYPE and opp_id not in service_ids:
            outside.append(group)
        elif record_type != SERVICES_RECORD_TYPE:
            other.append(group)

    services.sort(key=lambda row: (_fiscal_sort(row.fiscal_period), row.close or date.max, row.name))
    shadow.sort(key=lambda row: (-row.net_total, row.name))
    outside.sort(key=lambda row: (row.close or date.max, row.name))
    other.sort(key=lambda row: row.name)

    commits = _unique(_text(row.get(OPP_COMMIT)) for row in opps.rows) if OPP_COMMIT in opps.headers else []
    agreements = _unique(row.agreement_type for row in services)
    return Scorecard(
        services=services,
        shadow=shadow,
        outside_quarter=outside,
        other=other,
        commit_values=[value for value in commits if value],
        commit_column=OPP_COMMIT in opps.headers,
        agreement_types=agreements,
        currency=_one_currency(services, quote_lines),
        boats=_boats(services, shadow, outside),
    )


_BOAT_NAMES = {
    "ANZ": "ANZ",
    "ASEAN": "ASEAN",
    "JAPAN": "Japan",
    "KR": "Korea",
    "INDIA": "India",
    "HKTM": "HKTM",
}


def boat_label(territory: str) -> str:
    """APJ-ANZ is the ANZ boat. A blank territory is unassigned."""
    text = territory.strip()
    if not text:
        return UNASSIGNED
    suffix = text[4:] if text.upper().startswith("APJ-") else text
    return _BOAT_NAMES.get(suffix.upper(), suffix)


def stage_band(stage: str) -> str:
    """Stage 80 and above is forecast. Anything lower is pipeline."""
    match = re.match(r"\s*(\d+)", stage or "")
    if match and int(match.group(1)) >= 80:
        return "forecast"
    return "pipeline"


def fiscal_label(value: str) -> str:
    """Q4-2027 and FY2027 Q4 are the same period."""
    text = value.strip()
    match = re.fullmatch(r"Q([1-4])-(\d{4})", text)
    if match:
        return f"FY{match.group(2)} Q{match.group(1)}"
    match = re.fullmatch(r"FY(\d{4})\s+Q([1-4])", text, re.IGNORECASE)
    if match:
        return f"FY{match.group(1)} Q{match.group(2)}"
    return text


def _boats(
    services: list[ServiceOpportunity],
    shadow: list[QuoteGroup],
    outside: list[QuoteGroup],
) -> list[BoatRollup]:
    names: list[str] = []
    for row in [*services, *shadow, *outside]:
        if row.boat not in names:
            names.append(row.boat)
    rollups: list[BoatRollup] = []
    names.sort(key=lambda name: (name in {UNASSIGNED, "Mixed"}, name))
    for name in names:
        own = [row for row in services if row.boat == name]
        shaded = [row for row in shadow if row.boat == name]
        later = [row for row in outside if row.boat == name]
        rollups.append(
            BoatRollup(
                boat=name,
                services_value=sum(row.services_value or 0 for row in own),
                opportunities=len(own),
                missing_quotes=sum(1 for row in own if row.missing_quote),
                unlisted_quotes=sum(1 for row in own if row.unlisted_quote),
                shadow_value=sum(row.net_total for row in shaded),
                outside_value=sum(row.net_total for row in later),
            )
        )
    return rollups


def _service_opp(row: dict[str, object]) -> ServiceOpportunity:
    close_raw = _text(row.get(OPP_CLOSE))
    return ServiceOpportunity(
        account=_text(row.get(OPP_ACCOUNT)),
        name=_text(row.get(OPP_NAME)),
        owner=_text(row.get(OPP_OWNER)),
        stage=_text(row.get(OPP_STAGE)),
        fiscal_period=fiscal_label(_text(row.get(OPP_FISCAL))),
        close=_parse_date(row.get(OPP_CLOSE)),
        close_raw=close_raw,
        amount=_number(row.get(OPP_AMOUNT)),
        services_value=_number(row.get(OPP_SERVICES_VALUE)),
        weighted=_number(row.get(OPP_WEIGHTED)),
        probability=_probability(row.get(OPP_PROBABILITY)),
        services_type=_text(row.get(OPP_SERVICES_TYPE)),
        status_note=_text(row.get(OPP_STATUS)),
        status_date=_text(row.get(OPP_STATUS_DATE)),
        age=_text(row.get(OPP_AGE)),
        commit=_text(row.get(OPP_COMMIT)),
        recurring=_yes_no(row.get(OPP_RECURRING)),
        renewal=_yes_no(row.get(OPP_RENEWAL)),
        opportunity_id=_text(row.get(OPP_ID)),
        primary_quote=_text(row.get(OPP_PRIMARY)),
        currency=_text(row.get(OPP_SERVICES_CURRENCY)),
        agreement_type=_text(row.get(OPP_AGREEMENT)),
        territory=_text(row.get(OPP_TERRITORY)) or _text(row.get(OPP_BOAT)),
    )


def _quote_line(row: dict[str, object]) -> QuoteLine:
    close_raw = _text(row.get(QUOTE_CLOSE))
    return QuoteLine(
        record_type=_text(row.get(QUOTE_RECORD_TYPE)),
        account=_text(row.get(QUOTE_ACCOUNT)),
        opportunity=_text(row.get(QUOTE_NAME)),
        owner=_text(row.get(QUOTE_OWNER)),
        quote=_text(row.get(QUOTE_NUMBER)),
        line_name=_text(row.get(QUOTE_LINE)),
        product_code=_text(row.get(QUOTE_PRODUCT)),
        family=_text(row.get(QUOTE_FAMILY)),
        quantity=_number(row.get(QUOTE_QTY)),
        net_total=_number(row.get(QUOTE_NET)),
        discount=_probability(row.get(QUOTE_DISCOUNT)),
        stage=_text(row.get(QUOTE_STAGE)),
        close=_parse_date(row.get(QUOTE_CLOSE)),
        close_raw=close_raw,
        territory=_text(row.get(QUOTE_TERRITORY)),
        services_territory=_text(row.get(QUOTE_SERVICES_TERRITORY)),
        opportunity_status=_text(row.get(QUOTE_OPP_STATUS)),
        opportunity_id=_text(row.get(QUOTE_OPP_ID)),
        currency=_text(row.get(QUOTE_NET_CURRENCY)),
        fiscal_period=fiscal_label(_text(row.get(QUOTE_FISCAL))),
    )


def _boat_of(lines: list[QuoteLine]) -> str:
    boats = []
    for line in lines:
        label = boat_label(line.territory)
        if label != UNASSIGNED and label not in boats:
            boats.append(label)
    if not boats:
        return UNASSIGNED
    if len(boats) == 1:
        return boats[0]
    return "Mixed"


def _first(lines: list[QuoteLine], attr: str) -> str:
    for line in lines:
        value = getattr(line, attr)
        if value:
            return str(value)
    return ""


def _unique(values) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _yes_no(value: object) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    text = _text(value)
    if text.casefold() in {"true", "yes", "y", "1"}:
        return "Yes"
    if text.casefold() in {"false", "no", "n", "0"}:
        return "No"
    return text


def _number(value: object) -> float | None:
    if value is None or value is False or value is True:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("$", "")
    if not text or text in {"-", "—"}:
        return None
    percent = text.endswith("%")
    if percent:
        text = text[:-1].strip()
    try:
        number = float(text)
    except ValueError:
        return None
    return number / 100 if percent else number


def _probability(value: object) -> float | None:
    """Excel stores 90% as 0.9. A Salesforce csv stores it as 90, or 1 for 1%."""
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text or text in {"-", "—"}:
            return None
        if text.endswith("%"):
            text = text[:-1].strip()
        try:
            return float(text) / 100
        except ValueError:
            return None
    number = _number(value)
    if number is None:
        return None
    if abs(number) > 1:
        return number / 100
    return number


def _fiscal_sort(label: str) -> tuple[int, int, str]:
    match = re.fullmatch(r"FY(\d{4}) Q([1-4])", label)
    if match:
        return (int(match.group(1)), int(match.group(2)), label)
    return (9999, 9, label)


def _one_currency(services: list[ServiceOpportunity], lines: list[QuoteLine]) -> str:
    codes = _unique(
        [row.currency for row in services]
        + [line.currency for line in lines]
    )
    if len(codes) == 1:
        return codes[0]
    return ""


def _parse_date(value: object) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None
