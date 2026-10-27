#!/usr/bin/env python3
"""Python reference version of .cursor/hooks/deny-tf-apply.sh (same behavior).

Reads the Cursor beforeShellExecution payload on stdin and prints a permission decision.
Blocks: terraform / tofu  apply, destroy, import, taint, untaint, force-unlock,
        state rm|mv|push|replace-provider  (with or without -chdir=DIR / -chdir DIR).
Fail closed: if the payload cannot be read, deny.

Use it by pointing every hook in .cursor/hooks.json at `python .cursor/hooks/deny_tf_apply.py`
(python, py or python3, whichever works on your machine) and keeping "failClosed": true.
This is a guardrail on command text, not a security boundary.
"""

import json
import re
import sys

PATTERN = re.compile(
    r"(terraform|tofu)(\s+-chdir(=|\s+)\S+)?\s+"
    r"(apply|destroy|import|taint|untaint|force-unlock|state\s+(rm|mv|push|replace-provider))"
)

DENY = {
    "permission": "deny",
    "user_message": "Blocked: this repo stops at terraform plan. A human applies after PR review.",
    "agent_message": (
        "terraform apply/destroy/state changes are not allowed here. Run fmt, validate, tflint "
        "and plan, then summarize the plan for human review."
    ),
}
DENY_CANT_PARSE = {
    "permission": "deny",
    "user_message": "Blocked: the deny hook could not read the command.",
    "agent_message": "The terraform guardrail hook could not run, so terraform commands are blocked until it is fixed.",
}


def main() -> int:
    try:
        command = json.load(sys.stdin).get("command", "")
    except Exception:
        print(json.dumps(DENY_CANT_PARSE))
        return 0
    if PATTERN.search(command or ""):
        print(json.dumps(DENY))
    else:
        print(json.dumps({"permission": "allow"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
