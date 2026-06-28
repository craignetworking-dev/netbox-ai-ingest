# Layer 2 — Provisioning Engine SPEC

Marching orders for building Layer 2. Read `CLAUDE.md` first; this spec is
subordinate to it. Build the engine described here; populate only the Slice 1
data. Do not bleed into device instances, cables, IPAM, or other layers.

## What we are building

A **config-driven, dependency-aware NetBox provisioning engine**, not a one-off
population script. The engine knows *how* to create NetBox organization objects
idempotently and in the correct order. Per-client **baseline files** (YAML)
declare *what* should exist. FakeCorp is simply the first baseline the engine
consumes — proof the engine works, not special-cased code.

This separation is the point of the layer:
- It is the **NetSource delivery product** — onboarding a new client is "write
  their baseline YAML," not "modify the engine."
- It is the **credential** — the deliverable is "an idempotent, dependency-aware,
  config-driven NetBox provisioning engine," which is a far stronger interview
  sentence than "I populated NetBox."

## Engine / data separation

```
scaffold/
  apply.py            # entry point: load a baseline, apply it, report results
  engine/
    __init__.py
    client.py         # builds a pynetbox connection from env (.env)
    registry.py       # maps each object type -> endpoint, natural key, refs
    applier.py        # idempotent get-or-update + dependency ordering
    baseline.py       # load + validate a baseline YAML file
baselines/
  fakecorp.yaml       # the first (synthetic) baseline — Slice 1 data
```

`apply.py` usage:
```
python -m scaffold.apply baselines/fakecorp.yaml
python -m scaffold.apply baselines/fakecorp.yaml --dry-run
```

## Baseline schema (YAML)

A baseline is a mapping of object-type keys to lists of object definitions.
References to other objects are by **slug** (the natural key), never by ID — IDs
are environment-specific and would break portability across clients.

```yaml
# baselines/fakecorp.yaml — fully synthetic. No real-world data.
regions:
  - name: North America
    slug: north-america
  - name: US East
    slug: us-east
    parent: north-america          # -> region slug

site_groups:
  - name: Corporate
    slug: corporate

sites:
  - name: Atlanta HQ
    slug: atlanta-hq
    status: active
    region: us-east                # -> region slug (optional)
    group: corporate               # -> site_group slug (optional)
    # tenant: acme                 # -> tenant slug (optional; Slice 2)

locations:
  - name: Building A
    slug: atl-bldg-a
    site: atlanta-hq               # -> site slug (required)
  - name: Floor 1
    slug: atl-bldg-a-fl1
    site: atlanta-hq
    parent: atl-bldg-a             # -> location slug (self-nesting)
  - name: Server Room 101
    slug: atl-bldg-a-fl1-sr101
    site: atlanta-hq
    parent: atl-bldg-a-fl1
```

The loader must validate: required fields present, slugs unique within a type,
and every reference resolves to a slug defined earlier in the same baseline (or
already present in NetBox). On a missing reference, fail loudly with a clear
message — do not silently skip.

## Dependency order (hard requirement)

NetBox rejects a child whose parent does not yet exist. The engine applies object
**types** in this fixed order, and within self-nesting types applies **parents
before children**:

1. `regions`        (self-nesting)
2. `site_groups`    (self-nesting)
3. `tenant_groups`  (self-nesting)            ← Slice 2a
4. `tenants`        (-> tenant_group)         ← Slice 2a
5. `sites`          (-> region, site_group, tenant)
6. `locations`      (self-nesting; -> site, tenant)
7. `manufacturers`                            ← Slice 2a
8. `device_roles`                             ← Slice 2a
9. `device_types`   (-> manufacturer)         ← Slice 2a
10. device-type port/interface templates (-> device_type) ← Slice 2b

**Intra-type nesting:** within `regions`, `site_groups`, and `locations`, an
entry's `parent` must be created before the entry. Handle this with a
topological pass (apply entries whose parent is null or already applied, repeat
until none remain; if a pass makes no progress, error on the unresolved cycle).
Do not assume file order is correct — validate it.

## Idempotency contract

For every object, the applier must:
1. **Get** by natural key (`slug`).
2. If absent → **create**.
3. If present → compare the desired fields against the live object; **update**
   (PATCH) only the fields that differ; if nothing differs, leave it alone.
4. Track and report counts: `created`, `updated`, `unchanged`, per type.

The engine must be safe to run any number of times. A second run against an
unchanged baseline must report **0 created, 0 updated, everything unchanged**,
and exit 0. This re-run proof is the layer's definition of done.

`--dry-run` resolves and reports what *would* change without writing anything.

## Slice boundaries

**Slice 1 (this milestone):** build the full engine, but populate only the
organization + location hierarchy — `regions`, `site_groups`, `sites`,
`locations`. This already exercises every hard problem: inter-type ordering
(a site needs its region), intra-type nesting (a floor needs its building), and
idempotent re-runs. Get this correct and the rest is just more data.

**Slice 2a (next milestone, same engine, no refactor):** widen `fakecorp.yaml`
to add `tenant_groups`, `tenants`, `manufacturers`, `device_roles`, and bare
`device_types` (manufacturer + model + slug + u_height, no child templates).
These are all flat objects in the same shape Slice 1 already handles, so this
is registry entries + baseline data only — no applier changes.

**Slice 2b (separate milestone — requires extending the applier):** add
device-type port/interface templates, sourced from the community
`netbox-community/devicetype-library` rather than hand-authored. This is split
out from 2a deliberately: a device type carries child template objects
(interfaces, front/rear ports), a parent-with-children shape the flat applier
does not yet handle. 2b therefore needs a library fetch/parse step and applier
support for nested child objects — genuine new engine capability, not just data.
The baseline declares which device types to include; the engine sources their
full template definitions from the library (an upstream catalog it consumes, not
forks — mirroring how the deploy layer wraps netbox-docker).

## Definition of done (Slice 1)

- [ ] `python -m scaffold.apply baselines/fakecorp.yaml` creates the full
      region → site group → site → location tree.
- [ ] The hierarchy is visible and correct in the NetBox UI (`localhost:8000`).
- [ ] A second run reports 0 created, 0 updated, all unchanged, exit 0.
- [ ] `--dry-run` reports the same plan without writing.
- [ ] Adding a new object type later requires only a `registry.py` entry plus
      baseline data — no change to `applier.py`.
- [ ] Committed: `Layer 2: config-driven provisioning engine + FakeCorp org slice`.

## Non-goals (do not do these in Layer 2)

- No device instances, racks, cables, interfaces-on-devices — later layers.
- No IPAM, circuits, VPN, wireless, virtualization.
- Do **not** attempt to support every NetBox model. Support the types listed
  above with a clean extension point; widen by data, not speculation.
- No real-world data, ever. `fakecorp.yaml` is synthetic. (See `CLAUDE.md`.)

## Conventions

- Connection details and API token come from an untracked `.env`
  (`NETBOX_URL`, `NETBOX_TOKEN`). Never hardcode.
- Pin deps in `requirements.txt` (`pynetbox`, `PyYAML`, `python-dotenv`).
- Clear, defensible code: the author must be able to walk every line.
- Small, verifiable steps. Show the plan before large structural choices.
