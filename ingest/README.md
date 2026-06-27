# Layer 3 — AI ingestion pipeline (planned)

Pseudonymize-then-LLM. Sensitive identifiers (hostnames, IPs, ASNs, serials) are
mapped to synthetic tokens **locally** before any LLM call; structured output is
re-hydrated and written to NetBox via API. Pluggable local-model backend for
zero-egress environments.
