# Brazos Ridge Service Desk: Release Log and Known Issues

> **Demo page.** Brazos Ridge Electronics is fictional. This page stands in for a team wiki page (Confluence-style) used in the Cursor 201 training.

|  |  |
| -- | -- |
| **Space** | IT Service Desk |
| **Owner** | eCommerce & APIs lead |
| **Updated** | Oct 23, 2026 |
| **Status** | Open incidents listed below |

## 1. How to use this page

Before proposing a priority for an incident, check whether it started right after a release or matches a known issue. Link related tickets in one **internal note** on the primary ticket. Do not close duplicates without human approval.

## 2. Recent releases

| Release | Deployed | Component | Notes |
| -- | -- | -- | -- |
| **2026.10.23-1** | Oct 23, 2026, before 08:14 CT (deploy #4471) | OrderHub API | Canary stage was skipped. Linked to the 5xx spike below. |

## 3. Known issues

### KI-1: OrderHub API HTTP 5xx after release 2026.10.23-1 (open)

* **Started:** 08:14 CT on Oct 23. The 5xx rate went from 0.2% to 38%.
* **Symptom:** `POST /api/v2/order` returns HTTP 500 with `System.NullReferenceException` in the pricing tier resolver, for customers with a contract price tier (ticket #41090). Order status polls also return HTTP 500 with `ship_date=null` on `BACKORDER` lines (`data/logs/order-api-sample.log`).
* **Suspected cause:** release 2026.10.23-1. Two signals are open: the contract-tier pricing path and the null ship date on `BACKORDER` lines (see the runbook). Root cause is not confirmed.
* **Workaround:** the ERP sync can skip lines with `line_status=BACKORDER` until a patch ships.
* **Primary ticket:** #41090. **Duplicates:** #41088 (Corvane Data Systems, line-down), #41089 and #41091.
* **Priority:** P1. Many customers are affected and revenue is at risk.
* **Runbook:** `runbooks/order-api-5xx.md`. **Next step:** consider a rollback of 2026.10.23-1. Escalate on-call per the P1 bridge rules.

### KI-2: Zone D sorter not accepting cartons (open)

* **Started:** about 8:50 pm.
* **Symptom:** waves stay in RELEASED and induct scanners show `ERR 0x1F4 NO ROUTE FOR LPN`. Maintenance reports the PLC is fine, so the fault points at the WMS-to-sorter interface.
* **Impact:** about 1,800 orders are due for UPS and FedEx pickup.
* **Primary ticket:** #41076. **Duplicate:** #41077.
* **Priority:** P1 at carrier-cutoff scale.
* **Runbook:** `runbooks/wms-sorter-waves-stuck.md`.

### KI-3: Card payments declined at checkout (open)

* **Started:** about 12:55 CT.
* **Symptom:** every card payment on the website returns "Payment could not be authorized (ref PG-502)". PayPal and net-terms accounts work.
* **Impact:** 40+ customers are waiting in chat.
* **Primary ticket:** #41097. **Duplicate:** #41098.
* **Priority:** P1. Revenue is stopped for card customers.
* **Cause:** not yet identified.

## 4. Related

* [Routing and triage standards](routing-and-triage-standards.md)
* [Priority, SLA and escalation matrix](priority-sla-and-escalation-matrix.md)
