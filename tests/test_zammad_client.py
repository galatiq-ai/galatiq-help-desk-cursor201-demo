"""Tests for Zammad client and CLI (mocked HTTP)."""

from __future__ import annotations

import json
import unittest
from unittest import mock

from lib.zammad_client import ZammadClient


class ZammadClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = ZammadClient("https://zammad.example", "test-token")

    @mock.patch("urllib.request.urlopen")
    def test_get_ticket_by_number(self, urlopen: mock.MagicMock) -> None:
        search_body = json.dumps([{"id": 7, "number": "41086", "title": "ASN"}]).encode()
        urlopen.return_value.__enter__.return_value.read.return_value = search_body
        ticket = self.client.get_ticket_by_number("41086")
        self.assertEqual(ticket["number"], "41086")

    @mock.patch("urllib.request.urlopen")
    def test_add_internal_note(self, urlopen: mock.MagicMock) -> None:
        resp = json.dumps({"id": 99, "internal": True}).encode()
        urlopen.return_value.__enter__.return_value.read.return_value = resp
        article = self.client.add_article(7, "triaged", internal=True)
        self.assertTrue(article["internal"])

    @mock.patch("urllib.request.urlopen")
    def test_update_ticket_resolves_ids(self, urlopen: mock.MagicMock) -> None:
        def side_effect(req, timeout=60):
            path = req.full_url
            if path.endswith("/groups"):
                body = json.dumps([{"id": 3, "name": "EDI & B2B Integration"}]).encode()
            elif path.endswith("/ticket_priorities"):
                body = json.dumps([{"id": 2, "name": "P2 - High"}]).encode()
            elif path.endswith("/ticket_states"):
                body = json.dumps([{"id": 4, "name": "open"}]).encode()
            elif path.endswith("/tickets/5"):
                body = json.dumps({"id": 5, "group_id": 3}).encode()
            else:
                body = b"{}"
            m = mock.MagicMock()
            m.__enter__.return_value.read.return_value = body
            return m

        urlopen.side_effect = side_effect
        updated = self.client.update_ticket(
            5, group="EDI & B2B Integration", priority="P2 - High", state="open"
        )
        self.assertEqual(updated["id"], 5)


if __name__ == "__main__":
    unittest.main()
