# APJ PS desk

Local opportunity scorecard. It reads two Salesforce tabular exports and opens a single page. No login, no write-back, and no model.

## What the two files are

**Closing this quarter** is the services-opportunity book maintained by the PS team.

**PS quote lines** has three opportunity record types:

- `Services` — quote lines for a services opportunity. Join on `Opportunity ID`. Several lines on one opportunity stay together. Names are not used to match.
- `Direct License` and `Renewal` — a sales quote that carries a PS product, usually with no services opportunity.
- A blank `Primary Quote` on a services opportunity is flagged: no primary quote yet.
- A `Primary Quote` with no lines in the quote-line export is listed separately. The quote exists, and this file has no PS lines for it.

Boat comes from the quote-line `Territory` (`APJ-ANZ` displays as ANZ). The closing export has no territory column, so an opportunity with no quote lines is Unassigned.

## Run

```bash
pip install -r requirements.txt
python -m psdesk build path/to/exports -o dist/index.html
```

Or name the files:

```bash
python -m psdesk build --opps closing.xlsx --quotes quote-lines.xlsx -o dist/index.html
```

`python -m psdesk serve path/to/exports` serves that page at `http://127.0.0.1:8765/index.html`.

The page is a local dashboard. Switch between the services book, license and renewal quotes, and services quotes that are not in the closing file. Filter by boat, fiscal period, stage, quote coverage, and account, or search opportunity name and account. Click a column heading to sort. Click a bar or a count to cut the table. Click a row to see its quote lines. The address bar keeps the current cut, so a link reopens the same view. The page does not call out to a network.

Close dates are compared with the report date. Today or earlier is due. The next 14 days are coming up. On the services book only, a status is expected weekly above 100,000, fortnightly above 50,000 through 100,000, and monthly from 0 through 50,000. No status date counts as overdue.

`fixtures/` holds the sanitized 20 Oct 2026 sample. `python -m pytest` checks the flags against it.

Money is the converted amount already on the report. The old commit column is shown only when it has values; in the sample it is blank, so there is no commit / upside split yet.
