# Runbook: Pack line label printers blank

**Symptoms:** Zebra printers on pack lines print blank labels; multiple lines affected.

**Group:** Distribution Center Systems · **Priority:** P2 (shipping delayed).

## Steps

1. Verify media/ribbon loaded; run test print from printer front panel.
2. Check label template version pushed from WMS print server.
3. Restart print spooler service on affected line PCs if template ok.
4. Dedupe if multiple lines share one template deploy event.
