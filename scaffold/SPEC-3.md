# Layer 3 — AI Ingestion Pipeline SPEC

Marching orders for building Layer 3. Read `CLAUDE.md` and `scaffold/SPEC.md`
first; this spec is subordinate to them. Build slice 1 only (synthetic doc +
identifier pseudonymizer). Do not bleed into LLM structuring, re-identification,
or emit — those are later slices.

## What we are building

A **pseudonymize-then-LLM ingestion pipeline** that turns messy, unstructured
network documentation into structured NetBox objects — *safely*. The defining
principle: **sensitive identifiers are pseudonymized locally, before anything is
ever sent to an LLM.** Real hostnames, IPs, and serials never leave the operator's
environment in the clear.

This layer is the point of the whole project:
- It is the **network+AI intersection** — the distinctive credential. Layers 1–2
  are network automation; Layer 3 is a network engineer applying AI *with a
  security model*. That combination is the value proposition.
- It is the **NetSource delivery engine** — "Claude-powered network documentation
  cleanup" is the productized service. This pipeline is how that service runs.
- Its output feeds the **Layer 2 engine** — the pipeline emits a baseline YAML
  that the existing provisioning engine applies. Layer 3 does not duplicate
  Layer 2; it produces input for it. That seam is the architecture.

## Pipeline shape (full layer — for context, not all built now)

```
1. Synthetic input doc   messy, fully fabricated network doc (the test fixture)
2. Pseudonymize          local pass: sensitive identifiers -> stable placeholders,
                         reversible via a LOCAL-ONLY mapping. [SLICE 1 stops here]
3. LLM structure         send PSEUDONYMIZED text to Claude -> structured objects
4. Re-identify + emit     map placeholders back -> Layer 2 baseline YAML
```

Build order note: the synthetic doc (1) comes first because it is the fixture the
pseudonymizer (2) is developed and proven against. You cannot test a pseudonymizer
without something to pseudonymize.

## Threat model (the security thinking — read before building)

This pipeline exists because handing sensitive network docs to an LLM is a real
risk. The security model is deliberate and its boundaries are honest.

**What v1 protects — identifiers.** IPv4 addresses, hostnames, and serial numbers
are the identifying, exploitable, sensitive tokens. These are pseudonymized before
any LLM call.

**Where the security actually lives — two things, neither of them crypto:**
1. **Map custody.** The mapping (`placeholder -> real value`) never leaves the
   local environment. It is written local-only, gitignored, and never transmitted.
   The LLM sees only placeholders; the key to reverse them stays home. *This is
   the core security property.* If the map leaks, you are compromised regardless
   of placeholder format — so the map's locality is what matters, not the
   placeholder's unguessability.
2. **Detection completeness.** Every sensitive token must be caught and replaced.
   A single missed IP or hostname sent in the clear is the real leak. Rigor goes
   into detection coverage, not into obscuring already-caught tokens.

**Why deterministic mapping is correct and safe.** The same token maps to the
same placeholder every run (e.g. `10.1.1.1 -> IP_001` consistently). This is
required for correctness: the LLM must see that repeated mentions of a host are
the *same* host to structure relationships correctly; per-occurrence randomization
would destroy the structure the LLM exists to extract. Determinism is not a
weakness here — the adversary (anyone seeing the LLM traffic) does not have the
local map, so a stable placeholder is meaningless to them. Private (RFC 1918)
addresses cannot be brute-forced from structure, because private addressing is
arbitrary and carries no external truth to anchor to.

