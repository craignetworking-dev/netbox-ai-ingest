# Layer 2 — Provisioning Engine

A config-driven, dependency-aware engine that populates a NetBox instance from
declarative **baseline files**. The engine knows *how* to create NetBox
organization objects — idempotently, in the order NetBox's data model requires —
while per-client YAML baselines declare *what* should exist.

This is deliberately not a one-off population script. The same engine stands up
any environment's baseline; onboarding a new client is writing a new baseline
file, not changing code. The synthetic `fakecorp` baseline is simply the first
one the engine consumes.

## How it works

```
scaffold/apply.py  +  baselines/<name>.yaml  ->  populated NetBox
```

- **Engine** (`scaffold/`) — idempotent get-or-update, dependency ordering, and a
  registry that maps each supported object type to its NetBox endpoint and
  natural key.
- **Baselines** (`baselines/`) — human-editable YAML describing the desired
  organization hierarchy. References between objects are by slug, so baselines are
  portable across NetBox instances.

```bash
python -m scaffold.apply baselines/fakecorp.yaml            # apply
python -m scaffold.apply baselines/fakecorp.yaml --dry-run  # preview, no writes
```

## What it provisions

The organization and physical hierarchy that must exist before device instances
and cabling: **Regions, Site Groups, Sites, Locations** (buildings / floors /
rooms), plus **Tenancy** and the **DCIM** device-definition objects
(manufacturers, device roles, device types, port templates).

Objects are applied in NetBox's required dependency order, including
self-nesting types (a floor inside a building, a child region inside a parent).

## Idempotent by contract

Every object is get-or-update by slug: created if absent, patched only where it
drifts, left untouched otherwise. Running the engine twice against an unchanged
baseline makes zero changes. Re-runnability is a guarantee, not a side effect.

## Hard rule

Baselines contain **no real-world network data** — all demo data is synthetic.
See the repository root `CLAUDE.md`.
