# Runbook: DC sorter down / waves stuck

**Symptoms:** Zone sorter stopped; waves not releasing; carrier cutoff risk; thousands of orders.

**Group:** Distribution Center Systems · **Priority:** P1 at carrier cutoff scale.

## Steps

1. Confirm zone id and whether manual divert is active.
2. Check sortbridge controller heartbeat and last error code.
3. Engage DC supervisor for manual pack path per business continuity sheet.
4. Dedupe multiple caller tickets; one primary P1.
5. Internal note: ETA, orders at risk count, manual path in use.
