# Layer 3 — Slice 2 SPEC: LLM Structured Extraction + Validation

Marching orders for Layer 3 Slice 2. Read `CLAUDE.md`, `scaffold/SPEC.md`, and
`scaffold/SPEC-3.md` first; this is subordinate to them. Build Slice 2 only.

Slice 1 (identifier pseudonymizer) is complete: it turns a network doc into
pseudonymized text plus a local-only `ingest/identifiers.map.json`
(placeholder -> real value). Slice 2 adds the **LLM structuring step**: send the
pseudonymized text to Claude and get back a validated, structured device
inventory. Re-identification and emit-to-baseline are later slices.

## Purpose

This is the network+AI intersection made concrete, and it is a deliberate
training build. The goal is not just "call the Claude API" — it is to build a
**structured extraction pipeline with real validation**, and to hit and handle
the failure modes that separate a toy from a trustworthy pipeline.

The skills this slice exists to build:
- Structured output via **tool use** (typed output contract, not prose JSON).
- The failure modes of LLM extraction (hallucination, partial extraction,
  misattribution, placeholder-fidelity errors) and how to **detect** them.
- A layered **validation** approach — schema, referential, coverage,
  hallucination — cheapest checks first.

## Core mechanism: tool use as a typed output contract

Do NOT ask the model for JSON in prose and parse it out. Use tool use:

- Define ONE tool, `submit_network_inventory`, whose `input_schema` is the
  desired output shape. There is no implementation behind it — the tool exists
  solely to force the model's output into a typed shape. Harvest the arguments;
  the "call" is never executed.
- Force it: `tool_choice = {"type": "tool", "name": "submit_network_inventory"}`.
  This removes the model's option to answer in prose.
- `temperature = 0` (extraction, not creativity; makes output testable).
- Generous `max_tokens`; check `stop_reason` is `tool_use`, not `max_tokens`
  (a truncated tool_use block is a malformed-output failure).
- Read the result by FINDING the `tool_use` block by type, never by list index:
  `block = next(b for b in resp.content if b.type == "tool_use"); data = block.input`.

## Design principle: placeholders live in dedicated fields, never free text

Re-identification (a later slice) is a lookup of placeholder -> real value. If
placeholders appear inside free-text fields, re-identification must re-scan free
text for placeholders — reintroducing the pseudonymizer's detection-completeness
problem in reverse. Therefore:

- Every field that can carry a placeholder is a dedicated, structured field
  (`name`, `serial`, `mgmt_ip`, `connects_to_device`).
- Avoid free-text fields. The ONE exception is `source_line` (a validation
  artifact, see below), which is explicitly quarantined: excluded from
  re-identification and dropped before any emit.

## The extraction schema (tool input_schema)

`submit_network_inventory` with a top-level `devices` array. Per device:

- `name` (string, REQUIRED) — hostname placeholder EXACTLY as written
  (e.g. `HOST_001`). Verbatim: no case/punctuation/number changes; never invent
  a placeholder not present in the document.
- `role` (string enum, OPTIONAL) — one of
  `core-router | edge-router | dist-switch | access-switch`. The model
  normalizes messy source text to a canonical value; OMIT entirely if nothing
  maps. (Optional-enum: constrains the space without forcing a wrong pick.)
- `site` (string, OPTIONAL) — site name as written (e.g. `ATL HQ`). Omit if not
  stated.
- `rack_position` (string, OPTIONAL) — e.g. `A-01U01`. Omit if not stated.
- `serial` (string, OPTIONAL) — serial placeholder verbatim (e.g. `SERIAL_001`).
  Omit if not stated.
- `mgmt_ip` (string, OPTIONAL) — IP placeholder verbatim (e.g. `IP_001`), with no
  `/prefix`. Omit if not stated.
- `interfaces` (array, OPTIONAL) — see scope note; extracted best-effort in v1.
  Per interface: `name` (REQUIRED, e.g. `Gi0/1`), `connects_to_device`
  (OPTIONAL, placeholder verbatim), `connects_to_interface` (OPTIONAL).
- `source_line` (string, REQUIRED) — the exact line from the document where this
  device is defined, copied verbatim. Used for hallucination detection.

Required fields: ONLY `name` and `source_line`. Everything factual is optional —
a required factual field manufactures hallucination when the doc is silent.
Absence is honest data.

Schema descriptions carry the real instructions (the model reads them). The
verbatim/"omit if not stated"/"never invent" guidance lives in the field
`description`s, not in a separate prose prompt.

## Validation layer (the heart of this slice)

Run cheapest checks first. Each check maps to a specific failure mode.

1. **Schema validation** — tool use provides most of this; confirm the block is
   present and `stop_reason == "tool_use"`.
