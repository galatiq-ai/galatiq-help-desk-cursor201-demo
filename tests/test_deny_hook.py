"""Does the guardrail really block terraform apply?

This test does not care how the deny hook is written. It reads .cursor/hooks.json, finds the
beforeShellExecution hook that is fail closed and matches terraform, and runs its command
exactly the way Cursor does: from the repo root, with the JSON payload on stdin.

* On Mac and Linux the shipped bash hook passes.
* On Windows the bash hook cannot run (and, being fail closed, blocks every terraform command).
  After you have Cursor rewrite the hook for your machine, this test is the judge: the rewrite
  is right only if every case below still passes. A hook that allows everything, a weaker
  pattern, or a hooks.json entry without failClosed makes it fail.

Cursor treats {"permission": "deny"} (or exit code 2) as a block.
Run:  python -m pytest tests/test_deny_hook.py     (python3 on Mac/Linux, python or py on Windows)
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

MUST_DENY = [
    "terraform apply",
    "terraform apply tfplan",
    "terraform -chdir=infra/envs/aws apply tfplan",
    "terraform -chdir infra/envs/aws apply tfplan",  # space form of -chdir
    "terraform -chdir=infra/envs/aws destroy",
    "terraform -chdir infra/envs/aws destroy",
    "cd infra/envs/aws && terraform apply -auto-approve",
    "terraform import aws_s3_bucket.this my-bucket",
    "terraform state rm aws_s3_bucket.this",
    "terraform state mv aws_s3_bucket.a aws_s3_bucket.b",
    "terraform taint aws_s3_bucket.this",
    "terraform untaint aws_s3_bucket.this",
    "terraform force-unlock 1234",
    "tofu apply",
    "tofu -chdir=infra/envs/aws destroy",
    "tofu -chdir infra/envs/aws apply",
    "tofu import aws_s3_bucket.this my-bucket",
    "tofu state rm aws_s3_bucket.this",
]
MUST_ALLOW = [
    "terraform plan -out=tfplan",
    "terraform -chdir=infra/envs/aws plan -out=tfplan",
    "terraform -chdir infra/envs/aws plan -out=tfplan",
    "terraform validate",
    "terraform fmt -check",
    "terraform init -input=false",
    "terraform show -json tfplan",
    "terraform test",
    "tofu plan -out=tfplan",
    "ls infra",
]


def deny_hook_entry() -> dict:
    cfg = json.loads((REPO / ".cursor" / "hooks.json").read_text())
    hooks = cfg["hooks"]["beforeShellExecution"]
    closed = [h for h in hooks if h.get("failClosed") is True and "terraform" in h.get("matcher", "")]
    assert len(closed) == 1, (
        "expected exactly one beforeShellExecution hook with failClosed: true and a terraform "
        f"matcher in .cursor/hooks.json, found {len(closed)}"
    )
    return closed[0]


def run_hook(command_line: str, terraform_command: str) -> tuple[int, dict | None, str]:
    payload = json.dumps(
        {
            "hook_event_name": "beforeShellExecution",
            "command": terraform_command,
            "cwd": str(REPO),
            "conversation_id": "test-conversation",
        }
    )
    proc = subprocess.run(
        command_line,
        shell=True,
        cwd=REPO,
        input=payload,
        text=True,
        capture_output=True,
        timeout=30,
    )
    out = None
    try:
        out = json.loads(proc.stdout)
    except ValueError:
        pass
    return proc.returncode, out, proc.stdout + proc.stderr


class DenyHookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entry = deny_hook_entry()

    def test_registered_fail_closed(self) -> None:
        self.assertIs(self.entry["failClosed"], True)
        self.assertIn("terraform", self.entry["matcher"])
        self.assertIn("tofu", self.entry["matcher"])

    def test_blocks_state_changing_commands(self) -> None:
        for cmd in MUST_DENY:
            with self.subTest(cmd):
                code, out, raw = run_hook(self.entry["command"], cmd)
                denied = code == 2 or (out is not None and out.get("permission") == "deny")
                self.assertTrue(denied, f"{cmd!r} was not blocked (exit {code}): {raw[:300]}")

    def test_allows_plan_validate_and_friends(self) -> None:
        for cmd in MUST_ALLOW:
            with self.subTest(cmd):
                code, out, raw = run_hook(self.entry["command"], cmd)
                self.assertEqual(code, 0, f"{cmd!r}: hook exited {code}: {raw[:300]}")
                self.assertIsNotNone(out, f"{cmd!r}: hook printed no JSON: {raw[:300]}")
                self.assertEqual(out.get("permission"), "allow", f"{cmd!r}: {raw[:300]}")

    def test_deny_message_present(self) -> None:
        _, out, raw = run_hook(self.entry["command"], "terraform apply")
        if out is not None and out.get("permission") == "deny":
            self.assertTrue(out.get("user_message") or out.get("agent_message"), raw[:300])


if __name__ == "__main__":
    unittest.main()
