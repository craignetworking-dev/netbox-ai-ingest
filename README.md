# netbox-ai-ingest

**A config-driven NetBox provisioning engine and AI documentation-ingestion
pipeline.** Turns declarative baselines into a version-controlled network source
of truth, and turns messy, unstructured network documentation into structured
NetBox objects — safely, with sensitive identifiers pseudonymized locally before
any data reaches an LLM.

Companion to **[netbox-ansible-automation](https://github.com/craignetworking-dev/netbox-ansible-automation)**:
this project builds and structures the NetBox source of truth; that one consumes
it (via NetBox dynamic inventory) to drive device configuration. Together they
form a complete source-of-truth → config-automation pipeline.

```
netbox-ai-ingest            NetBox                  netbox-ansible-automation
(source-of-truth engine     (devices, roles,        (dynamic inventory +
 + AI ingestion)      ─────► sites, interfaces) ◄───  Jinja2 config rendering)
```

## What this demonstrates

- **Config-driven, idempotent provisioning** — a dependency-aware engine applies
  declarative YAML baselines (regions, sites, tenancy, device types, front/rear
  port templates) into NetBox. A second run against an unchanged baseline makes
  zero changes; that re-run proof is the definition of done.
- **Applied AI with a security model** — an ingestion pipeline structures
  unstructured network docs into NetBox objects using the Claude API, with a
  local pseudonymization layer that strips sensitive identifiers (IPs, hostnames,
  serials) before anything is sent to an LLM.
- **The network + AI intersection** — deep network domain modeling (DCIM,
  source-of-truth structure) combined with agentic/LLM tooling, built by a
  network engineer rather than bolted on.
- **Verification-first engineering** — API schemas are confirmed against the live
  system (e.g. by introspecting NetBox serializers directly) rather than assumed;
  design decisions and their limitations are documented honestly.

## Architecture

The engine is built in layers, each scoped tightly and proven before the next:

1. **Deployment** — reproducible NetBox via a pinned `netbox-docker` wrapper
   (Docker, versioned).
2. **Provisioning engine** — a config-driven, dependency-aware, idempotent
   applier. A registry describes each object type (endpoint, natural key,
   references); the applier topologically orders dependencies, resolves
   references by slug, and PATCHes only changed fields. Widening to new object
   types is done by data + registry entries, not by rewriting the engine.
3. **AI ingestion pipeline** — pseudonymize-then-LLM: a local pass replaces
   sensitive identifiers with stable, reversible placeholders (kept in a
   local-only mapping) before any LLM call. The security model protects
   identifiers via map custody and detection completeness; its boundaries
   (e.g. topology shape) are documented explicitly.
4. **Synthetic dataset** — a fully fabricated demo network for end-to-end
   demonstration. No real network data, ever.

## The pseudonymization security model

The ingestion pipeline exists because handing sensitive network documentation to
an LLM is a real risk. Its design is deliberate:

- **Identifiers are pseudonymized locally** (IPv4, hostnames, serials) before any
  data leaves the environment.
- **Security lives in map custody and detection completeness** — the placeholder
  ↔ real-value mapping never leaves the local machine (git-ignored), and every
  sensitive token must be caught. A missed token is the real risk, not a
  guessable placeholder.
- **Deterministic mapping** (same token → same placeholder) preserves the
  relationships an LLM needs to structure the data correctly, while private
  addresses cannot be reconstructed from structure alone.
- **Named limitation:** the pipeline protects *identifiers*, not *topology shape*
  — preserving structure is the pipeline's purpose, so the operator consents to
  an LLM seeing the shape, not the identifiers. This boundary is documented
  rather than hidden.

## Data & safety

All data in this repository is **synthetic**. Real vendor model names (public
catalog data) may appear; instance-level data — hostnames, IPs, serials,
topology, real cabling — never does. API tokens live only in a git-ignored
`.env`, and the pseudonymization mapping is git-ignored and local-only.

## Project status

- **Layer 1 — deployment:** reproducible NetBox. Complete.
- **Layer 2 — provisioning engine:** organization/tenancy/DCIM including
  device-type front/rear port templates with pairing. Complete and idempotent.
- **Layer 3 — AI ingestion:** identifier pseudonymizer complete; LLM structuring
  and re-identification are the next slices.

See the `SPEC` documents for detailed design, build order, and the verified
API-schema notes.

## Related

- **[netbox-ansible-automation](https://github.com/craignetworking-dev/netbox-ansible-automation)**
  — NetBox-driven Ansible automation that consumes this source of truth to render
  and apply device configuration.