**Named, irreducible limitation — topology is exposed by design.** Pseudonymizing
*values* does not pseudonymize *relationships*. If the LLM sees that one host is a
gateway peering with an upstream that peers with a core, the topology's *shape*
leaks — because preserving that shape is exactly the pipeline's job. This cannot
be "solved" without defeating the purpose (an LLM cannot both structure a topology
and be blind to it). The honest boundary: **this pipeline protects identifiers,
not topology.** Topology shape ("a three-tier campus with a /24 access layer") is
generic and far less sensitive than identifiers ("core at 10.14.200.1, serial
FTX..., hostname atl-core-01"); the operator consents to an LLM seeing the shape,
not the identifiers. Public IPs are a partial exception (registered/geolocatable,
so more inferable) — flag them but do not over-engineer around them in v1.

**Explicitly NOT building (wrong axis or premature):**
- Keyed/HMAC hashing of placeholders — changes placeholder *format* but does
  nothing for the real threats (map custody, detection, topology leakage).
  Adds a key to manage (a new secret to leak) and non-human-readable placeholders
  (worse for debugging and client demos) for no security gain against this threat
  model. A documented v2 option ONLY if cross-run/cross-machine consistency
  without a shared map ever becomes a real requirement.
- Structural generalization (obscuring subnet sizes/roles) — defeats the
  pipeline's purpose; lossy; premature.

## Hard rules carried forward

- **No real-world data. Ever.** The input doc built here is fully synthetic —
  fabricated values in a realistic *structure*. Real rack-elevation and A-to-Z
  interface docs never enter the repo or the pipeline during development.
- The mapping file is **gitignored and local-only** — it must never be committed
  or transmitted.
- Output ultimately conforms to a Layer 2 baseline shape (later slice).

## Slice 1 scope (synthetic doc + identifier pseudonymizer)

Build exactly two things and prove them together:

### Part A — synthetic input document
A small, messy, **fully fabricated** network doc that mimics the shape of a real
device/interface document (the kind of thing a real A-to-Z or device spreadsheet
looks like — but invented). It must contain, in realistic messy form:
- fabricated hostnames (e.g. `core-sw-01`, `edge-rtr-02`)
- fabricated IPv4 addresses (RFC 1918, e.g. `10.1.1.1`, `192.168.20.5`)
- fabricated serial numbers (e.g. `FAKE-SN-00123`)
- some repetition (same host/IP mentioned more than once — to prove determinism)
Format: plain text or simple structured text (`.txt` / `.md` / a small CSV-like
block). Location: `ingest/samples/` (a new dir; synthetic fixtures live here).

### Part B — identifier pseudonymizer
A local module that:
- **Detects** the three sensitive identifier classes: IPv4 (regex), hostnames
  (pattern/heuristic), serial numbers (pattern). Start conservative and explicit;
  widening the detection set is a later slice.
- **Replaces** each detected token with a stable, deterministic, human-readable
  placeholder: `IP_001`, `HOST_001`, `SERIAL_001`, incrementing per class, with
  the SAME token always mapping to the SAME placeholder within a run.
- **Records** a mapping (`placeholder -> real value`) to a local-only file
  (gitignored). This is the reversal key for a later re-identification slice.
- **Returns/writes** the pseudonymized text.
Location: `ingest/pseudonymize.py` (+ `ingest/__init__.py` if not present).

## Definition of done (Slice 1)

- [ ] A synthetic sample doc exists under `ingest/samples/` — fully fabricated,
      contains hostnames + IPv4 + serials, with at least one repeated token.
- [ ] `pseudonymize.py` runs on the sample and produces pseudonymized text where
      **every** hostname, IPv4, and serial is replaced by a placeholder.
- [ ] Determinism proven: a repeated token gets the SAME placeholder every time;
      re-running produces identical output.
- [ ] The mapping is written to a local-only, gitignored file (verify it is in
      `.gitignore` and does NOT show in `git status`).
- [ ] Completeness check: no un-replaced sensitive token remains in the output
      (spot-check the sample; a missed token is the real failure mode).
- [ ] Committed (mapping file NOT committed):
      `Layer 3 Slice 1: identifier pseudonymizer + synthetic sample doc`.

## Non-goals (do not do in Slice 1)

- No LLM calls (that is the next slice — nothing goes to Claude yet).
- No re-identification / reversal tool (later slice; slice 1 only *records* the map).
- No baseline-YAML emit (later slice).
- No MAC addresses, VLAN names, free-text locations, or public-IP special-casing
  (detection-set widening is a later slice — v1 is IPv4 + hostname + serial).
- No keyed hashing, no structural generalization (see threat model).
- No real-world data.

## Review checkpoints (where the author slows down)

- **Detection completeness** — the make-or-break. Walk the pseudonymized output
  and confirm NO real identifier slipped through. A missed token is a silent leak.
  This is the security-critical check, analogous to the idempotency re-run proof.
- **Determinism** — confirm the same input token yields the same placeholder, and
  that a second run is byte-identical. Relationships depend on this.
- **Map custody** — confirm the mapping file is gitignored and absent from
  `git status`. The map leaking is the one thing that breaks the whole model.
- **Hostname detection scope** — hostnames are the hardest to pattern-match
  without over-matching (catching ordinary words). Confirm it catches the sample's
  hostnames without mangling normal prose; note any over/under-matching as a known
  edge for the widening slice.
