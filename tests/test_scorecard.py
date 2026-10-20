from datetime import date
from pathlib import Path

import openpyxl
import pytest

from psdesk.columns import (
    OPP_ACCOUNT,
    OPP_CLOSE,
    OPP_FISCAL,
    OPP_ID,
    OPP_NAME,
    OPP_OWNER,
    OPP_PRIMARY,
    OPP_PROBABILITY,
    OPP_SERVICES_VALUE,
    OPP_STAGE,
    OPP_WEIGHTED,
    QUOTE_ACCOUNT,
    QUOTE_CLOSE,
    QUOTE_FISCAL,
    QUOTE_LINE,
    QUOTE_NAME,
    QUOTE_NET,
    QUOTE_NUMBER,
    QUOTE_OPP_ID,
    QUOTE_OWNER,
    QUOTE_PRODUCT,
    QUOTE_RECORD_TYPE,
    QUOTE_STAGE,
    QUOTE_TERRITORY,
)
from psdesk.load import ReportError, load_directory, load_table
from psdesk.payload import to_payload
from psdesk.render import render
from psdesk.scorecard import build_scorecard
from psdesk.__main__ import main

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


def _scorecard():
    opps, quotes = load_directory(FIXTURES)
    return build_scorecard(opps, quotes), opps, quotes


def test_sample_flags_the_services_opp_with_no_quote():
    card, _, _ = _scorecard()
    assert len(card.services) == 1
    opp = card.services[0]
    assert opp.name == "SomeUni-Apps"
    assert opp.missing_quote is True
    assert opp.boat == "Unassigned"
    assert opp.services_value == pytest.approx(163102.68)
    assert opp.weighted == pytest.approx(146792.412)
    assert opp.probability == pytest.approx(0.9)
    assert opp.close == date(2026, 10, 30)
    assert opp.fiscal_period == "FY2027 Q3"
    assert opp.primary_quote == ""
    assert opp.unlisted_quote is False
    assert card.currency == "USD"
    assert opp.renewal == "No"
    assert card.missing_quotes == 1
    assert card.commit_values == []
    by_boat = {row.boat: row for row in card.boats}
    assert by_boat["Unassigned"].missing_quotes == 1
    assert by_boat["Unassigned"].services_value == pytest.approx(163102.68)
    assert by_boat["ANZ"].shadow_value == pytest.approx(1105018.1059068)
    assert by_boat["ASEAN"].shadow_value == pytest.approx(8000)
    assert by_boat["ASEAN"].outside_value == pytest.approx(166200)


def test_sample_separates_license_ps_from_services_quotes():
    card, _, _ = _scorecard()
    shadow = {(row.record_type, row.name): row for row in card.shadow}
    assert set(shadow) == {
        ("Direct License", "Bank-ISC New"),
        ("Renewal", "Company-Renewal"),
    }
    license_deal = shadow[("Direct License", "Bank-ISC New")]
    assert license_deal.boat == "ASEAN"
    assert license_deal.net_total == pytest.approx(8000)
    assert license_deal.in_services_book is False
    assert license_deal.quotes == ["Q-000001"]

    renewal = shadow[("Renewal", "Company-Renewal")]
    assert renewal.boat == "ANZ"
    assert renewal.net_total == pytest.approx(1105018.1059068)
    assert renewal.negative_discount is True

    assert len(card.outside_quarter) == 1
    outside = card.outside_quarter[0]
    assert outside.name == "Something-PS Phase 1"
    assert outside.record_type == "Services"
    assert outside.boat == "ASEAN"
    assert outside.net_total == pytest.approx(166200)
    assert outside.lines[0].product_code == "PS-STAFF-AUG-SM"
    assert card.other == []


def test_multiple_services_lines_sum_onto_one_opportunity(tmp_path):
    opps = tmp_path / "closing.xlsx"
    quotes = tmp_path / "quotes.xlsx"
    _write(
        opps,
        _opp_header(),
        [_opp("Acme", "Acme-PS", 100, services=80, weighted=40)],
    )
    _write(
        quotes,
        _quote_header(),
        [
            _quote("Services", "Acme", "Acme-PS", "QL-1", "PS-A", 30, "APJ-Japan"),
            _quote("Services", "Acme", "Acme-PS", "QL-2", "PS-B", 50, "APJ-Japan"),
            _quote("Direct License", "Acme", "Acme-PS", "QL-3", "PS-C", 9, "APJ-Japan"),
        ],
    )
    card = build_scorecard(load_table(opps), load_table(quotes))
    assert card.missing_quotes == 0
    assert card.services[0].quote_total == pytest.approx(80)
    assert card.services[0].boat == "Japan"
    assert len(card.services[0].lines) == 2
    assert card.shadow[0].in_services_book is True
    assert card.outside_quarter == []


