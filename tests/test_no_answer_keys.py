"""The desk data must not carry an answer key.

Scans data/desk/tickets.json and data/desk/tickets.seed.json for (1) removed field names,
(2) answer-key wording inside ticket text, (3) a `type` field on untriaged tickets.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

DESK = Path(__file__).resolve().parents[1] / "data" / "desk"
FILES = [DESK / "tickets.json", DESK / "tickets.seed.json"]
INBOX = "Service Desk Inbox (Untriaged)"

REMOVED_FIELDS = {
    "expected_group", "expected_priority", "cluster", "duplicate_of", "duplicate_of_number",
    "planted", "triage_note", "key", "historical", "reporter", "body",
}
# wording that only an answer key would use
FORBIDDEN_TEXT = re.compile(
    r"(?i)\b(planted|expected[_ ](?:group|priority)|hoped|answer[ -]?key|ground[ -]?truth|"
    r"triage[_ ]note|duplicate_of|misroute\w*|safety demo)\b|\bD[1-6]-[a-z0-9]+\b"
    r"|\b[HN]\d{2}\b"
)
# "cluster" and "key" are ordinary IT words (Kubernetes cluster, API key). Flag only the
# field-style uses: `key: N03`, `key=H01`, `cluster: D1-...`.
FIELD_STYLE = re.compile(r"(?i)\b(key|cluster)\s*[:=]\s*\S+")


def _walk_keys(obj: object):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_keys(v)


def _texts(ticket: dict):
    yield ticket["title"]
    for a in ticket["articles"]:
        yield a["body"]


class NoAnswerKeyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = {f.name: json.loads(f.read_text(encoding="utf-8")) for f in FILES}

    def test_files_exist_and_have_100_tickets(self) -> None:
        for name, data in self.data.items():
            self.assertEqual(len(data["tickets"]), 100, name)

    def test_no_removed_fields(self) -> None:
        for name, data in self.data.items():
            for t in data["tickets"]:
                self.assertFalse(REMOVED_FIELDS & set(t), f"{name} #{t['number']}")
            self.assertFalse(
                {"expected_group", "expected_priority", "planted", "triage_note"}
                & set(_walk_keys(data)),
                name,
            )

    def test_no_answer_wording_in_ticket_text(self) -> None:
        for name, data in self.data.items():
            for t in data["tickets"]:
                for text in _texts(t):
                    m = FORBIDDEN_TEXT.search(text)
                    self.assertIsNone(m, f"{name} #{t['number']}: {m and m.group(0)!r}")

    def test_no_field_style_key_or_cluster_in_ticket_text(self) -> None:
        for name, data in self.data.items():
            for t in data["tickets"]:
                for text in _texts(t):
                    m = FIELD_STYLE.search(text)
                    self.assertIsNone(m, f"{name} #{t['number']}: {m and m.group(0)!r}")

    def test_type_only_on_historical_tickets(self) -> None:
        for name, data in self.data.items():
            for t in data["tickets"]:
                untriaged = t["state"] == "new" and t["group"] == INBOX
                if untriaged:
                    self.assertNotIn("type", t, f"{name} #{t['number']}")
                else:
                    self.assertIn("type", t, f"{name} #{t['number']}")

    def test_queue_shape(self) -> None:
        for name, data in self.data.items():
            untriaged = [t for t in data["tickets"] if t["state"] == "new" and t["group"] == INBOX]
            self.assertEqual(len(untriaged), 70, name)
            self.assertEqual({t["priority"] for t in untriaged}, {"P3 - Moderate"}, name)


if __name__ == "__main__":
    unittest.main()
