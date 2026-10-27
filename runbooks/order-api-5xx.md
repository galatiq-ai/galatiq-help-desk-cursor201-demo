# Runbook: OrderHub / Order API HTTP 5xx after release

**Symptoms:** Multiple customers report `HTTP 500` on order placement or status API; often after a release tag (e.g. `2026.10.23-1`).

**Group:** eCommerce & APIs · **Priority:** P1 if many customers / line-down.

## Steps

1. Check status page and error rate dashboard for `order-api`.
2. Correlate with latest deploy tag in ticket text.
3. Pull sample stack trace from `data/logs/order-api-sample.log` pattern: null ship date on `BACKORDER` lines.
4. Identify primary ticket if duplicates exist; link others internally.
5. **Internal note:** suspected defect, workaround (skip BACKORDER line in status poll), rollback candidate—no public promise of root cause.
6. Escalate on-call per P1 bridge if customer count > 3 or revenue-at-risk language.

**Workaround:** ERP sync may skip lines with `line_status=BACKORDER` until patch ships.
