# Infrastructure (optional beat 4 extra)

Terraform is **optional** in this workshop. Everything you need for beat 4 (the safety hook) works without it.

- `modules/artifact-store/aws`: the provider-neutral contract (`name`, `site`, `retention_days`, `tags` -> `store_id`, `store_url`) and its AWS implementation.
- `envs/aws`: sandbox root with placeholder credentials and a local backend. Starts as a stub; ticket #41044 asks you to fill it in.
- `modules/artifact-store/{gcp,azure}`: interface files only (`variables.tf`, `outputs.tf`), kept to show that the contract is the same on every cloud. There is no GCP or Azure root in this repo.
- `scripts/plan_summary.py`: turns `terraform show -json tfplan` into markdown for a human reviewer.
- `.cursor/hooks.json` (repo root): blocks `apply` / `destroy` / `import` / state changes; the stop hook asks for a fresh plan and `infra/PLAN_SUMMARY.md` after Terraform work. If Terraform is not installed the stop hook stays quiet.

To try it you need Terraform 1.6+ (or OpenTofu) and network access once, to download the AWS provider with `terraform init`. No cloud account is used: the root has dummy credentials and skips all validation calls.
