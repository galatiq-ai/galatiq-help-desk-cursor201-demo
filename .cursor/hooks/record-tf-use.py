#!/usr/bin/env python3
"""beforeShellExecution (observer only): remember that this conversation ran Terraform.

The stop hook (plan-gate-stop.py) uses the marker to decide whether the plan gate
applies to the conversation. This hook never blocks anything: it always answers
"allow" and leaves apply/destroy blocking to deny-tf-apply.sh (deny wins when
Cursor merges hook responses).
"""
import json
import os
import re
import sys

# `terraform|tofu [-chdir=x] <subcommand>` at the start of a command or after ; & | ( or whitespace.
# Quotes are not allowed before the word, so `rg "terraform plan" runbooks` does not match.
TF_COMMAND = re.compile(
    r"(?:^|[\s;&|(])(?:terraform|tofu)(?:\s+-chdir=\S+)?\s+"
    r"(?:init|validate|plan|fmt|test|show|apply|destroy|import|state|output|workspace|"
    r"taint|untaint|force-unlock|providers|graph|console)\b"
)
MARKER_DIR = os.path.join(".cursor", "hooks", "state")


def marker_path(root: str, conversation_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", conversation_id)
    return os.path.join(root, MARKER_DIR, f"tf-used-{safe}")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        command = str(payload.get("command", ""))
        conversation_id = str(payload.get("conversation_id") or "")
        if conversation_id and TF_COMMAND.search(command):
            root = os.environ.get("CURSOR_PROJECT_DIR", os.getcwd())
            path = marker_path(root, conversation_id)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("1\n")
    except Exception:  # never let bookkeeping break a shell command
        pass
    print(json.dumps({"permission": "allow"}))


if __name__ == "__main__":
    main()
