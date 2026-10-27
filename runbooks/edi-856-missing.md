# Runbook: Missing or rejected EDI 856 (ASN)

**Symptoms:** Customer dock cannot receive; "no ASN"; truck waiting; PO acknowledged (855) but no 856.

**Group:** EDI & B2B Integration · **Typical priority:** P2–P3 depending on line-down at customer.

## Steps

1. Confirm PO number and trading partner id in the ticket.
2. In EDI monitor, search outbound 856 for the PO. Status `REJECTED` or absent?
3. If rejected, open the functional ack (997) or partner portal message for segment/quantity errors.
4. Compare against sample in `data/edi/856-sample.po4500123.edi` if provided in repo notes.
5. **Internal note:** rejection reason, whether resend is queued, ETA.
6. **Customer workaround:** receive against packing list / manual ASN entry per partner agreement—human sends reply.

**Not DC Facilities** unless the issue is physical dock equipment with no EDI angle.
