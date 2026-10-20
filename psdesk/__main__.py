"""Build or serve the opportunity page.

    python -m psdesk build fixtures -o dist/index.html
    python -m psdesk serve fixtures
"""

from __future__ import annotations

import argparse
import re
from datetime import date
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from psdesk.load import ReportError, load_directory, load_table, require_reports
from psdesk.render import render
from psdesk.scorecard import build_scorecard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="psdesk", description="APJ PS opportunity scorecard")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="write the offline page")
    build.add_argument("folder", nargs="?", help="folder containing the two exports")
    build.add_argument("--opps", type=Path, help="closing-opportunity export")
    build.add_argument("--quotes", type=Path, help="quote-line export")
    build.add_argument("-o", "--out", type=Path, default=Path("dist/index.html"))
    build.add_argument("--as-of", help="report date, YYYY-MM-DD")

    serve = sub.add_parser("serve", help="build the page and serve it locally")
    serve.add_argument("folder", nargs="?", help="folder containing the two exports")
    serve.add_argument("--opps", type=Path)
    serve.add_argument("--quotes", type=Path)
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--as-of")

    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            out = _build(args.folder, args.opps, args.quotes, args.out, args.as_of)
            print(out)
            return 0
        out = _build(args.folder, args.opps, args.quotes, Path("dist/index.html"), args.as_of)
        _serve(out.parent, args.port)
        return 0
    except ReportError as exc:
        print(f"error: {exc}")
        return 1


def _build(folder, opps, quotes, out: Path, as_of: str | None) -> Path:
    opp_table, quote_table = _tables(folder, opps, quotes)
    require_reports(opp_table, quote_table)
    page = render(build_scorecard(opp_table, quote_table), opp_table, quote_table, _parse_as_of(as_of))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out


def _tables(folder, opps, quotes):
    if opps or quotes:
        if not opps or not quotes:
            raise ReportError("Pass both --opps and --quotes, or pass a folder")
        return load_table(opps), load_table(quotes)
    return load_directory(Path(folder or "fixtures"))


def _parse_as_of(value: str | None) -> date | None:
    if not value:
        return None
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", value):
        raise ReportError("--as-of must be YYYY-MM-DD")
    return date.fromisoformat(value)


def _serve(directory: Path, port: int) -> None:
    handler = lambda *a, **k: SimpleHTTPRequestHandler(*a, directory=str(directory), **k)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"http://127.0.0.1:{port}/index.html")
    server.serve_forever()


if __name__ == "__main__":
    raise SystemExit(main())
