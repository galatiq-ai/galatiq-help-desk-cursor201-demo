"""Tests for the stop hook (plan gate) and the recorder hook.

The deny hook has its own tests in tests/test_deny_hook.py.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STOP = REPO / ".cursor" / "hooks" / "plan-gate-stop.py"
RECORD = REPO / ".cursor" / "hooks" / "record-tf-use.py"


def make_fake_terraform(directory: Path) -> str:
    """A stand-in `terraform` executable so the stop-hook tests do not need a real install."""
    if os.name == "nt":
        path = directory / "terraform.cmd"
        path.write_text("@echo off\r\n")
    else:
        path = directory / "terraform"
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


class StopHookTests(unittest.TestCase):
    """plan-gate-stop.py gates Terraform work only; help desk turns pass."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "work"
        self.root.mkdir()
        self.terraform_bin = make_fake_terraform(Path(self._tmp.name))
        (self.root / "infra" / "envs" / "aws").mkdir(parents=True)
        (self.root / "infra" / "envs" / "aws" / "main.tf").write_text("# stub\n")
        (self.root / "docs").mkdir()
        (self.root / "docs" / "routing.md").write_text("routing\n")
        (self.root / ".gitignore").write_text("infra/envs/*/tfplan\n.cursor/hooks/state/\n")
        self._git("init", "-q")
        self._git("add", "-A")
        self._git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "init")

    @property
    def env_extra(self) -> dict:
        return {"TERRAFORM_BIN": self.terraform_bin}

    def _git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def _stop(self, conversation_id: str = "conv-1", **extra: object) -> dict:
        payload = {"status": "completed", "loop_count": 0, "conversation_id": conversation_id}
        payload.update(extra)
        env = {**os.environ, "CURSOR_PROJECT_DIR": str(self.root), **self.env_extra}
        proc = subprocess.run(
            [sys.executable, str(STOP)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
            env=env,
        )
        return json.loads(proc.stdout)

    def _record(self, command: str, conversation_id: str = "conv-1") -> dict:
        env = {**os.environ, "CURSOR_PROJECT_DIR": str(self.root)}
        proc = subprocess.run(
            [sys.executable, str(RECORD)],
            input=json.dumps({"command": command, "conversation_id": conversation_id}),
            text=True,
            capture_output=True,
            check=True,
            env=env,
        )
        return json.loads(proc.stdout)

    def _write_fresh_plan(self) -> None:
        time.sleep(0.05)
        (self.root / "infra" / "envs" / "aws" / "tfplan").write_text("plan")
        (self.root / "infra" / "PLAN_SUMMARY.md").write_text("summary")

    def test_help_desk_turn_passes(self) -> None:
        (self.root / "docs" / "routing.md").write_text("edited by a help desk turn\n")
        self.assertEqual(self._stop(), {})

    def test_help_desk_turn_passes_even_after_reading_terraform_docs(self) -> None:
        self._record('rg "terraform plan" runbooks')
        self._record("cat runbooks/terraform-infra-request.md")
        self.assertEqual(self._stop(), {})

    def test_terraform_edit_without_plan_is_blocked(self) -> None:
        (self.root / "infra" / "envs" / "aws" / "main.tf").write_text("module {}\n")
        self.assertIn("followup_message", self._stop())

    def test_modified_lock_file_only_passes(self) -> None:
        lock = self.root / "infra" / "envs" / "aws" / ".terraform.lock.hcl"
        lock.write_text('provider "x" { hashes = ["h1:aaa"] }\n')
        self._git("add", "-A")
        self._git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "lock")
        lock.write_text('provider "x" { hashes = ["h1:aaa", "h1:bbb"] }\n')
        self.assertEqual(self._stop(), {})
        # an untracked lock file (fresh init in a new directory) is ignored too
        (self.root / "infra" / "envs" / "gcp").mkdir()
        (self.root / "infra" / "envs" / "gcp" / ".terraform.lock.hcl").write_text("# new\n")
        self.assertEqual(self._stop(), {})

    def test_main_tf_change_still_blocked_alongside_lock_change(self) -> None:
        lock = self.root / "infra" / "envs" / "aws" / ".terraform.lock.hcl"
        lock.write_text("# lock\n")
        (self.root / "infra" / "envs" / "aws" / "main.tf").write_text("module {}\n")
        self.assertIn("followup_message", self._stop())

    def test_new_infra_file_without_plan_is_blocked(self) -> None:
        (self.root / "infra" / "envs" / "aws" / "extra.tf").write_text("# new\n")
        self.assertIn("followup_message", self._stop())

    def test_deleted_summary_is_blocked(self) -> None:
        (self.root / "infra" / "PLAN_SUMMARY.md").write_text("s")
        self._git("add", "-A")
        self._git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "summary")
        (self.root / "infra" / "PLAN_SUMMARY.md").unlink()
        self.assertIn("followup_message", self._stop())

    def test_terraform_command_in_conversation_without_plan_is_blocked(self) -> None:
        out = self._record("terraform -chdir=infra/envs/aws validate")
        self.assertEqual(out, {"permission": "allow"})
        self.assertIn("followup_message", self._stop("conv-1"))

    def test_terraform_command_marker_is_per_conversation(self) -> None:
        self._record("cd infra/envs/aws && terraform plan -out=tfplan", "conv-1")
        self.assertEqual(self._stop("conv-2"), {})

    def test_terraform_work_with_fresh_plan_and_summary_passes(self) -> None:
        (self.root / "infra" / "envs" / "aws" / "main.tf").write_text("module {}\n")
        self._record("terraform plan -out=tfplan")
        self._write_fresh_plan()
        self.assertEqual(self._stop(), {})

    def test_stale_plan_is_blocked(self) -> None:
        self._write_fresh_plan()
        time.sleep(0.05)
        (self.root / "infra" / "envs" / "aws" / "main.tf").write_text("module { changed }\n")
        self.assertIn("followup_message", self._stop())

    def test_aborted_and_loop_limit_pass(self) -> None:
        (self.root / "infra" / "envs" / "aws" / "main.tf").write_text("module {}\n")
        self.assertEqual(self._stop(status="aborted"), {})
        self.assertEqual(self._stop(loop_count=2), {})

    def test_terraform_not_installed_passes(self) -> None:
        # Terraform work is pending (edited main.tf, no plan) but this machine has no Terraform:
        # the gate must not ask for a plan nobody can run.
        (self.root / "infra" / "envs" / "aws" / "main.tf").write_text("module {}\n")
        self.assertIn("followup_message", self._stop())  # installed: gate fires
        self.terraform_bin = "definitely-not-installed-terraform-xyz"
        self.assertEqual(self._stop(), {})

    def test_record_hook_always_allows_and_ignores_garbage(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(RECORD)], input="not json", text=True, capture_output=True, check=True
        )
        self.assertEqual(json.loads(proc.stdout), {"permission": "allow"})


class HooksConfigTests(unittest.TestCase):
    """Checks the wiring in .cursor/hooks.json without caring which interpreter is used."""

    def setUp(self) -> None:
        self.cfg = json.loads((REPO / ".cursor" / "hooks.json").read_text())

    def test_recorder_and_stop_hook_registered(self) -> None:
        before = self.cfg["hooks"]["beforeShellExecution"]
        self.assertIn("record-tf-use", " ".join(h["command"] for h in before))
        stops = self.cfg["hooks"]["stop"]
        self.assertEqual(len(stops), 1)
        self.assertIn("plan-gate-stop", stops[0]["command"])

    def test_exactly_one_fail_closed_terraform_hook(self) -> None:
        before = self.cfg["hooks"]["beforeShellExecution"]
        closed = [h for h in before if h.get("failClosed") is True]
        self.assertEqual(len(closed), 1)
        self.assertIn("terraform", closed[0]["matcher"])


if __name__ == "__main__":
    unittest.main()