2. **Referential validation** — every placeholder in `name`, `serial`,
   `mgmt_ip`, and each interface `connects_to_device` MUST exist as a key/value
   in `identifiers.map.json`. Catches invented / malformed placeholders
   (`HOST-001`, `host_001`, `HOST_007`). This is the direct analog of the
   pseudonymizer's detection-completeness check, on the far side of the LLM.
3. **Coverage validation** — every `HOST_` placeholder present in the INPUT
   pseudonymized doc should appear as some device's `name`. A gap means partial
   extraction (devices silently dropped). Report gaps explicitly.
4. **Hallucination validation** — every `source_line` MUST be a substring of the
   input document. If it is not, the device was fabricated. (The model can
   occasionally fabricate the evidence too; the substring check still catches the
   common case cold.)

Validation output is a structured report (what passed, what failed, which
devices/placeholders). A failing check does not silently drop data — it surfaces.

## Scope: devices gated, interfaces observed

- **Gated (definition of done rests on these):** device-level fields — `name`,
  `role`, `site`, `serial`, `mgmt_ip` — extracted and passing referential,
  coverage, and hallucination validation on the synthetic fixture.
- **Observed, NOT gated:** `interfaces`. The schema includes interfaces and the
  model attempts them, but v1 does not certify interface correctness. Interface
  data is scattered across multiple regions of the doc (table, cable-plant
  section, per-device uplink blocks, prose), which is a distinct
  multi-region-assembly problem. Record what the model got right/wrong as
  observations for Slice 2b. Do not let interface handling block this slice.

Rationale: the NEW skills here are tool use + validation + round-trip. Interface
assembly is a second, orthogonal hard problem; isolating it keeps one variable
changing at a time (same discipline that made the Ansible slices debuggable).

## Hard rules carried forward

- **Pseudonymized text ONLY goes to the LLM.** Slice 2 operates on the output of
  Slice 1's pseudonymizer; real identifiers never leave the environment. Confirm
  the input to the LLM call contains placeholders, not real values.
- **No real-world data.** The fixture is the synthetic `sample_network_doc.txt`.
- **Credential custody.** The Anthropic API key lives in a git-ignored `.env`
  (never committed, never printed). `identifiers.map.json` stays git-ignored and
  local-only (now enforced in `.gitignore`).
- **Fail loud, not silent.** Validation surfaces problems; it never quietly drops
  a device or invents a value.

## Definition of done (Slice 2)

- [ ] `submit_network_inventory` tool defined; forced via `tool_choice`;
      `temperature=0`; result read by finding the `tool_use` block by type.
- [ ] Given the pseudonymized synthetic doc, the pipeline returns a structured
      device inventory conforming to the schema.
- [ ] **Referential validation** passes on device-level placeholder fields: every
      `name`/`serial`/`mgmt_ip` exists in `identifiers.map.json`.
- [ ] **Coverage validation** run: every `HOST_` placeholder in the input is
      accounted for as a device `name` (or the gap is reported).
- [ ] **Hallucination validation** passes: every `source_line` is a substring of
      the input doc.
- [ ] Determinism observed: two runs at `temperature=0` produce the same device
      set (note any variance).
- [ ] The LLM input is verified to contain placeholders, not real identifiers.
- [ ] Interfaces are extracted best-effort; observations recorded for Slice 2b
      (NOT gated).
- [ ] No secrets committed; `.env` and `identifiers.map.json` absent from
      `git status`.
- [ ] Committed:
      `Layer 3 Slice 2: LLM structured extraction (tool use) + validation`.

## Non-goals (later slices)

- Re-identification (placeholder -> real value round-trip) and emit to a Layer 2
  baseline — Slice 3.
- Interface-extraction hardening / multi-region assembly — Slice 2b.
- Cabling as first-class deduplicated objects (A-to-Z described from both ends) —
  a later slice; v1 only captures per-interface `connects_to_*` best-effort.
- An automated eval/metrics harness (precision/recall over a golden set) — a
  strong follow-up once extraction + validation exist; scoped as its own slice.

## Review checkpoints (where to slow down)

- **The LLM never sees real data.** Before the API call, confirm the payload is
  the pseudonymized text. This is the security-critical check.
- **Schema descriptions do the work.** The verbatim/omit/never-invent guidance is
  attached to fields, not floating in a prose prompt.
- **Validation surfaces, never hides.** A failed check produces a clear report;
  it does not drop or paper over data.
- **Required vs optional discipline.** Only `name` and `source_line` are
  required. If a factual field creeps into `required`, it will manufacture
  hallucination.
- **`source_line` is quarantined.** It carries placeholders but is a validation
  artifact — excluded from any future re-identification and dropped before emit.
