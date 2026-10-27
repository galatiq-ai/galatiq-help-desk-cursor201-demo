# Runbook: Punchout / cXML cart return failures (Ariba, OCI)

**Symptoms:** Customer cannot return cart from eProcurement to supplier catalog; "session expired", cXML errors.

**Group:** EDI & B2B Integration · **Priority:** P2 for key account unable to order.

## Steps

1. Confirm punchout profile id and whether issue is prod vs test.
2. Check cXML POST logs for `HookURL` / `BuyerCookie` mismatch.
3. Validate cert on punchout gateway if TLS errors mentioned.
4. Internal note: failed request id, fix (profile, cert, clock skew).
5. Customer workaround: place order via web account if contract allows—human communicates.
