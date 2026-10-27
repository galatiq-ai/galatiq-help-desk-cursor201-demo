#!/bin/bash
# beforeShellExecution: block terraform/tofu apply, destroy, import, state mutation.
# Needs bash and python3. Windows: see the README Windows call-out for the Cursor-assisted rewrite.
deny_cant_parse='{"permission":"deny","user_message":"Blocked: the deny hook could not read the command (is python3 installed?).","agent_message":"The terraform guardrail hook could not run, so terraform commands are blocked until it is fixed."}'
if ! cmd=$(python3 -c 'import json,sys;print(json.load(sys.stdin).get("command",""))' 2>/dev/null); then
  echo "$deny_cant_parse"
  exit 0
fi
if echo "$cmd" | grep -Eq '(terraform|tofu)([[:space:]]+-chdir(=|[[:space:]]+)[^[:space:]]+)?[[:space:]]+(apply|destroy|import|taint|untaint|force-unlock|state[[:space:]]+(rm|mv|push|replace-provider))'; then
  echo '{"permission":"deny","user_message":"Blocked: this repo stops at terraform plan. A human applies after PR review.","agent_message":"terraform apply/destroy/state changes are not allowed here. Run fmt, validate, tflint and plan, then summarize the plan for human review."}'
  exit 0
fi
echo '{"permission":"allow"}'
