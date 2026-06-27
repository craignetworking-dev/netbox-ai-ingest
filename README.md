# netbox-ai-ingest

A reproducible NetBox deployment with a privacy-preserving AI ingestion pipeline:
turn messy network documentation into a structured NetBox source of truth, with
sensitive identifiers pseudonymized **locally** before any data ever reaches an LLM.

Built by a network engineer, for environments where "just send it to the cloud"
is not an acceptable answer.

## Why this exists

Most "AI for networks" demos are a chatbot wired to an API. This is the opposite:
infrastructure-first. It stands up real NetBox, ingests real-shaped data, and keeps
sensitive identifiers out of any third-party model **by design** — not by policy.

## Architecture — four layers

| Layer | What it does | Status |
|------:|--------------|--------|
| 1. Deployment | One-command, reproducible NetBox via pinned `netbox-docker` | ✅ working |
| 2. Data-model scaffold | Opinionated baseline: sites, roles, device types, interfaces | ⬜ planned |
| 3. AI ingestion pipeline | Pseudonymize-then-LLM: structures messy docs into NetBox objects | ⬜ planned |
| 4. FakeCorp dataset | Synthetic, shareable demo network | ⬜ planned |

## Hard rule

No real-world network data ever enters this repository. All demo data is synthetic
(see `fakecorp/`). At runtime, the pipeline pseudonymizes sensitive identifiers
locally before any LLM call — so the differentiator is the security model, not an
afterthought.

## Quick start (Layer 1)

```bash
cd deploy
./bootstrap.sh
# wait ~1-2 min for first-boot migrations, then create an admin user
# (command is printed at the end of bootstrap)
```

Then browse to http://localhost:8000. See [`deploy/README.md`](deploy/README.md) for the full runbook.