def test_same_name_does_not_join_and_ids_do(tmp_path):
    opps = tmp_path / "closing.csv"
    quotes = tmp_path / "quotes.csv"
    _write_csv(opps, _opp_header(), [
        _opp("Customer1", "Opp1", 10, opp_id="006AAA000000001", primary=""),
        _opp("Customer9", "Opp1", 20, opp_id="006AAA000000002", primary="Q-9"),
    ])
    _write_csv(quotes, _quote_header(), [
        _quote("Services", "OtherName", "Different", "QL-1", "PS-A", 10, "APJ-KR", opp_id="006AAA000000001"),
    ])
    card = build_scorecard(load_table(opps), load_table(quotes))
    linked = next(row for row in card.services if row.opportunity_id == "006AAA000000001")
    other = next(row for row in card.services if row.opportunity_id == "006AAA000000002")
    assert linked.quote_total == pytest.approx(10)
    assert linked.boat == "Korea"
    assert linked.missing_quote is False
    assert other.unlisted_quote is True
    assert other.lines == []
    assert card.outside_quarter == []


def test_duplicate_opportunity_ids_are_marked(tmp_path):
    opps = tmp_path / "closing.csv"
    quotes = tmp_path / "quotes.csv"
    _write_csv(opps, _opp_header(), [
        _opp("One", "First", 10, opp_id="006SAME00000001"),
        _opp("Two", "Second", 20, opp_id="006SAME00000001"),
    ])
    _write_csv(quotes, _quote_header(), [])
    card = build_scorecard(load_table(opps), load_table(quotes))
    assert all(row.duplicate_id for row in card.services)


def test_csv_percents_and_fiscal_labels():
    from psdesk.scorecard import _probability, fiscal_label

    assert _probability("1") == pytest.approx(0.01)
    assert _probability("20") == pytest.approx(0.20)
    assert _probability("33.333") == pytest.approx(0.33333)
    assert _probability(0.9) == pytest.approx(0.9)
    assert fiscal_label("Q4-2027") == "FY2027 Q4"
    assert fiscal_label("FY2027 Q3") == "FY2027 Q3"


def test_unknown_record_type_is_kept(tmp_path):
    opps = tmp_path / "closing.csv"
    quotes = tmp_path / "quotes.csv"
    _write_csv(opps, _opp_header(), [_opp("Acme", "Acme-PS", 10)])
    _write_csv(quotes, _quote_header(), [
        _quote("Partner", "Acme", "Other-Deal", "QL-9", "PS-Z", 15, "APJ-India"),
    ])
    card = build_scorecard(load_table(opps), load_table(quotes))
    assert card.other[0].record_type == "Partner"
    assert card.other[0].boat == "India"
    assert card.shadow == []
    from psdesk.payload import to_payload

    payload = to_payload(card, load_table(opps), load_table(quotes), None)
    assert payload["other"][0]["recordType"] == "Partner"
    assert payload["other"][0]["boat"] == "India"
    assert payload["shadow"] == []


def test_missing_column_names_the_file(tmp_path):
    from psdesk.load import require_reports

    unnamed = tmp_path / "empty.csv"
    unnamed.write_text("Foo,Bar\n1,2\n", encoding="utf-8")
    with pytest.raises(ReportError, match="empty.csv"):
        load_table(unnamed)

    path = tmp_path / "notes.csv"
    path.write_text("Opportunity Name,Notes\nDeal,hello\n", encoding="utf-8")
    quotes = tmp_path / "q.csv"
    _write_csv(quotes, _quote_header(), [])
    with pytest.raises(ReportError, match="notes.csv"):
        require_reports(load_table(path), load_table(quotes))


