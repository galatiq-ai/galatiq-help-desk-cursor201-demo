"""Terraform validate and contract test for the AWS env (skipped when Terraform is unavailable).

Skips when:
  * Terraform is not installed (looks at $TERRAFORM_BIN, then `terraform` on PATH), or
  * the AWS provider has not been downloaded yet. Run once, with network:
        terraform -chdir=infra/envs/aws init -input=false
        terraform -chdir=infra/modules/artifact-store/aws init -input=false
    (or set RUN_TERRAFORM_TESTS=1 to let this test try `init` itself), or
  * `terraform init` fails (for example no network or registry blocked): the init error is
    shown as the skip reason.
Nothing here calls AWS: the env uses placeholder credentials and the module test uses a mock provider.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INFRA = REPO / "infra"
AWS_ENV = INFRA / "envs" / "aws"
AWS_MODULE = INFRA / "modules" / "artifact-store" / "aws"
TF = os.environ.get("TERRAFORM_BIN") or shutil.which("terraform")
INIT_TIMEOUT = int(os.environ.get("TERRAFORM_INIT_TIMEOUT", "180"))


def _ensure_init(directory: Path) -> None:
    if (directory / ".terraform" / "providers").is_dir():
        return
    if os.environ.get("RUN_TERRAFORM_TESTS") != "1":
        raise unittest.SkipTest(
            f"provider not initialised in {directory.relative_to(REPO)}; run `terraform init` "
            "there once (needs network) or set RUN_TERRAFORM_TESTS=1"
        )
    try:
        proc = subprocess.run(
            [TF, "init", "-input=false"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=INIT_TIMEOUT,
        )
    except subprocess.TimeoutExpired as exc:
        raise unittest.SkipTest(f"terraform init timed out after {INIT_TIMEOUT}s") from exc
    if proc.returncode != 0:
        raise unittest.SkipTest("terraform init failed: " + (proc.stderr or proc.stdout)[-400:])


class TerraformOfflineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not TF:
            raise unittest.SkipTest("terraform not found (set TERRAFORM_BIN or add it to PATH)")

    def test_validate(self) -> None:
        _ensure_init(AWS_ENV)
        proc = subprocess.run([TF, "validate"], cwd=AWS_ENV, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_contract(self) -> None:
        _ensure_init(AWS_MODULE)
        proc = subprocess.run(
            [TF, "test", "-filter=tests/contract.tftest.hcl"],
            cwd=AWS_MODULE,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
