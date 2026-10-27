"""Local desk parity with the Zammad helper: list, show, set, note, search, create."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lib.local_desk import LocalDesk
from lib.zammad_client import ZammadError

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "data" / "desk" / "tickets.seed.json"
CLI = REPO / "scripts" / "zammad.py"
INBOX = "Service Desk Inbox (Untriaged)"


class LocalDeskTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "tickets.json"
        shutil.copyfile(SEED, self.path)
        self.desk = LocalDesk(self.path)

    def test_list_untriaged_is_70_newest_first(self) -> None:
        rows = self.desk.list_untriaged(limit=100)
        self.assertEqual(len(rows), 70)
        self.assertEqual(rows[0]["number"], "41100")
        created = [r["created_at"] for r in rows]
        self.assertEqual(created, sorted(created, reverse=True))
        self.assertEqual(len(self.desk.list_untriaged(limit=5)), 5)

    def test_show_ticket_and_articles(self) -> None:
        t = self.desk.get_ticket_by_number("41086")
        self.assertEqual(t["state"], "new")
        self.assertEqual(t["group"], INBOX)
        arts = self.desk.list_articles(t["id"])
        self.assertEqual(len(arts), 1)
        self.assertFalse(arts[0]["internal"])
        self.assertIn("advance ship notice", arts[0]["body"])
        with self.assertRaises(ZammadError):
            self.desk.get_ticket_by_number("99999")

    def test_set_group_priority_state(self) -> None:
        t = self.desk.get_ticket_by_number("41086")
        out = self.desk.update_ticket(
            t["id"], group="EDI & B2B Integration", priority="P2 - High", state="open"
        )
        self.assertEqual((out["group"], out["priority"], out["state"]), (
            "EDI & B2B Integration", "P2 - High", "open"))
        again = LocalDesk(self.path).get_ticket_by_number("41086")  # persisted
        self.assertEqual(again["group"], "EDI & B2B Integration")
        self.assertEqual(len(self.desk.list_untriaged(limit=100)), 69)

    def test_unknown_names_rejected_with_zammad_text(self) -> None:
        t = self.desk.get_ticket_by_number("41086")
        before = self.path.read_text(encoding="utf-8")
        for kwargs, text in (
            ({"state": "pending"}, "Unknown state: pending"),
            ({"group": "Nope"}, "Unknown group: Nope"),
            ({"priority": "P9"}, "Unknown priority: P9"),
        ):
            with self.assertRaises(ZammadError) as ctx:
                self.desk.update_ticket(t["id"], **kwargs)
            self.assertEqual(str(ctx.exception), text)
        # a bad value mixed with good ones changes nothing
        with self.assertRaises(ZammadError):
            self.desk.update_ticket(t["id"], group="EDI & B2B Integration", state="pending")
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_pending_reminder_needs_a_time(self) -> None:
        t = self.desk.get_ticket_by_number("41086")
        with self.assertRaises(ZammadError):
            self.desk.update_ticket(t["id"], state="pending reminder")
        # a ticket that already carries pending_until may enter that state
        pending = self.desk.get_ticket_by_number("41015")
        self.assertEqual(pending["state"], "pending reminder")
        self.desk.update_ticket(pending["id"], state="open")
        self.desk.update_ticket(pending["id"], state="pending reminder")

    def test_internal_note(self) -> None:
        t = self.desk.get_ticket_by_number("41090")
        art = self.desk.add_article(t["id"], "triage proposal", internal=True)
        self.assertTrue(art["internal"])
        self.assertEqual(art["sender"], "Agent")
        self.assertEqual(art["created_by"], "agent")
        self.assertTrue(art["created_at"])
        arts = LocalDesk(self.path).list_articles(t["id"])
        self.assertEqual(arts[-1]["body"], "triage proposal")
        with self.assertRaises(ZammadError):
            self.desk.add_article(t["id"], "   ")

    def test_search_is_case_insensitive_over_title_body_reporter(self) -> None:
        by_title = {h["number"] for h in self.desk.search("pinecrest")}
        self.assertIn("41086", by_title)
        by_body = {h["number"] for h in self.desk.search("ADVANCE SHIP NOTICE")}
        self.assertIn("41086", by_body)
        by_reporter = {h["number"] for h in self.desk.search("keisha")}
        self.assertIn("41086", by_reporter)
        self.assertEqual(self.desk.search("number:41086")[0]["number"], "41086")
        self.assertEqual(self.desk.search("zzzz-no-such-text"), [])
        self.assertEqual(len(self.desk.search("a", limit=3)), 3)

    def test_create_ticket(self) -> None:
        cid = self.desk.find_customer_id("jake.brennan@brazosridge.example")
        t = self.desk.create_ticket(title="Test ticket", body="hello", customer_id=cid)
        self.assertEqual(t["number"], "41101")
        self.assertEqual(t["state"], "new")
        self.assertEqual(t["group"], INBOX)
        self.assertEqual(t["priority"], "P3 - Moderate")
        self.assertEqual(len(self.desk.list_untriaged(limit=100)), 71)
        self.assertEqual(self.desk.list_untriaged(limit=1)[0]["number"], "41101")
        with self.assertRaises(ZammadError):
            self.desk.find_customer_id("nobody@example.invalid")
        with self.assertRaises(ZammadError):
            self.desk.create_ticket(title="x", body="y", customer_id=cid, group="Nope")

    def test_writes_are_atomic_and_leave_no_temp_files(self) -> None:
        t = self.desk.get_ticket_by_number("41086")
        self.desk.add_article(t["id"], "n1", internal=True)
        self.desk.update_ticket(t["id"], priority="P2 - High")
        json.loads(self.path.read_text(encoding="utf-8"))  # still valid JSON
        self.assertEqual([p.name for p in self.path.parent.iterdir()], ["tickets.json"])
        # a failing write (unwritable target dir) leaves the original file untouched
        original = self.path.read_text(encoding="utf-8")
        real_replace = os.replace

        def boom(*_a, **_k):
            raise OSError("disk full")

        os.replace = boom
        try:
            with self.assertRaises(OSError):
                self.desk.update_ticket(t["id"], priority="P1 - Critical")
        finally:
            os.replace = real_replace
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)
        self.assertEqual([p.name for p in self.path.parent.iterdir()], ["tickets.json"])


class CliTests(unittest.TestCase):
    """scripts/zammad.py picks the local desk when no Zammad is configured."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "tickets.json"
        shutil.copyfile(SEED, self.path)
        env = {k: v for k, v in os.environ.items() if not k.startswith("ZAMMAD_")}
        env["LOCAL_DESK_FILE"] = str(self.path)
        env["ZAMMAD_ENV_FILE"] = str(Path(self._tmp.name) / "no-such.env")
        self.env = env

    def run_cli(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            capture_output=True,
            text=True,
            env=env or self.env,
            cwd=REPO,
        )

    def test_list_show_set_note_search_create(self) -> None:
        p = self.run_cli("list-untriaged", "--limit", "3")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("desk: local", p.stderr)
        self.assertEqual(json.loads(p.stdout)["count"], 3)

        p = self.run_cli("show", "41086")
        self.assertEqual(json.loads(p.stdout)["ticket"]["number"], "41086")

        p = self.run_cli(
            "set", "41086", "--group", "EDI & B2B Integration", "--priority", "P2 - High", "--state", "open"
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["group"], "EDI & B2B Integration")

        p = self.run_cli("note", "41086", "--internal", "Runbook: edi-856-missing")
        self.assertTrue(json.loads(p.stdout)["internal"])

        p = self.run_cli("search", "ASN")
        self.assertTrue(json.loads(p.stdout))

        p = self.run_cli(
            "create", "--title", "New one", "--body", "b", "--customer-email",
            "jake.brennan@brazosridge.example",
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["number"], "41101")

    def test_unknown_state_error_matches_zammad(self) -> None:
        p = self.run_cli("set", "41086", "--state", "pending")
        self.assertEqual(p.returncode, 1)
        self.assertIn("Unknown state: pending", p.stderr)

    def test_zammad_values_select_zammad_backend_and_local_flag_overrides(self) -> None:
        env = {**self.env, "ZAMMAD_URL": "http://127.0.0.1:9", "ZAMMAD_API_TOKEN": "t"}
        env.pop("LOCAL_DESK_FILE")
        p = self.run_cli("search", "x", env=env)
        self.assertIn("desk: zammad", p.stderr)  # tries a real Zammad (nothing listens there)
        env2 = {**env, "ZAMMAD_LOCAL": "1", "LOCAL_DESK_FILE": str(self.path)}
        p = self.run_cli("list-untriaged", "--limit", "1", env=env2)
        self.assertIn("desk: local", p.stderr)
        self.assertEqual(p.returncode, 0, p.stderr)
        env3 = {**self.env, "ZAMMAD_URL": "http://127.0.0.1:9", "ZAMMAD_API_TOKEN": ""}
        p = self.run_cli("list-untriaged", "--limit", "1", env=env3)
        self.assertIn("desk: local", p.stderr)  # blank token means local


class ResetTests(unittest.TestCase):
    def test_seed_and_working_copy_start_identical(self) -> None:
        a = (REPO / "data" / "desk" / "tickets.json").read_text(encoding="utf-8")
        b = SEED.read_text(encoding="utf-8")
        # the working copy may legitimately differ after you triage; the committed one must not
        out = subprocess.run(
            ["git", "status", "--porcelain", "--", "data/desk/tickets.json"],
            cwd=REPO, capture_output=True, text=True,
        )
        if out.returncode != 0 or out.stdout.strip():
            self.skipTest("not a clean git checkout of the desk file (you may have been triaging)")
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
