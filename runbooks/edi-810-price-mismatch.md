# Runbook: EDI 810 transmitted but customer disputes price

**Symptoms:** Partner says invoice (810) amount wrong; 997 accepted.

**Group:** ERP & Pricing (not EDI ops unless transmission failed).

## Steps

1. Verify 810 reached partner (997 accepted).
2. Pull quote/contract price tier in ERP for the SKU and PO date.
3. Check PriceSync / FX staging locks if prices drifted (`runbooks/pricesync-stuck.md`).
4. Internal note: root cause (tier, promo, rounding), corrective credit path.
5. Draft reply: acknowledge discrepancy, credit/rebill timeline—human sends.
