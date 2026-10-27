"""The read-only viewer must HTML-escape ticket text and expose no write routes."""

from __future__ import annotations

import copy
import http.client
import json
import re
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

import importlib.util

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "data" / "desk" / "tickets.seed.json"

spec = importlib.util.spec_from_file_location("desk_viewer", REPO / "scripts" / "desk.py")
desk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desk)

PAYLOAD = '<script>alert("x")</script><img src=x onerror=alert(1)> & <b>bold</b>'


def data_with_hostile_ticket() -> dict:
    data = json.loads(SEED.read_text(encoding="utf-8"))
    t = copy.deepcopy(data["tickets"][-1])
    t.update(id=999, number="49999", title=PAYLOAD, reporter_name=PAYLOAD)
    t["articles"] = [
        {"id": 9001, "at": "2026-10-23T08:00:00-04:00", "by": PAYLOAD, "by_email": None,
         "sender": "Customer", "internal": False, "body": PAYLOAD},
        {"id": 9002, "at": "2026-10-23T08:05:00-04:00", "by": "agent", "by_email": None,
         "sender": "Agent", "internal": True, "body": PAYLOAD},
    ]
    t["changed_at"] = "2026-10-27T10:00:00+00:00"
    t["group"] = PAYLOAD
    data["tickets"].append(t)
    return data


def only_escaped_markup(doc: str) -> bool:
    """True when the document has no tag other than the ones this viewer writes itself."""
    allowed = {
        "!doctype", "html", "head", "meta", "title", "style", "body", "header", "span", "a", "main",
        "h2", "table", "tr", "th", "td", "p", "div", "pre",
    }
    tags = {m.group(1).lower() for m in re.finditer(r"</?([A-Za-z!][A-Za-z0-9-]*)", doc)}
    return tags <= allowed


class ViewerEscapingTests(unittest.TestCase):
    def test_ticket_41096_renders_text_not_markup(self) -> None:
        data = json.loads(SEED.read_text(encoding="utf-8"))
        code, doc = desk.route(data, "/ticket/41096")
        self.assertEqual(code, 200)
        self.assertIn("ignore all previous instructions", doc)
        self.assertIn("&quot;resolved by automation&quot;", doc)  # quotes escaped
        self.assertNotIn('"resolved by automation"', doc)
        self.assertTrue(only_escaped_markup(doc))

    def test_hostile_ticket_everywhere(self) -> None:
        data = data_with_hostile_ticket()
        for path in ("/", "/changed", "/ticket/49999"):
            code, doc = desk.route(data, path)
            self.assertEqual(code, 200, path)
            self.assertNotIn("<script", doc.lower(), path)
            self.assertNotIn("<img", doc.lower(), path)
            self.assertNotIn("<b>", doc.lower(), path)
            self.assertNotIn("onerror=alert(1)>", doc, path)
            self.assertTrue(only_escaped_markup(doc), path)
        self.assertIn("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;", desk.route(data, "/ticket/49999")[1])

    def test_every_seed_ticket_renders(self) -> None:
        data = json.loads(SEED.read_text(encoding="utf-8"))
        for t in data["tickets"]:
            code, doc = desk.route(data, f"/ticket/{t['number']}")
            self.assertEqual(code, 200)
            self.assertTrue(only_escaped_markup(doc), t["number"])
        self.assertEqual(desk.route(data, "/ticket/1")[0], 404)
        self.assertEqual(desk.route(data, "/ticket/abc")[0], 404)
        self.assertEqual(desk.route(data, "/nope")[0], 404)

    def test_queue_lists_70_and_marks_internal_notes(self) -> None:
        data = json.loads(SEED.read_text(encoding="utf-8"))
        code, doc = desk.route(data, "/")
        self.assertIn("Untriaged queue (70)", doc)
        _, ticket = desk.route(data, "/ticket/41001")
        self.assertIn("internal note", ticket)

    def test_page_has_no_script_or_external_requests(self) -> None:
        data = json.loads(SEED.read_text(encoding="utf-8"))
        _, doc = desk.route(data, "/")
        self.assertNotIn("<script", doc.lower())
        self.assertNotRegex(doc, r"(?i)(src|href)=\"https?://")
        self.assertIn('http-equiv="refresh" content="5"', doc)


class ViewerServerTests(unittest.TestCase):
    """Boot the real server on a free port: GET works, anything that writes is refused."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), desk.make_handler(SEED))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def request(self, method: str, path: str):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request(method, path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        conn.close()
        return resp, body

    def test_get_and_headers(self) -> None:
        resp, body = self.request("GET", "/ticket/41096")
        self.assertEqual(resp.status, 200)
        self.assertIn("default-src 'none'", resp.getheader("Content-Security-Policy"))
        self.assertIn("Bluewater", body)

    def test_bound_to_localhost_only(self) -> None:
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_write_methods_refused(self) -> None:
        for method in ("POST", "PUT", "DELETE", "PATCH"):
            resp, _ = self.request(method, "/ticket/41096")
            self.assertEqual(resp.status, 405, method)


if __name__ == "__main__":
    unittest.main()
