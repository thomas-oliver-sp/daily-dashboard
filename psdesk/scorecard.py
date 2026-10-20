"""Turn the two exports into the opportunity position.

Services opportunities come from the closing report. Quote lines join to them
on Opportunity Name. These exports do not include an opportunity id.

A services opportunity with no Services quote lines has no primary quote yet.
Direct License and Renewal lines are PS sold on a license quote. Several lines
on one opportunity are one deal, not duplicates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from psdesk.columns import (
    OPP_ACCOUNT,
    OPP_AGE,
    OPP_AMOUNT,
    OPP_CLOSE,
    OPP_COMMIT,
    OPP_FISCAL,
    OPP_NAME,
    OPP_OWNER,
    OPP_PROBABILITY,
    OPP_RECURRING,
    OPP_RENEWAL,
    OPP_SERVICES_TYPE,
    OPP_SERVICES_VALUE,
    OPP_STAGE,
    OPP_STATUS,
    OPP_STATUS_DATE,
    OPP_WEIGHTED,
    QUOTE_ACCOUNT,
    QUOTE_CLOSE,
    QUOTE_DISCOUNT,
    QUOTE_FAMILY,
    QUOTE_LINE,
    QUOTE_NAME,
    QUOTE_NET,
    QUOTE_NUMBER,
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
    lines: list[QuoteLine] = field(default_factory=list)
    duplicate_name: bool = False

    @property
    def missing_quote(self) -> bool:
        return not self.lines

    @property
    def quote_total(self) -> float:
        return sum(line.net_total or 0 for line in self.lines)

    @property
    def boat(self) -> str:
        return _boat_of(self.lines)


@dataclass
class QuoteGroup:
    """Quote lines that share an opportunity name and record type."""

    record_type: str
    account: str
    name: str
    owner: str
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
    shadow_value: float
    outside_value: float


@dataclass
class Scorecard:
    services: list[ServiceOpportunity]
    shadow: list[QuoteGroup]
    outside_quarter: list[QuoteGroup]
    other: list[QuoteGroup]
    commit_values: list[str]
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
        buckets.setdefault((line.record_type, line.opportunity), []).append(line)
        if line.record_type == SERVICES_RECORD_TYPE:
            services_lines.setdefault(line.opportunity, []).append(line)

    name_counts: dict[str, int] = {}
    for row in opps.rows:
        name = _text(row.get(OPP_NAME))
        name_counts[name] = name_counts.get(name, 0) + 1

    services: list[ServiceOpportunity] = []
    service_names: set[str] = set()
    for row in opps.rows:
        item = _service_opp(row)
        item.lines = list(services_lines.get(item.name, []))
        item.duplicate_name = name_counts[item.name] > 1
        services.append(item)
        service_names.add(item.name)

    shadow: list[QuoteGroup] = []
    outside: list[QuoteGroup] = []
    other: list[QuoteGroup] = []
    for (record_type, name), lines in buckets.items():
        group = QuoteGroup(
            record_type=record_type,
            account=_first(lines, "account"),
            name=name,
            owner=_first(lines, "owner"),
            lines=lines,
            in_services_book=name in service_names,
        )
        if record_type in SHADOW_RECORD_TYPES:
            shadow.append(group)
        elif record_type == SERVICES_RECORD_TYPE and name not in service_names:
            outside.append(group)
        elif record_type != SERVICES_RECORD_TYPE:
            other.append(group)

    services.sort(key=lambda row: (row.close or date.max, row.name))
    shadow.sort(key=lambda row: (-row.net_total, row.name))
    outside.sort(key=lambda row: (row.close or date.max, row.name))
    other.sort(key=lambda row: row.name)

    commits = _unique(_text(row.get(OPP_COMMIT)) for row in opps.rows)
    return Scorecard(
        services=services,
        shadow=shadow,
        outside_quarter=outside,
        other=other,
        commit_values=[value for value in commits if value],
        boats=_boats(services, shadow, outside),
    )


def boat_label(territory: str) -> str:
    """APJ-ANZ is the ANZ boat. A blank territory is unassigned."""
    text = territory.strip()
    if not text:
        return UNASSIGNED
    if text.upper().startswith("APJ-"):
        return text[4:]
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
        fiscal_period=_text(row.get(OPP_FISCAL)),
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
        recurring=_text(row.get(OPP_RECURRING)),
        renewal=_yes_no(row.get(OPP_RENEWAL)),
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
    if text.casefold() in {"true", "yes", "y"}:
        return "Yes"
    if text.casefold() in {"false", "no", "n"}:
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
    """Excel stores 90% as 0.9. A plain 90, or -49.5, in a csv is already points."""
    number = _number(value)
    if number is None:
        return None
    if abs(number) > 1:
        return number / 100
    return number


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
