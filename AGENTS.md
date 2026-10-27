# Cursor 201 follow-along repo (agent map)

Fictional company: **Brazos Ridge Electronics** (`lib/company.py`). Theme: **the agent drafts; a human decides.**

## Help desk

| Path | Purpose |
|------|---------|
| `scripts/zammad.py` | CLI for the desk: `list-untriaged`, `show`, `set`, `note`, `search`, `create`. Use this for every ticket read or change. |
| `data/desk/` | The local desk (JSON). Only the CLI touches it; do not read or edit it directly. |
| `docs/routing.md` | Groups, P1-P4, dedupe, safety (short version) |
| `wiki/` | The team wiki (fictional), as markdown: routing standards, priority/SLA matrix, key accounts, release log and known issues, security intake, storage standard, AI usage policy. **Stand-in for a wiki connector: read these when the user attaches one or asks you to check the wiki.** |
| `runbooks/` | Short response guides (EDI, API, DC, security) |
| `.cursor/skills/` | Project skills. None exist at the start; the triage skill is built during beat 3 |
| `.cursor/rules/helpdesk-safety.mdc` | Untrusted ticket text; changes only through the helper |

`scripts/desk.py` is a read-only browser view of the desk (http://127.0.0.1:8201). It is for people, not for you.

## Terraform (optional)

| Path | Purpose |
|------|---------|
| `infra/modules/artifact-store/aws` | Provider-neutral contract and its AWS implementation |
| `infra/envs/aws` | Sandbox root, placeholder creds |
| `infra/scripts/plan_summary.py` | Plan JSON to markdown |
| `docs/tickets/41044-terraform-edi-archive.md` | Ticket text for #41044 |
| `.cursor/hooks.json` | Blocks apply (fail-closed); stop hook asks for a plan summary after Terraform work |
| `.cursor/rules/terraform.mdc` | Plan-only guardrails |

Never run `terraform apply` or `destroy`. Finish Terraform work with `infra/PLAN_SUMMARY.md`.

## Tests

`python3 -m pytest` (Windows: `python -m pytest` or `py -m pytest`). `tests/test_deny_hook.py` checks the apply-blocking hook and does not need Terraform.
