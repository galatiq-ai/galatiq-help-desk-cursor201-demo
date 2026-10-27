# Runbook: Terraform / infra change requests

**Symptoms:** Engineer requests object store, bucket, or module change via ticket; mentions PR, plan review, retention.

**Group:** Cloud Platform / DevOps · **Priority:** P3 change unless production outage.

## Steps

1. Confirm change type: new resource vs modify existing.
2. Use provider-neutral **`artifact-store`** contract in `infra/modules/artifact-store/` (`name`, `site`, `retention_days`, `tags` → `store_id`, `store_url`).
3. Agent may draft Terraform and run **plan only**; human opens PR and applies after review.
4. Post **internal note** with plan summary; set ticket **pending** awaiting approval.
5. **Never** run `terraform apply` or `destroy` from the agent environment (hooks enforce this).

See `docs/tickets/41044-terraform-edi-archive.md` for the live demo ticket text.
