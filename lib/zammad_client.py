"""Small Zammad REST client for the Cursor 201 help desk demo."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from lib.company import INBOX_GROUP


class ZammadError(RuntimeError):
    pass


class ZammadClient:
    def __init__(self, base_url: str, api_token: str) -> None:
        self.base = base_url.rstrip("/") + "/api/v1"
        self.api_token = api_token

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        ok: tuple[int, ...] = (200, 201),
        headers: dict[str, str] | None = None,
    ) -> Any:
        url = self.base + path
        data = None
        req_headers = {
            "Authorization": f"Token token={self.api_token}",
            "Content-Type": "application/json",
        }
        if headers:
            req_headers.update(headers)
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            raise ZammadError(f"{method} {path} -> {exc.code}: {detail}") from exc
        if not raw.strip():
            return None
        return json.loads(raw)

    def list_tickets(self, page: int = 1, per_page: int = 100) -> list[dict[str, Any]]:
        return self._request("GET", f"/tickets?per_page={per_page}&page={page}") or []

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        q = urllib.parse.quote(query)
        return self._request("GET", f"/tickets/search?query={q}&limit={limit}") or []

    def get_ticket_by_number(self, number: str | int) -> dict[str, Any]:
        hits = self.search(f"number:{number}", limit=5)
        for ticket in hits:
            if str(ticket.get("number")) == str(number):
                return ticket
        raise ZammadError(f"Ticket #{number} not found")

    def get_ticket(self, ticket_id: int) -> dict[str, Any]:
        return self._request("GET", f"/tickets/{ticket_id}")

    def list_articles(self, ticket_id: int) -> list[dict[str, Any]]:
        return self._request("GET", f"/ticket_articles/by_ticket/{ticket_id}") or []

    def list_groups(self) -> list[dict[str, Any]]:
        return self._request("GET", "/groups") or []

    def list_priorities(self) -> list[dict[str, Any]]:
        return self._request("GET", "/ticket_priorities") or []

    def list_states(self) -> list[dict[str, Any]]:
        return self._request("GET", "/ticket_states") or []

    def _resolve_group_id(self, group_name: str) -> int:
        for group in self.list_groups():
            if group["name"] == group_name:
                return int(group["id"])
        raise ZammadError(f"Unknown group: {group_name}")

    def _resolve_priority_id(self, priority_name: str) -> int:
        for priority in self.list_priorities():
            if priority["name"] == priority_name:
                return int(priority["id"])
        raise ZammadError(f"Unknown priority: {priority_name}")

    def _resolve_state_id(self, state_name: str) -> int:
        for state in self.list_states():
            if state["name"] == state_name:
                return int(state["id"])
        raise ZammadError(f"Unknown state: {state_name}")

    def update_ticket(
        self,
        ticket_id: int,
        *,
        group: str | None = None,
        priority: str | None = None,
        state: str | None = None,
        owner_id: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if group is not None:
            payload["group_id"] = self._resolve_group_id(group)
        if priority is not None:
            payload["priority_id"] = self._resolve_priority_id(priority)
        if state is not None:
            payload["state_id"] = self._resolve_state_id(state)
        if owner_id is not None:
            payload["owner_id"] = owner_id
        return self._request("PUT", f"/tickets/{ticket_id}", body=payload)

    def add_article(
        self,
        ticket_id: int,
        body: str,
        *,
        internal: bool = False,
        subject: str | None = None,
    ) -> dict[str, Any]:
        article = {
            "ticket_id": ticket_id,
            "body": body,
            "type": "note",
            "internal": internal,
            "sender": "Agent",
            "content_type": "text/plain",
        }
        if subject:
            article["subject"] = subject
        return self._request("POST", "/ticket_articles", body=article)

    def create_ticket(
        self,
        *,
        title: str,
        body: str,
        customer_id: int,
        group: str = INBOX_GROUP,
    ) -> dict[str, Any]:
        payload = {
            "title": title,
            "group": group,
            "customer_id": customer_id,
            "article": {
                "subject": title,
                "body": body,
                "type": "web",
                "internal": False,
                "sender": "Customer",
                "content_type": "text/plain",
            },
        }
        return self._request("POST", "/tickets", body=payload)

    def find_customer_id(self, email: str) -> int:
        q = urllib.parse.quote(email)
        users = self._request("GET", f"/users/search?query={q}&limit=5")
        if not users:
            raise ZammadError(f"No user for {email}")
        return int(users[0]["id"])

    def list_untriaged(self, limit: int = 100) -> list[dict[str, Any]]:
        """Tickets in the Service Desk inbox still in state *new*."""
        state_new = self._resolve_state_id("new")
        inbox_id = self._resolve_group_id(INBOX_GROUP)
        out: list[dict[str, Any]] = []
        page = 1
        while len(out) < limit:
            batch = self.list_tickets(page=page, per_page=100)
            if not batch:
                break
            for ticket in batch:
                if ticket.get("group_id") == inbox_id and ticket.get("state_id") == state_new:
                    out.append(ticket)
                    if len(out) >= limit:
                        break
            page += 1
        return out
