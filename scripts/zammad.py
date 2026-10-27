#!/usr/bin/env python3
"""Help desk CLI for the Cursor 201 follow-along.

By default it talks to the local desk (data/desk/tickets.json), so nothing here needs a
network or an account. If ZAMMAD_URL and ZAMMAD_API_TOKEN are both set in .env it talks to
that Zammad instead (ZAMMAD_LOCAL=1 forces the local desk). Every run prints one line to
stderr naming the backend. Use `python` or `py` instead of `python3` on Windows.

Examples:
  python scripts/zammad.py list-untriaged
  python scripts/zammad.py show 41086
  python scripts/zammad.py set 41086 --group "EDI & B2B Integration" --priority "P2 - High" --state open
  python scripts/zammad.py note 41090 --internal "Runbook: null ship date on BACKORDER lines"
  python scripts/zammad.py search "ASN"
  python scripts/zammad.py create --title "..." --body "..." --customer-email jake.brennan@brazosridge.example
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.env_loader import zammad_env
from lib.local_desk import LocalDesk
from lib.zammad_client import ZammadClient, ZammadError


def _client() -> ZammadClient | LocalDesk:
    creds = zammad_env()
    if creds is None:
        desk = LocalDesk()
        try:
            shown = desk.path.relative_to(ROOT).as_posix()
        except ValueError:
            shown = str(desk.path)
        print(f"desk: local ({shown})", file=sys.stderr)
        return desk
    url, token = creds
    print(f"desk: zammad ({url})", file=sys.stderr)
    return ZammadClient(url, token)


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, default=str))


def cmd_list_untriaged(args: argparse.Namespace) -> None:
    client = _client()
    tickets = client.list_untriaged(limit=args.limit)
    rows = [
        {
            "number": t.get("number"),
            "title": t.get("title"),
            "created_at": t.get("created_at"),
            "priority_id": t.get("priority_id"),
            "group_id": t.get("group_id"),
            # the local desk also reports names; a real Zammad list only has ids
            **{k: t[k] for k in ("group", "priority", "state") if k in t},
        }
        for t in tickets
    ]
    _print_json({"count": len(rows), "tickets": rows})


def cmd_show(args: argparse.Namespace) -> None:
    client = _client()
    ticket = client.get_ticket_by_number(args.number)
    articles = client.list_articles(int(ticket["id"]))
    _print_json({"ticket": ticket, "articles": articles})


def cmd_set(args: argparse.Namespace) -> None:
    client = _client()
    ticket = client.get_ticket_by_number(args.number)
    updated = client.update_ticket(
        int(ticket["id"]),
        group=args.group,
        priority=args.priority,
        state=args.state,
    )
    _print_json(updated)


def cmd_note(args: argparse.Namespace) -> None:
    client = _client()
    ticket = client.get_ticket_by_number(args.number)
    article = client.add_article(int(ticket["id"]), args.body, internal=args.internal)
    _print_json(article)


def cmd_search(args: argparse.Namespace) -> None:
    client = _client()
    _print_json(client.search(args.query, limit=args.limit))


def cmd_create(args: argparse.Namespace) -> None:
    client = _client()
    customer_id = client.find_customer_id(args.customer_email)
    ticket = client.create_ticket(
        title=args.title,
        body=args.body,
        customer_id=customer_id,
        group=args.group,
    )
    _print_json(ticket)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Help desk helper for the Cursor 201 follow-along")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list-untriaged", help="List new tickets in the Service Desk inbox")
    p_list.add_argument("--limit", type=int, default=100)
    p_list.set_defaults(func=cmd_list_untriaged)

    p_show = sub.add_parser("show", help="Show one ticket and its articles")
    p_show.add_argument("number")
    p_show.set_defaults(func=cmd_show)

    p_set = sub.add_parser("set", help="Update group, priority, and/or state")
    p_set.add_argument("number")
    p_set.add_argument("--group")
    p_set.add_argument("--priority")
    p_set.add_argument("--state")
    p_set.set_defaults(func=cmd_set)

    p_note = sub.add_parser("note", help="Add an internal or public note")
    p_note.add_argument("number")
    p_note.add_argument("body")
    p_note.add_argument("--internal", action="store_true")
    p_note.set_defaults(func=cmd_note)

    p_search = sub.add_parser("search", help="Search tickets")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=50)
    p_search.set_defaults(func=cmd_search)

    p_create = sub.add_parser("create", help="Create a ticket (so you can triage a new one)")
    p_create.add_argument("--title", required=True)
    p_create.add_argument("--body", required=True)
    p_create.add_argument("--customer-email", required=True)
    p_create.add_argument("--group", default="Service Desk Inbox (Untriaged)")
    p_create.set_defaults(func=cmd_create)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except ZammadError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
