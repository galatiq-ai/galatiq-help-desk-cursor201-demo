#!/usr/bin/env python3
"""Stop hook: for Terraform work only, require a fresh plan + PLAN_SUMMARY.md under infra/.

The gate applies only when the conversation touched Terraform:
  1. a terraform/tofu command was run in this conversation (marker written by
     record-tf-use.py, keyed by conversation_id), or
  2. files under infra/ differ from HEAD (modified, deleted or untracked; ignored
     build output such as tfplan and .terraform/ does not count).
Help desk turns on a clean infra/ tree pass straight through.

If Terraform (or OpenTofu) is not installed on this machine the hook also passes: nobody
should be asked for a plan they cannot run. TERRAFORM_BIN may point at the binary.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys

MARKER_DIR = os.path.join(".cursor", "hooks", "state")


def marker_path(root: str, conversation_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", conversation_id)
    return os.path.join(root, MARKER_DIR, f"tf-used-{safe}")


def infra_changed(root: str) -> bool:
    """True if anything under infra/ differs from HEAD. False if git is unavailable."""
    try:
        out = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                "infra",
                # `terraform init` on another OS adds its h1 hash to the committed lock
                # files; that is not Terraform work.
                ":(exclude,glob)infra/**/.terraform.lock.hcl",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return bool(out.strip())


def terraform_installed() -> bool:
    explicit = os.environ.get("TERRAFORM_BIN")
    if explicit:
        return shutil.which(explicit) is not None
    return shutil.which("terraform") is not None or shutil.which("tofu") is not None


def touched_terraform(root: str, conversation_id: str) -> bool:
    if conversation_id and os.path.exists(marker_path(root, conversation_id)):
        return True
    return infra_changed(root)


def plan_is_fresh(root: str) -> bool:
    infra = os.path.join(root, "infra")
    tf = [
        p
        for p in glob.glob(os.path.join(infra, "**/*.tf"), recursive=True)
        if "/.terraform/" not in p.replace(os.sep, "/")
    ]
    newest_tf = max((os.path.getmtime(p) for p in tf), default=0)
    summary = os.path.join(infra, "PLAN_SUMMARY.md")
    plans = glob.glob(os.path.join(infra, "envs/*/tfplan"))
    return bool(
        os.path.exists(summary)
        and plans
        and min(os.path.getmtime(summary), max(map(os.path.getmtime, plans))) >= newest_tf
    )


def main() -> None:
    payload = json.load(sys.stdin)
    root = os.environ.get("CURSOR_PROJECT_DIR", os.getcwd())
    if payload.get("status") != "completed" or payload.get("loop_count", 0) >= 2:
        print("{}")
        return
    if not terraform_installed():
        print("{}")
        return
    if not touched_terraform(root, str(payload.get("conversation_id") or "")):
        print("{}")
        return
    if plan_is_fresh(root):
        print("{}")
        return
    print(
        json.dumps(
            {
                "followup_message": (
                    "Before you finish: in infra/, run terraform fmt -check, validate, "
                    "tflint (skip it and say so if it is not installed) and plan -out=tfplan "
                    "for the env you changed (envs/aws), "
                    "then write infra/PLAN_SUMMARY.md using "
                    "infra/scripts/plan_summary.py. Do not apply."
                )
            }
        )
    )


if __name__ == "__main__":
    main()
