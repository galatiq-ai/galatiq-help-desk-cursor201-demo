# Brazos Ridge Service Desk: Key Accounts and Trading Partners

> **Demo page.** Brazos Ridge Electronics and all customers listed here are fictional. Tiers are illustrative demo values.

|  |  |
| -- | -- |
| **Space** | IT Service Desk |
| **Owner** | Customer Operations |
| **Status** | Current (demo values) |

## 1. Why this page matters

The priority standard says P2 applies when a **major customer is blocked**. This page says who counts as major and how they connect to us.

## 2. Key accounts

| Customer | How they order | Notes | Demo tier |
| -- | -- | -- | -- |
| **Pinecrest Medical Devices** (Fort Worth plant) | EDI, with ASN (856) required for receiving | Their dock cannot accept a truck without an ASN. See ticket #41086. | Key |
| **Corvane Data Systems** (account 0048812) | Order API from their ERP | Line-down customers escalate fast. See #41088. | Key |
| **Redhollow Defense Electronics** | Ariba punchout (cXML) | Punchout is their only ordering path. See #41093. | Key |
| **Bluewater Marine Electronics** | Email and phone to sales | Order-status questions go to Sales Ops. See #41096. | Standard |
| **Ostara Robotics** | Search API with an API key | Growing account. Rate limits (HTTP 429) are common. See #41070. | Growing |

## 3. Routing hints by customer channel

| Channel | Group |
| -- | -- |
| EDI (850, 855, 856, 810, 997), AS2, VAN, SFTP | EDI & B2B Integration |
| Ariba and other punchout (cXML or OCI) | EDI & B2B Integration |
| Search, Order or Catalog API, API keys, rate limits | eCommerce & APIs |
| Website, checkout, My Account | eCommerce & APIs |
| Wrong price on an invoice | ERP & Pricing |

## 4. Handling rules

* A key account that **cannot order or receive** is at least **P2**.
* Many customers affected, or a line-down with revenue at risk, is **P1**.
* Customer names appear in internal notes only. Do not put customer details in a public reply unless a person approves it.

## 5. Related

* [Routing and triage standards](routing-and-triage-standards.md)
* [Priority, SLA and escalation matrix](priority-sla-and-escalation-matrix.md)
