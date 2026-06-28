# CLAUDE.md — netbox-ai-ingest

Project memory for Claude Code. Read this fully before doing anything. When a
request conflicts with the rules here, surface the conflict instead of silently
working around it.

## What this project is

A reproducible NetBox deployment plus a privacy-preserving AI ingestion pipeline
that turns messy network documentation into a structured NetBox source of truth.
Sensitive identifiers are pseudonymized **locally** before any data reaches an LLM.

This repo serves two real purposes at once. Optimize for both:

1. **A hiring credential** — public, reviewed by network-automation employers
   (NetBox Labs is the top target, especially solutions/technical roles). Code
   must be clean, readable, and explainable: the author has to be able to walk
   any line of it in an interview. "It works" is not the bar; "I can defend every
   decision" is.
2. **The delivery engine for NetSource** — a productized B2B service (NetBox
   implementation + AI-assisted documentation cleanup for mid-market IT teams).
   Favor approaches that generalize across client environments over one-off hacks.

## Hard rules (non-negotiable)

- **No real-world network data ever enters this repository.** All demo data is
  synthetic and lives under `fakecorp/` / `baselines/`. If asked to ingest,
  commit, or hardcode a real config, hostname, IP, ASN, serial, or topology —
  refuse and use or generate synthetic data instead. This holds even if the
  request is framed as "just to test" or "to help." (Real vendor model names —
  e.g. a Cisco Catalyst 9300 — are public catalog data and are allowed; what
  stays synthetic are instances: hostnames, IPs, serials, and topology.)
- **Pseudonymize before the LLM, always.** In the ingestion pipeline, sensitive
  identifiers are mapped to synthetic tokens *locally* before any LLM call, then
  re-hydrated locally after. No raw sensitive identifier is ever sent to a
  third-party model. This security model is the project's differentiator, not an
  afterthought — treat it as a design constraint, not a feature to add later.
- **No secrets in the repo.** API keys, tokens, passwords go in untracked `.env`
  files or environment variables. `.gitignore` already excludes `*.env` (except
  `*.env.example`).
- **Do not edit vendored upstream.** `deploy/.netbox-docker/` is the official
  netbox-docker project, cloned and gitignored by the bootstrap. It is a black
  box managed by `deploy/bootstrap.sh`. Never edit inside it; customize only via
  `deploy/docker-compose.override.yml`.

## Architecture — four layers

Build in order. Keep each layer's work scoped to that layer; don't bleed ahead.

| Layer | What it does | Status |
|------:|--------------|--------|
| 1. Deployment | One-command reproducible NetBox via pinned `netbox-docker` wrapper, with reboot persistence | ✅ done |
| 2. Provisioning engine | Config-driven, dependency-aware engine that applies per-client YAML baselines (org + location hierarchy, tenancy, DCIM) into NetBox idempotently | ⬜ in progress |
| 3. AI ingestion pipeline | Pseudonymize-then-LLM: structure messy docs into NetBox objects via API | ⬜ planned |
| 4. FakeCorp dataset | Fully synthetic demo network: devices, interfaces, cables on top of the Layer 2 baseline | ⬜ planned |

## Layer 2 — provisioning engine (current work)

Detailed marching orders live in `scaffold/SPEC.md`. Summary:

- **Engine / data separation.** An engine (`scaffold/`) knows *how* to create
  NetBox objects idempotently and in dependency order; per-client baseline files
  (`baselines/<name>.yaml`) declare *what* exists. FakeCorp is the first baseline,
  not special-cased code. Onboarding a client = a new baseline file, not a code
  change. This is both the credential and the NetSource margin story.
- **Dependency order is a hard requirement.** Apply types in the order NetBox's
  foreign keys require (regions → site groups → tenancy → sites → locations →
  manufacturers → device roles → device types → templates), and within
  self-nesting types apply parents before children.
- **Idempotency is a contract.** Get-or-update by slug; a second run against an
  unchanged baseline makes zero changes and exits 0. That re-run proof is the
  definition of done.
- **Slice 1** (current): build the full engine, populate only org + location
  (regions, site groups, sites, locations). **Slice 2**: widen the same engine
  to tenancy + DCIM by adding registry entries and baseline data — no refactor.
- References between objects are by **slug**, never by ID (IDs are
  environment-specific and break portability).

## Current state

- **Layer 1 complete and public.** `deploy/bootstrap.sh` vendors netbox-docker
  pinned to `5.0.1`, applies `docker-compose.override.yml` (port `8000:8080`,
  healthcheck `start_period`, `restart: unless-stopped` on all services), and
  brings the stack up. Verified: NetBox v4.6, Postgres 18, dual Valkey, all
  healthy, survives reboot.
- **Layer 2 in progress** per `scaffold/SPEC.md`.
- Layers 3–4 are placeholders (`ingest/`, `fakecorp/`).

## Tech stack & conventions

- **Deployment:** Docker Compose v2 wrapping official `netbox-docker`. Customize
  only through the override file; keep it minimal.
- **Python (Layers 2–3):** use a local virtualenv (`python3 -m venv .venv`), never
  system pip. Use `pynetbox` for the NetBox REST API, `PyYAML` for baselines,
  `python-dotenv` for env. Use the Anthropic SDK for LLM calls. Pin dependencies
  in `requirements.txt`.
- **Idempotency:** scaffold/ingest scripts must be safely re-runnable — get-or-
  update by natural key, so a second run produces no changes and no errors.
- **Commits:** one logical change per commit; message format `Layer N: <what>`.
- **NetBox access:** the app is at `http://localhost:8000`. URL + API token come
  from an untracked `.env` (`NETBOX_URL`, `NETBOX_TOKEN`), never hardcoded.

## How to work in this repo

- Keep changes scoped to the current layer and the file(s) under discussion.
- Before a large refactor, restructure, or new dependency, explain the plan and
  wait for confirmation rather than proceeding.
- Write code the author can read and defend — clarity over cleverness. Comment the
  *why*, not the obvious *what*.
- When something is ambiguous, ask one sharp question rather than guessing.
- Prefer small, verifiable steps with a clear "definition of done" over large
  speculative builds.
