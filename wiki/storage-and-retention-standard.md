# Brazos Ridge Cloud Platform: Storage and Retention Standard

> **Demo page.** Brazos Ridge Electronics is fictional. This page stands in for a team wiki page used in the Cursor 201 training.

|  |  |
| -- | -- |
| **Space** | Cloud Platform |
| **Owner** | Cloud Platform / DevOps lead |
| **Status** | Current |

## 1. Standard for archive object stores

Every archive store must be:

* **Private.** No public access.
* **Versioned.**
* **Encrypted at rest.**
* **Tiered.** Move to the cold or archive tier after **90 days**.
* **Retained for the period in section 2.**
* **Tagged** with `owner`, `ticket` and `env`.

## 2. Retention periods

| Data | Retention |
| -- | -- |
| EDI document archive | **7 years** (compliance) |
| Application logs | 90 days |
| Build artifacts | 30 days |

## 3. How to request one

1. Open a service request. It lands with **Cloud Platform / DevOps** at P3 as a change, unless a production outage is involved.
2. Use the provider-neutral **artifact-store module**:
   * Inputs: `name`, `site`, `retention_days`, `tags`.
   * Outputs: `store_id`, `store_url`.
3. The agent drafts the Terraform and runs `fmt`, `validate`, `tflint`, `test` and `plan` only.
4. The agent writes a plan summary and posts it as an **internal note** on the ticket. It does not change the ticket state; the ticket stays **open** for the reviewer.
5. A **person reviews the plan and runs apply.**

## 4. Hard rules

* **Agents never run** `apply`**,** `destroy`**,** `import` **or state changes.** A hook blocks them.
* Rules guide the agent. Hooks enforce the line that must never be crossed.
* No `data` sources in sandbox roots under `infra/envs/*`.

## 5. Worked example: ticket #41044

A new object store for the EDI document archive, 7-year retention, site `dfw2`, tagged with owner, ticket and env. Draft the module call, run the plan, summarize it in an internal note on the ticket, leave the ticket open, and stop for approval.

## 6. Related

* [Routing and triage standards](routing-and-triage-standards.md)
* [AI agent usage policy](ai-agent-usage-policy.md)
