# Brazos Ridge Service Desk: Priority, SLA and Escalation Matrix

> **Demo page.** Brazos Ridge Electronics is fictional. The targets and roles below are illustrative demo values, not real commitments.

|  |  |
| -- | -- |
| **Space** | IT Service Desk |
| **Owner** | Service Desk L1 lead |
| **Status** | Current (demo values) |

## 1. Targets by priority (demo values)

| Priority | Response target | Update cadence | Resolution target | Who is engaged |
| -- | -- | -- | -- | -- |
| **P1 Critical** | 15 minutes | Every 30 minutes | 4 hours | On-call engineer, the P1 bridge, the service desk manager |
| **P2 High** | 1 hour | Every 2 hours | 1 business day | Assigned group lead |
| **P3 Moderate** | 4 hours | Daily | 3 business days | Assigned group |
| **P4 Low** | 1 business day | Weekly | 10 business days | Assigned group |

## 2. When to open the P1 bridge

Open the bridge when **any** of these is true:

* More than 3 customers report the same failure.
* The ticket mentions revenue at risk, a line-down customer, or a carrier cutoff.
* A whole DC zone, the website checkout, or the Order API is down.

One primary P1 ticket owns the incident. Link every duplicate to it in an **internal note**.

## 3. Escalation path

1. **Service Desk L1** triages and proposes group and priority. A human approves.
2. The **assigned group** acknowledges within the response target.
3. If the target is missed, the **group lead** is paged.
4. If a P1 is unresolved after 1 hour, the **service desk manager** joins the bridge.

## 4. What the agent may and may not do

* **May:** propose group and priority, find duplicates, write internal notes, summarize runbook findings.
* **May not:** close tickets, send customer replies, change other tickets, or change priority without human approval.

## 5. Related

* [Routing and triage standards](routing-and-triage-standards.md)
* Release log and known issues
