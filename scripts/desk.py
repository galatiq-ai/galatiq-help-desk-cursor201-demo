#!/usr/bin/env python3
"""Read-only viewer for the local help desk, so you can watch the queue change.

    python3 scripts/desk.py            (python or py on Windows)
    -> open http://127.0.0.1:8201

Pages:  /            untriaged queue + recently changed tickets
        /changed     tickets changed since the desk was reset
        /ticket/NNNNN  one ticket with its notes (internal notes are marked)

It is read only (GET only, no forms), bound to 127.0.0.1, standard library only, no JavaScript
and no external requests. It reloads data/desk/tickets.json on every request and the page
refreshes itself every 5 seconds. All ticket text is HTML-escaped.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILE = ROOT / "data" / "desk" / "tickets.json"
INBOX = "Service Desk Inbox (Untriaged)"
PORT = 8201
REFRESH_SECONDS = 5

STYLE = """
body{font:14px/1.4 system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;color:#1f2937;background:#f6f8f9}
header{background:#0e5f6b;color:#fff;padding:10px 20px;display:flex;justify-content:space-between;align-items:baseline}
header a{color:#fff;text-decoration:none;margin-right:16px} header .t{font-weight:700;font-size:16px}
main{padding:16px 20px;max-width:1200px}
h2{font-size:15px;margin:18px 0 6px;color:#0e5f6b}
table{border-collapse:collapse;width:100%;background:#fff;border:1px solid #d5dde3}
th{background:#e6f2f3;color:#0e5f6b;text-align:left;padding:6px 8px;font-size:12px}
td{padding:5px 8px;border-top:1px solid #e5e9ec;vertical-align:top}
.p1{color:#b42318;font-weight:700}.p2{color:#b54708;font-weight:700}
.note{border:1px solid #d5dde3;background:#fff;border-radius:4px;padding:8px 10px;margin:8px 0}
.note.internal{background:#fff7e8;border-color:#efd9a8}
.badge{display:inline-block;font-size:11px;font-weight:700;padding:0 6px;border-radius:9px;background:#0e5f6b;color:#fff}
.badge.int{background:#8a5a00}
.meta{color:#5b6472;font-size:12px}
pre{white-space:pre-wrap;word-break:break-word;margin:4px 0 0;font:13px/1.4 ui-monospace,Menlo,Consolas,monospace}
.small{color:#5b6472;font-size:12px;margin-top:20px}
"""


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def page(title: str, body: str) -> str:
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<meta http-equiv=\"refresh\" content=\"{REFRESH_SECONDS}\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{esc(title)}</title><style>{STYLE}</style></head><body>"
        "<header><span class=\"t\">Brazos Ridge IT Service Desk (local, read only)</span>"
        "<span><a href=\"/\">Queue</a><a href=\"/changed\">Recently changed</a></span></header>"
        f"<main>{body}</main></body></html>"
    )


def _prio_class(priority: str) -> str:
    if priority.startswith("P1"):
        return "p1"
    if priority.startswith("P2"):
        return "p2"
    return ""


def _ticket_link(t: dict) -> str:
    return f"<a href=\"/ticket/{esc(t['number'])}\">#{esc(t['number'])}</a>"


def _rows(tickets: list[dict], with_changed: bool = False) -> str:
    out = []
    for t in tickets:
        extra = f"<td class=\"meta\">{esc(t.get('changed_at'))}</td>" if with_changed else ""
        out.append(
            f"<tr><td>{_ticket_link(t)}</td><td>{esc(t['title'])}</td><td>{esc(t['group'])}</td>"
            f"<td class=\"{_prio_class(t['priority'])}\">{esc(t['priority'])}</td>"
            f"<td>{esc(t['state'])}</td><td class=\"meta\">{esc(t['created'])}</td>{extra}</tr>"
        )
    return "".join(out)


def _table(tickets: list[dict], with_changed: bool = False) -> str:
    if not tickets:
        return "<p class=\"meta\">Nothing here.</p>"
    extra = "<th>Changed</th>" if with_changed else ""
    return (
        "<table><tr><th>Ticket</th><th>Title</th><th>Group</th><th>Priority</th><th>State</th>"
        f"<th>Created</th>{extra}</tr>{_rows(tickets, with_changed)}</table>"
    )


def _untriaged(data: dict) -> list[dict]:
    rows = [t for t in data["tickets"] if t["state"] == "new" and t["group"] == INBOX]
    return sorted(rows, key=lambda t: (t["created"], t["id"]), reverse=True)


def _changed(data: dict) -> list[dict]:
    rows = [t for t in data["tickets"] if t.get("changed_at")]
    return sorted(rows, key=lambda t: t["changed_at"], reverse=True)


def render_queue(data: dict) -> str:
    queue = _untriaged(data)
    changed = _changed(data)
    body = (
        f"<h2>Untriaged queue ({len(queue)})</h2>"
        f"{_table(queue)}"
        f"<h2>Recently changed ({len(changed)})</h2>"
        f"{_table(changed[:15], with_changed=True)}"
        f"<p class=\"small\">Refreshes every {REFRESH_SECONDS} seconds. Read only: change tickets "
        "through scripts/zammad.py (Cursor does this for you after you approve).</p>"
    )
    return page("Queue", body)


def render_changed(data: dict) -> str:
    changed = _changed(data)
    return page("Recently changed", f"<h2>Recently changed ({len(changed)})</h2>{_table(changed, True)}")


def render_ticket(data: dict, number: str) -> str | None:
    for t in data["tickets"]:
        if str(t["number"]) == number:
            break
    else:
        return None
    arts = []
    for a in t["articles"]:
        internal = bool(a["internal"])
        badge = "<span class=\"badge int\">internal note</span>" if internal else (
            "<span class=\"badge\">" + ("customer" if a["sender"] == "Customer" else "public") + "</span>"
        )
        arts.append(
            f"<div class=\"note{' internal' if internal else ''}\">{badge} "
            f"<span class=\"meta\">{esc(a.get('by'))} &middot; {esc(a['at'])}</span>"
            f"<pre>{esc(a['body'])}</pre></div>"
        )
    body = (
        f"<h2>#{esc(t['number'])} {esc(t['title'])}</h2>"
        "<table>"
        f"<tr><th>Group</th><td>{esc(t['group'])}</td><th>Priority</th>"
        f"<td class=\"{_prio_class(t['priority'])}\">{esc(t['priority'])}</td></tr>"
        f"<tr><th>State</th><td>{esc(t['state'])}</td><th>Owner</th><td>{esc(t.get('owner') or '-')}</td></tr>"
        f"<tr><th>Reporter</th><td>{esc(t['reporter_name'])} &lt;{esc(t['reporter_email'])}&gt;</td>"
        f"<th>Created</th><td>{esc(t['created'])}</td></tr>"
        f"<tr><th>Tags</th><td colspan=\"3\">{esc(', '.join(t.get('tags') or []) or '-')}</td></tr>"
        "</table>"
        f"<h2>Notes ({len(t['articles'])})</h2>{''.join(arts)}"
    )
    return page(f"#{t['number']}", body)


def route(data: dict, path: str) -> tuple[int, str]:
    path = path.split("?", 1)[0]
    if path in ("/", "/index.html"):
        return 200, render_queue(data)
    if path == "/changed":
        return 200, render_changed(data)
    m = re.fullmatch(r"/ticket/(\d{1,10})", path)
    if m:
        doc = render_ticket(data, m.group(1))
        if doc is not None:
            return 200, doc
    return 404, page("Not found", "<h2>Not found</h2><p><a href=\"/\">Back to the queue</a></p>")


def make_handler(path: Path):
    class Handler(BaseHTTPRequestHandler):
        server_version = "desk/1.0"

        def _send(self, code: int, doc: str, head_only: bool = False) -> None:
            raw = doc.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'"
            )
            self.end_headers()
            if not head_only:
                self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802
            try:
                code, doc = route(load(path), self.path)
            except (OSError, ValueError) as exc:
                code, doc = 500, page("Error", f"<h2>Could not read the desk file</h2><pre>{esc(exc)}</pre>")
            self._send(code, doc)

        def do_HEAD(self) -> None:  # noqa: N802
            self._send(200, "", head_only=True)

        def _refuse(self) -> None:
            self.send_response(405)
            self.send_header("Allow", "GET, HEAD")
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_POST = do_PUT = do_DELETE = do_PATCH = _refuse  # noqa: N815

        def log_message(self, fmt: str, *args: object) -> None:  # keep the terminal quiet
            pass

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only viewer for the local help desk")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--file", default=os.environ.get("LOCAL_DESK_FILE") or str(DEFAULT_FILE))
    args = parser.parse_args(argv)
    path = Path(args.file)
    if not path.is_file():
        print(f"Desk file not found: {path}", file=sys.stderr)
        return 1
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(path))
    except OSError as exc:
        print(f"Could not listen on 127.0.0.1:{args.port}: {exc}. Try --port 8202.", file=sys.stderr)
        return 1
    print(f"Desk viewer: http://127.0.0.1:{args.port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
