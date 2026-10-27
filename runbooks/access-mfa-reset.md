# Runbook: MFA reset / new hire access

**Symptoms:** User locked out, needs MFA reset, mentions "DC systems" or warehouse apps.

**Group:** Identity & Access · **Priority:** P3 (P2 if whole team blocked).

## Steps

1. Verify identity per policy (manager approval ticket, callback).
2. Reset MFA in IdP; confirm user can reach SSO apps.
3. DC/WMS access is separate entitlement—link to access request if missing.
4. Internal note only; never send temporary passwords in public replies.
