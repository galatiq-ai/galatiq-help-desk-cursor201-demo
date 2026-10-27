#!/usr/bin/env python3
"""Turn `terraform show -json tfplan` into a markdown PR comment."""
import json, sys
from collections import Counter
p = json.load(sys.stdin)
c, rows = Counter(), []
for r in p.get("resource_changes", []):
    a = "/".join(r["change"]["actions"])
    if a == "no-op":
        continue
    c[a] += 1
    rows.append("| `%s` | %s |" % (r["address"], a))
print("### Terraform plan (review required, not applied)\n")
print("| Resource | Action |\n|---|---|")
print("\n".join(rows) or "| (no changes) | |")
print("\n**Totals:** " + (", ".join("%s: %d" % kv for kv in c.items()) or "none"))
if c.get("delete") or c.get("delete/create") or c.get("create/delete"):
    print("\n> WARNING: this plan destroys or replaces resources.")