def test_close_pressure_and_status_cadence():
    from psdesk.attention import close_timing, status_band, status_fresh

    as_of = date(2026, 10, 20)
    assert close_timing(as_of, as_of) == "due"
    assert close_timing(date(2026, 10, 19), as_of) == "due"
    assert close_timing(date(2026, 10, 21), as_of) == "soon"
    assert close_timing(date(2026, 11, 3), as_of) == "soon"
    assert close_timing(date(2026, 11, 4), as_of) == "later"
    assert close_timing(None, as_of) == ""

    assert status_band(0) == "monthly"
    assert status_band(50_000) == "monthly"
    assert status_band(50_000.01) == "fortnightly"
    assert status_band(100_000) == "fortnightly"
    assert status_band(100_000.01) == "weekly"
    assert status_band(-1) == ""
    assert status_band(None) == ""

    assert status_fresh(10_000, date(2026, 9, 20), as_of) is True
    assert status_fresh(10_000, date(2026, 9, 19), as_of) is False
    assert status_fresh(10_000, None, as_of) is False
    assert status_fresh(75_000, date(2026, 10, 6), as_of) is True
    assert status_fresh(75_000, date(2026, 10, 5), as_of) is False
    assert status_fresh(150_000, date(2026, 10, 13), as_of) is True
    assert status_fresh(150_000, date(2026, 10, 12), as_of) is False
    assert status_fresh(-5, date(2026, 1, 1), as_of) is None

    card, opps, quotes = _scorecard()
    payload = to_payload(card, opps, quotes, as_of)
    service = payload["services"][0]
    assert service["closeTiming"] == "soon"
    assert service["statusBand"] == "weekly"
    assert service["statusAge"] == 6
    assert service["statusFresh"] is True
    assert payload["asOfIso"] == "2026-10-20"


def test_page_escapes_status_notes_and_shows_the_sample_flag(tmp_path):
    card, opps, quotes = _scorecard()
    card.services[0].status_note = "<script>alert(1)</script>"
    page = render(card, opps, quotes, date(2026, 10, 20))
    assert "<script>alert" not in page
    assert r"\u003cscript>alert(1)\u003c/script>" in page
    assert 'id="ps-data"' in page
    assert "SomeUni-Apps" in page
    assert "Bank-ISC New" in page
    assert "Company-Renewal" in page
    assert "Something-PS Phase 1" in page
    assert "No primary quote" in page
    payload = _page_payload(page)
    assert payload["services"][0]["coverage"] == "missing"
    assert payload["services"][0]["statusNote"] == "<script>alert(1)</script>"
    assert any(row["name"] == "Company-Renewal" for row in payload["shadow"])
    assert any(row["name"] == "Something-PS Phase 1" for row in payload["outside"])
    out = tmp_path / "index.html"
    assert main(["build", str(FIXTURES), "-o", str(out), "--as-of", "2026-10-20"]) == 0
    written = out.read_text(encoding="utf-8")
    assert "20 Oct 2026" in written
    assert "1 opportunity." in written
    assert "1,105,018.11" in written or "1105018.1059068" in written


def _page_payload(page: str) -> dict:
    import json
    import re

    match = re.search(r'<script id="ps-data" type="application/json">(.*?)</script>', page, re.S)
    assert match
    return json.loads(match.group(1))


def _opp_header():
    return [
        OPP_ACCOUNT, OPP_NAME, OPP_SERVICES_VALUE, OPP_WEIGHTED, OPP_PROBABILITY,
        OPP_STAGE, OPP_FISCAL, OPP_CLOSE, OPP_ID, OPP_PRIMARY, OPP_OWNER,
    ]


def _quote_header():
    return [
        QUOTE_RECORD_TYPE, QUOTE_ACCOUNT, QUOTE_NAME, QUOTE_OWNER, QUOTE_NUMBER,
        QUOTE_LINE, QUOTE_PRODUCT, QUOTE_NET, QUOTE_STAGE, QUOTE_CLOSE, QUOTE_TERRITORY,
        QUOTE_OPP_ID, QUOTE_FISCAL,
    ]


def _opp(account, name, amount, services=None, weighted=None, opp_id="006FAKE000000099", primary="Q-1"):
    services = amount if services is None else services
    weighted = services if weighted is None else weighted
    return [account, name, services, weighted, "50", "60-Proposal", "Q3-2027", "10/30/2026", opp_id, primary, "Owner"]


def _quote(record_type, account, name, line, product, net, territory, opp_id="006FAKE000000099"):
    return [record_type, account, name, "Owner", "Q-1", line, product, net, "60-Proposal", "11/1/2026", territory, opp_id, "FY2027 Q3"]


def _write(path: Path, headers, rows):
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    book.save(path)


def _write_csv(path: Path, headers, rows):
    import csv

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
