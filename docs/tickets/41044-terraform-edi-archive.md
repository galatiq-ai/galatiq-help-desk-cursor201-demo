# Ticket #41044 — Terraform artifact store for EDI archive

The same text is ticket #41044 on the desk (`python3 scripts/zammad.py show 41044`). This copy is here so you can @-attach it.

| Field | Value |
|-------|--------|
| **Number** | 41044 |
| **Type** | Change / service request |
| **Group (after triage)** | Cloud Platform / DevOps |
| **Priority** | P3 - Moderate |

## Title

Terraform: provider-neutral artifact store for EDI document archive (7-year retention)

## Body

Cloud Platform team — we need a **private, versioned object store** for the EDI document archive per our retention standard:

- **7-year** retention (compliance)
- Encryption at rest, no public access
- Lifecycle transition to cold/archive tier after **90 days**
- Tagged `owner`, `ticket`, `env`

Use the team's **artifact-store module contract** (`name`, `site`, `retention_days`, `tags` → `store_id`, `store_url`). Site code: **dfw2**. Preferred implementation for this change: **AWS** env root under `infra/envs/aws`.

I'll open the infra PR; need **plan review and approval before apply**.
