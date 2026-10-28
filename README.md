# Cursor 201 follow-along: Brazos Ridge help desk

Hands-on repo for Galatiq's **Cursor 201** session. You triage a help desk queue with Cursor, from "plain prompt" to a reusable skill to a safety hook. Fictional distributor **Brazos Ridge Electronics**. **Theme: the agent drafts; a human decides.**

Repo: `galatiq-ai/galatiq-help-desk-cursor201-demo`. The step-by-step guide is **[FOLLOW-ALONG.md](FOLLOW-ALONG.md)** (also shared as a PDF).

> **Do not open the `solution` branch until after beat 3.** It contains the finished skill and the answer table, which spoils the exercise.

<table><tr><td>

### ⚠️ On Windows? Read this before beat 4.

The safety hooks in `.cursor/hooks.json` call **`bash`** and **`python3`**, which may not exist on a Windows machine. Beat 4 has a short, optional exercise where you ask Cursor to rewrite the hook in Python so it works on your machine, and a test (`python -m pytest tests/test_deny_hook.py`) tells you whether it still blocks what it should.
Until you do that, the deny hook **fails closed**: it blocks every Terraform command. That is a safe failure, not a bug. If nobody on your machine is on Windows, skip it. The presenter will call it out live.
Also: use `python` (or `py`) wherever this repo says `python3`.

</td></tr></table>

## Before the session (about 10 minutes)

You need: [Cursor](https://cursor.com), Git, **Python 3.10 or newer**. Terraform is optional (see below). No Zammad, no cloud account, no API keys.

```bash
git clone https://github.com/galatiq-ai/galatiq-help-desk-cursor201-demo.git
cd galatiq-help-desk-cursor201-demo
python3 -m pip install -r requirements.txt     # Windows: python -m pip install -r requirements.txt
python3 -m pytest                              # should pass with no network, no Terraform
python3 scripts/desk.py                        # leave running; open http://127.0.0.1:8201
```

Then open the folder in Cursor (File > Open Folder). Downloaded a zip instead? Unzip it and run the same commands from inside the folder (the first `git clone` step is not needed; `git init` is optional).

If `pytest` is not found, use `python3 -m pytest` as shown. If port 8201 is busy: `python3 scripts/desk.py --port 8202`.

## The local desk

Tickets live in `data/desk/tickets.json`: 100 tickets, 70 of them new in **Service Desk Inbox (Untriaged)** at P3. `scripts/zammad.py` works the same way as the helper for a real Zammad help desk, but with no `.env` it uses this file.

```bash
python3 scripts/zammad.py list-untriaged --limit 20
python3 scripts/zammad.py show 41086
python3 scripts/zammad.py search "ASN"
python3 scripts/zammad.py set 41086 --group "EDI & B2B Integration" --priority "P2 - High"
python3 scripts/zammad.py note 41086 --internal "Runbook: runbooks/edi-856-missing.md"
```

Watch your changes live at http://127.0.0.1:8201 (`/changed` shows what you changed). The page is read-only.

**Reset to the starting state any time:** `python3 scripts/reset_desk.py` (or `git checkout data/desk/tickets.json`).

Do not edit `data/desk/*.json` by hand and do not ask Cursor to; use the helper (a rule in `.cursor/rules/` tells the agent the same).

## The beats

| Beat | What you do |
|------|-------------|
| 1 | Plain prompt: triage the newest tickets. Notice what is missing (no wiki, no house rules). |
| 2 | Attach `@wiki/...` pages and `@runbooks/...`. Same task, much better answer. |
| 3 | Turn it into a reusable skill (`.cursor/skills/`), run it, watch the desk change. |
| 4 | Safety: a hostile ticket (#41096), the deny hook, `python3 -m pytest tests/test_deny_hook.py`. Windows: optional hook rewrite. |
| 5 | Watch only: Automations preview. |

Details, prompts and what "good" looks like: **[FOLLOW-ALONG.md](FOLLOW-ALONG.md)**.

## Layout

| Path | Purpose |
|------|---------|
| `scripts/zammad.py`, `scripts/desk.py`, `scripts/reset_desk.py` | Desk helper, read-only viewer, reset |
| `data/desk/` | The desk (JSON) |
| `wiki/` | Fictional team wiki as markdown |
| `runbooks/`, `docs/routing.md` | Runbooks and routing rules |
| `.cursor/hooks.json`, `.cursor/hooks/`, `.cursor/rules/` | Hooks and rules |
| `infra/` | Optional Terraform (beat 4 extra) |
| `tests/` | `python3 -m pytest` |

## Optional: Terraform (beat 4 extra)

Needs Terraform 1.6+ (or OpenTofu) and internet once for the provider download. Plan only; `apply` is blocked by the hook.

```bash
cd infra/envs/aws
terraform init -input=false
terraform validate
terraform plan -out=tfplan
```

Optional: `tflint` (a Terraform linter the rule asks the agent to run). If it is missing, the agent should say so and skip it. Install only if you want it:

- macOS: `brew install terraform-linters/tap/tflint` (plain `brew install tflint` no longer works)
- Windows: `winget install -e --id TerraformLinters.tflint`
- Linux and others: download the archive from the [TFLint releases page](https://github.com/terraform-linters/tflint/releases/latest)
- Check: `tflint --version`

Without Terraform installed, everything else still works, and the stop hook stays quiet. To run the extra Terraform tests: `RUN_TERRAFORM_TESTS=1 python3 -m pytest tests/test_terraform_offline.py`.

## Known limits

- The deny hook is a **regex on the command text**: a guardrail, not a security boundary. It can over-block (for example `rg "terraform apply" runbooks` is denied) and a determined person could get around it. Real enforcement is IAM and review.
- Everything is fictional: company, people, customers, tickets, wiki.
