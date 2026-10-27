# Runbook: API rate limit (HTTP 429)

**Symptoms:** Customer reports "blocked" or 429 from Order/Search API; web orders fine.

**Group:** eCommerce & APIs · **Priority:** P3 unless production cutover with deadline (then P2).

## Steps

1. Look up API key prefix and account id; confirm per-minute quota in gateway admin.
2. Distinguish abuse vs legitimate burst (cutover test, bad retry loop).
3. Temporary quota raise requires account manager approval—note in internal comment only.
4. Draft reply: standard backoff, batching guidance, or scheduled quota bump—human sends.

**Not Security Operations** unless credentials were exposed.
