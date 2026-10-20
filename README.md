# APJ PS desk

Local opportunity scorecard. It reads two Salesforce tabular exports and opens a single page. No login, no write-back, and no model.

## What the two files are

**Closing this quarter** is the services-opportunity book maintained by the PS team.

**PS quote lines** has three opportunity record types:

- `Services` — quote lines for a services opportunity. Join on `Opportunity Name`. Several lines on one opportunity stay together.
- `Direct License` and `Renewal` — a sales quote that carries a PS product, usually with no services opportunity.
- A services opportunity with no `Services` quote lines is flagged: no primary quote yet.

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

`fixtures/` holds the sanitized 20 Oct 2026 sample. `python -m pytest` checks the flags against it.

Money is the converted amount already on the report. The old commit column is shown only when it has values; in the sample it is blank, so there is no commit / upside split yet.
