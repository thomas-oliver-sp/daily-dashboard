# APJ PS desk

Local opportunity scorecard. It reads two Salesforce tabular exports and opens a single page. No login, no write-back, and no model.

## What the two files are

**Closing this quarter** is the services-opportunity book maintained by the PS team.

**PS quote lines** has three opportunity record types:

- `Services` — quote lines for a services opportunity. Join on `Opportunity ID`. Several lines on one opportunity stay together. Names are not used to match.
- `Direct License` and `Renewal` — a sales quote that carries a PS product, usually with no services opportunity.
- A blank `Primary Quote` on a services opportunity is flagged: no primary quote yet.
- A `Primary Quote` with no lines in the quote-line export is listed separately. The quote exists, and this file has no PS lines for it.

Boat on a services opportunity comes from a `Territory` column on the closing export (`APJ-ANZ` displays as ANZ). A column named `Boat` is read the same way. If that cell is blank, the boat falls back to the quote-line territory. Add `Territory` to the closing export so an opportunity with no quote lines is not left Unassigned.

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

The page opens on a summary of the services book: services value, weighted value, and the split between forecast and pipeline. Stage 80 and above is forecast. A lower stage is pipeline. Under that is the action list: close dates that are already due, closes in the next 14 days, a status that is overdue, no primary quote, and a primary quote with no lines in the quote export. Click a number or an action to open that cut of the services table. License and renewal quotes are the other book. Filter by boat, fiscal period, stage, quote coverage, and account, or search opportunity name and account. Click a column heading to sort. The address bar keeps the current cut. The page does not call out to a network.

Close dates are compared with the report date. Today or earlier is due. The next 14 days are coming up. On the services book only, a status is expected weekly above 100,000, fortnightly above 50,000 through 100,000, and monthly from 0 through 50,000. No status date counts as overdue.

`fixtures/` holds the sanitized 20 Oct 2026 sample. `python -m pytest` checks the flags against it.

Money is the converted amount already on the report. The old commit column is shown only when it has values; in the sample it is blank, so there is no commit / upside split yet.
