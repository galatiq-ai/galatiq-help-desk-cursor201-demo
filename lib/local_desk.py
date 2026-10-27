"""A local, file-backed help desk with the same methods as ZammadClient.

Tickets live in data/desk/tickets.json. Use it only through scripts/zammad.py (the helper
CLI): the rule in .cursor/rules/helpdesk-safety.mdc says never to read or edit the file
directly. Nothing here touches the network.

Reset to the starting queue with:  python scripts/reset_desk.py   (or: git checkout data/desk/tickets.json)
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.company import INBOX_GROUP
from lib.zammad_client import ZammadError

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = REPO_ROOT / "data" / "desk" / "tickets.json"
DEFAULT_PRIORITY = "P3 - Moderate"
PENDING_STATES = {"pending reminder", "pending close"}


def default_desk_path() -> Path:
    return Path(os.environ.get("LOCAL_DESK_FILE") or DEFAULT_PATH)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class LocalDesk:
    """Same public methods as ZammadClient, backed by a JSON file."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_desk_path()

    # -- file access (reloaded on every call, written atomically) -------------------------
    def _load(self) -> dict[str, Any]:
        try:
            with open(self.path, encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError as exc:
            raise ZammadError(f"Local desk file not found: {self.path}") from exc
        except json.JSONDecodeError as exc:
            raise ZammadError(f"Local desk file is not valid JSON: {self.path} ({exc})") from exc

    def _save(self, data: dict[str, Any]) -> None:
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".desk-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(data, fh, indent=1, ensure_ascii=False)
                fh.write("\n")
            os.replace(tmp, self.path)  # atomic on POSIX and Windows
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    # -- lookups ---------------------------------------------------------------------------
    @staticmethod
    def _name_to_id(rows: list[dict[str, Any]], name: str, kind: str) -> int:
        for row in rows:
            if row["name"] == name:
                return int(row["id"])
        raise ZammadError(f"Unknown {kind}: {name}")

    @staticmethod
    def _id_to_name(rows: list[dict[str, Any]], row_id: int) -> str:
        for row in rows:
            if int(row["id"]) == int(row_id):
                return row["name"]
        raise ZammadError(f"Unknown id {row_id}")

    @staticmethod
    def _find(data: dict[str, Any], ticket_id: int) -> dict[str, Any]:
        for ticket in data["tickets"]:
            if int(ticket["id"]) == int(ticket_id):
                return ticket
        raise ZammadError(f"GET /tickets/{ticket_id} -> 404: Couldn't find Ticket with 'id'={ticket_id}")

    @staticmethod
    def _user_id(data: dict[str, Any], email: str | None) -> int | None:
        for user in data.get("users", []):
            if email and user["email"].lower() == email.lower():
                return int(user["id"])
        return None

    # -- rendering: Zammad-shaped dicts ----------------------------------------------------
    def _render(self, data: dict[str, Any], t: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": t["id"],
            "number": str(t["number"]),
            "title": t["title"],
            "group_id": self._name_to_id(data["groups"], t["group"], "group"),
            "priority_id": self._name_to_id(data["priorities"], t["priority"], "priority"),
            "state_id": self._name_to_id(data["states"], t["state"], "state"),
            "owner_id": self._user_id(data, t.get("owner_email")),
            "customer_id": self._user_id(data, t.get("reporter_email")),
            "group": t["group"],
            "priority": t["priority"],
            "state": t["state"],
            "owner": t.get("owner"),
            "customer": t.get("reporter_name"),
            "tags": list(t.get("tags") or []),
            "created_at": t["created"],
            "updated_at": t.get("changed_at") or t.get("closed") or t["created"],
            "close_at": t.get("closed"),
            "pending_time": t.get("pending_until"),
        }

    @staticmethod
    def _render_article(ticket_id: int, a: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": a["id"],
            "ticket_id": ticket_id,
            "body": a["body"],
            "internal": bool(a["internal"]),
            "sender": a["sender"],
            "type": "note" if a["sender"] == "Agent" else "web",
            "content_type": "text/plain",
            "created_by": a.get("by"),
            "created_at": a["at"],
        }

    # -- ZammadClient interface ------------------------------------------------------------
    def list_groups(self) -> list[dict[str, Any]]:
        return list(self._load()["groups"])

    def list_priorities(self) -> list[dict[str, Any]]:
        return list(self._load()["priorities"])

    def list_states(self) -> list[dict[str, Any]]:
        return list(self._load()["states"])

    def list_tickets(self, page: int = 1, per_page: int = 100) -> list[dict[str, Any]]:
        data = self._load()
        rows = sorted(data["tickets"], key=lambda t: (t["created"], t["id"]), reverse=True)
        start = (page - 1) * per_page
        return [self._render(data, t) for t in rows[start : start + per_page]]

    def list_untriaged(self, limit: int = 100) -> list[dict[str, Any]]:
        """Tickets in the Service Desk inbox still in state *new*, newest first."""
        data = self._load()
        rows = [t for t in data["tickets"] if t["state"] == "new" and t["group"] == INBOX_GROUP]
        rows.sort(key=lambda t: (t["created"], t["id"]), reverse=True)
        return [self._render(data, t) for t in rows[:limit]]

    def get_ticket(self, ticket_id: int) -> dict[str, Any]:
        data = self._load()
        return self._render(data, self._find(data, ticket_id))

    def get_ticket_by_number(self, number: str | int) -> dict[str, Any]:
        data = self._load()
        for t in data["tickets"]:
            if str(t["number"]) == str(number):
                return self._render(data, t)
        raise ZammadError(f"Ticket #{number} not found")

    def list_articles(self, ticket_id: int) -> list[dict[str, Any]]:
        data = self._load()
        t = self._find(data, ticket_id)
        return [self._render_article(int(t["id"]), a) for a in t["articles"]]

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        data = self._load()
        q = (query or "").strip()
        if q.lower().startswith("number:"):
            wanted = q.split(":", 1)[1].strip()
            hits = [t for t in data["tickets"] if str(t["number"]) == wanted]
        else:
            needle = q.lower()
            hits = [
                t
                for t in data["tickets"]
                if needle in t["title"].lower()
                or needle in (t.get("reporter_name") or "").lower()
                or needle in (t.get("reporter_email") or "").lower()
                or any(needle in a["body"].lower() for a in t["articles"])
            ]
        hits.sort(key=lambda t: (t["created"], t["id"]), reverse=True)
        return [self._render(data, t) for t in hits[:limit]]

    def find_customer_id(self, email: str) -> int:
        data = self._load()
        uid = self._user_id(data, email)
        if uid is None:
            raise ZammadError(f"No user for {email}")
        return uid

    def update_ticket(
        self,
        ticket_id: int,
        *,
        group: str | None = None,
        priority: str | None = None,
        state: str | None = None,
        owner_id: int | None = None,
    ) -> dict[str, Any]:
        data = self._load()
        t = self._find(data, ticket_id)
        # validate everything first so a bad value changes nothing
        if group is not None:
            self._name_to_id(data["groups"], group, "group")
        if priority is not None:
            self._name_to_id(data["priorities"], priority, "priority")
        if state is not None:
            self._name_to_id(data["states"], state, "state")
            if state in PENDING_STATES and not t.get("pending_until"):
                raise ZammadError(
                    f"PUT /tickets/{ticket_id} -> 422: {{\"error\":\"Need a valid pending_time "
                    f"for state '{state}'\"}}"
                )
        owner = None
        if owner_id is not None:
            owner = next((u for u in data["users"] if int(u["id"]) == int(owner_id)), None)
            if owner is None:
                raise ZammadError(f"Unknown owner id: {owner_id}")
        if group is not None:
            t["group"] = group
        if priority is not None:
            t["priority"] = priority
        if state is not None:
            t["state"] = state
        if owner is not None:
            t["owner"], t["owner_email"] = owner["name"], owner["email"]
        t["changed_at"] = _now()
        self._save(data)
        return self._render(data, t)

    def add_article(
        self,
        ticket_id: int,
        body: str,
        *,
        internal: bool = False,
        subject: str | None = None,
    ) -> dict[str, Any]:
        if not body or not body.strip():
            raise ZammadError("POST /ticket_articles -> 422: Need a body")
        data = self._load()
        t = self._find(data, ticket_id)
        next_id = 1 + max((a["id"] for x in data["tickets"] for a in x["articles"]), default=0)
        now = _now()
        art = {
            "id": next_id,
            "at": now,
            "by": "agent",
            "by_email": None,
            "sender": "Agent",
            "internal": bool(internal),
            "body": body,
        }
        if subject:
            art["subject"] = subject
        t["articles"].append(art)
        t["changed_at"] = now
        self._save(data)
        return self._render_article(int(t["id"]), art)

    def create_ticket(
        self,
        *,
        title: str,
        body: str,
        customer_id: int,
        group: str = INBOX_GROUP,
    ) -> dict[str, Any]:
        data = self._load()
        self._name_to_id(data["groups"], group, "group")
        customer = next((u for u in data["users"] if int(u["id"]) == int(customer_id)), None)
        if customer is None:
            raise ZammadError(f"Unknown customer id: {customer_id}")
        now = _now()
        next_id = 1 + max(int(t["id"]) for t in data["tickets"])
        number = str(1 + max(int(t["number"]) for t in data["tickets"]))
        art_id = 1 + max((a["id"] for x in data["tickets"] for a in x["articles"]), default=0)
        ticket = {
            "id": next_id,
            "number": number,
            "title": title,
            "created": now,
            "state": "new",
            "group": group,
            "priority": DEFAULT_PRIORITY,
            "owner": None,
            "owner_email": None,
            "reporter_name": customer["name"],
            "reporter_email": customer["email"],
            "tags": [],
            "pending_until": None,
            "closed": None,
            "changed_at": now,
            "articles": [
                {
                    "id": art_id,
                    "at": now,
                    "by": customer["name"],
                    "by_email": customer["email"],
                    "sender": "Customer",
                    "internal": False,
                    "body": body,
                }
            ],
        }
        data["tickets"].append(ticket)
        self._save(data)
        return self._render(data, ticket)
