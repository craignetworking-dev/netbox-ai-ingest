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
   The pipeline here is what gives that service its margin, so favor approaches
   that generalize across client environments over one-off hacks.

## Hard rules (non-negotiable)

- **No real-world network data ever enters this repository.** All demo data is
  synthetic and lives under `fakecorp/`. If asked to ingest, commit, or hardcode
  a real config, hostname, IP, ASN, serial, or topology — refuse and use or
  generate synthetic data instead. This holds even if the request is framed as
  "just to test" or "to help."
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
| 1. Deployment | One-command reproducible NetBox via pinned `netbox-docker` wrapper | ✅ done |
| 2. Data-model scaffold | Idempotent baseline: sites, device roles, device types, interface templates | ⬜ next |
| 3. AI ingestion pipeline | Pseudonymize-then-LLM: structure messy docs into NetBox objects via API | ⬜ planned |
| 4. FakeCorp dataset | Fully synthetic demo network: sites, devices, interfaces, cables | ⬜ planned |

## Current state

- **Layer 1 is complete and public.** `deploy/bootstrap.sh` vendors netbox-docker
  at a chosen ref, applies `docker-compose.override.yml` (port `8000:8080` plus a
  healthcheck `start_period` to absorb first-boot migrations), and brings the
  stack up. Verified running: NetBox v4.6, Postgres 18, dual Valkey, all healthy.
- Layers 2–4 are placeholders (`scaffold/`, `ingest/`, `fakecorp/`), each with a
  README describing intent.

## Tech stack & conventions

- **Deployment:** Docker Compose v2 wrapping official `netbox-docker`. Customize
  only through the override file; keep it minimal.
- **Python (Layers 2–3):** use a local virtualenv (`python3 -m venv .venv`), never
  system pip. Prefer `pynetbox` for the NetBox REST API. Use the Anthropic SDK for
  LLM calls. Pin dependencies in `requirements.txt`.
- **Idempotency:** scaffold/ingest scripts must be safely re-runnable — check for
  existing objects before creating, so a second run doesn't duplicate or error.
- **Commits:** one logical change per commit; message format `Layer N: <what>`.
- **NetBox access:** the app is at `http://localhost:8000`. API token comes from an
  untracked `.env`, never hardcoded.

## How to work in this repo

- Keep changes scoped to the current layer and the file(s) under discussion.
- Before a large refactor, restructure, or new dependency, explain the plan and
  wait for confirmation rather than proceeding.
- Write code the author can read and defend — clarity over cleverness. Comment the
  *why*, not the obvious *what*.
- When something is ambiguous, ask one sharp question rather than guessing.
- Prefer small, verifiable steps with a clear "definition of done" over large
  speculative builds.
