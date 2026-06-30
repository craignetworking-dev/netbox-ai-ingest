# Layer 2 — Slice 2b SPEC: device-type port templates

Marching orders for Slice 2b. Read `CLAUDE.md` and `scaffold/SPEC.md` first;
this spec is subordinate to them. 2b is the first slice that requires extending
the **applier** — it is not data-only widening. Build it incrementally, prove
each step, and do not bleed into device instances, racks, cabling, or IPAM.

## Why 2b is different from everything before

Slices 1–2a handled **flat objects**: a single record identified by a global
`slug`, upserted by get-or-update. 2b introduces **parent objects with child
template collections** — a device type that carries front-port and rear-port
templates. Three properties make this genuinely new engine work:

1. **Children have no global slug.** A port template's identity is the pair
   `(parent device_type, name)`. The idempotency check becomes "get the port
   template named `X` *on this device type*," not "get by slug." A new,
   parent-scoped natural key.
2. **Front ports reference rear ports — a sibling reference resolved by name.**
   A front port maps to a specific rear-port position. This front↔rear pairing
   is the entire point: it models structured-cabling pass-through, so NetBox can
   trace a cable *through* a panel (switch → panel front → panel rear →
   provider). Rear ports must therefore be created before front ports, and each
   front port resolves its rear-port reference by name. A mini dependency-order
   problem nested inside one device type.
3. **The whole thing must stay idempotent at the child level.** A re-run finds
   existing child templates by their scoped key and changes nothing — same
   contract as Slice 1, one level deeper.

## Scope of this slice (2b-local)

Local panel device-types with front/rear port templates and correct pairing,
proven idempotent. That is the whole slice.

**Explicitly deferred (separate follow-on slices, reusing this same applier
extension):**
- **2b-library:** sourcing vendor device types + their interface/port templates
  from `netbox-community/devicetype-library`. Reuses the child-template handling
  built here; adds a fetch/parse/name-mapping layer on top.
- **Port generators:** baseline shorthand like `front_ports: {count: 48, ...}`
  that the engine expands. Right answer for real 48-port panels, but it is a
  second feature on top of the applier extension. Build explicit-list handling
  first; add the generator after.
- Interface templates for switches/routers (same child mechanism; comes with
  2b-library, since that is where those device types come from).

## Hard rules carried forward

- No real-world data. The panel proven here is **synthetic** — a small,
  illustrative patch panel, not a copy of any real site's equipment. (Real
  rack-elevation and A-to-Z interface documents never enter the repo.)
- Real vendor/generic model names are fine (public catalog data); instances,
  topology, and real port assignments are not.
- References by natural key, never by raw NetBox ID.

## Build order (incremental — prove each before the next)

### Step 0 — API probe ✅ COMPLETE (corrected after serializer introspection)
Verified against live NetBox 4.6.3. Initial probe conclusions about front-port
pairing were wrong — corrected here after introspecting `FrontPortTemplateSerializer`
directly inside the container.

**How the correct schema was found:** OPTIONS/schema endpoints return 403 for
token auth. NetBox 4.6 silently accepts unknown fields on create without erroring
— so a probe that sends wrong field names gets a 201 back, the fields are
silently dropped, and the round-trip looks like the pairing was set but is
unreadable. The only reliable source is the Django serializer itself. Always
verify field names by introspecting the serializer, not by API round-trip alone.

- Endpoints `dcim.rear_port_templates`, `dcim.front_port_templates` confirmed.
- Rear port create: `device_type` (id), `name`, `type` (e.g. `8p8c`, a choice
  field), `positions`.
- Front port create: `device_type` (id), `name`, `type`, and `rear_ports` — a
  **list of mapping objects**, not flat `rear_port`/`rear_port_position` fields.
  Each mapping: `{"position": <int>, "rear_port": <rear-port-template id>,
  "rear_port_position": <int, optional>}`. Example:
  `rear_ports=[{"position": 1, "rear_port": <rear_id>, "rear_port_position": 1}]`
- The pairing **is readable on GET** — it returns back populated. The initial
  "write-only" conclusion was wrong: it was caused by sending the non-existent
  field names `rear_port` and `rear_port_template`, which NetBox silently dropped.
- Scoped GET works via `devicetype_id` + `name`; returns `None` when absent.

### Step 1 — registry: child-template descriptors
Extend the `device_types` registry entry (or add a parallel structure) so the
engine knows a device type *may* carry child collections, each with:
- the child endpoint (`dcim.rear_port_templates`, `dcim.front_port_templates`)
- the scoped natural key (`name`, scoped to parent `device_type`)
- the parent ref field (`device_type`)
- intra-collection ordering (rear ports before front ports)
- front-port child: a by-name ref to a rear-port child (`rear_port`)

Keep this declarative, in the same registry-as-source-of-truth spirit as 2a.

### Step 2 — applier extension: child upsert
After the applier upserts a device type (existing behavior, unchanged), if that
type declares child collections, it then, in order:
1. Upserts **rear-port** templates: for each, get by `(device_type, name)`;
   create if absent; PATCH only changed fields if present; unchanged otherwise.
   Cache `name -> id` for this device type's rear ports.
2. Upserts **front-port** templates: resolve `rear_port` (by name) to the cached
   rear-port id and `rear_port_position`; then get/create/patch by
   `(device_type, name)`.

Track child create/update/unchanged counts and roll them into the per-type
report (e.g. a nested or suffixed line). Keep the existing flat path untouched —
device types *without* child collections must behave exactly as in 2a.

### Step 3 — baseline: one small synthetic panel
Add to `baselines/fakecorp.yaml` a single **4-port** patch-panel device type
(small enough to read in full; the mechanism is identical at 4 or 48 ports).
Shape (illustrative — confirm field names from Step 0):

```yaml
device_types:
  - manufacturer: generic
    model: Patch Panel 4-Port
    slug: generic-patch-panel-4
    u_height: 1
    rear_ports:
      - name: "1"
        type: 8p8c
        positions: 1
      - name: "2"
        type: 8p8c
        positions: 1
      - name: "3"
        type: 8p8c
        positions: 1
      - name: "4"
        type: 8p8c
        positions: 1
    front_ports:
      - name: "1"
        type: 8p8c
        rear_ports:
          - position: 1
            rear_port: "1"        # by name -> resolved to rear-port-template id
            rear_port_position: 1
      - name: "2"
        type: 8p8c
        rear_ports:
          - position: 1
            rear_port: "2"
            rear_port_position: 1
      - name: "3"
        type: 8p8c
        rear_ports:
          - position: 1
            rear_port: "3"
            rear_port_position: 1
      - name: "4"
        type: 8p8c
        rear_ports:
          - position: 1
            rear_port: "4"
            rear_port_position: 1
```

(Requires a `Generic` manufacturer — add it to `manufacturers` if not present.)

## Idempotency contract (Slice 2b)

**Verified API behavior (NetBox 4.6.3, confirmed by serializer introspection):**
front-port template pairing is the `rear_ports` field — a list of mapping
objects, **readable on GET**. The "write-only" framing in the earlier probe
was wrong and is retracted. See Step 0 for the corrected field schema.

**Consequences for the applier:**

- **Child identity is `(device_type, name)`** — get by scoped name, create if
  absent.
- **Rear ports diff normally** — readable fields (`type`, `positions`) are
  compared and PATCHed on change.
- **Front ports: pairing is set on create via `rear_ports` list.** On create,
  send `rear_ports=[{"position": <n>, "rear_port": <rear-port-template id>,
  "rear_port_position": <n>}]` with the rear-port ID resolved from the sibling
  cache by name. On re-run where the front port already exists by
  `(device_type, name)`, `type` is diffed normally. Diffing the `rear_ports`
  mapping list is deferred — it requires list-level comparison, not simple
  field equality, and is a bounded follow-up, not a blocker.

**Documented follow-up (not a blocker):** the applier does not yet reconcile
`rear_ports` mapping changes on re-run. A pairing changed manually in the UI
would not be detected. This is a known, scoped gap: it can be added later by
comparing the `rear_ports` list from the baseline against the live object's
`rear_ports` list. Named here so it is honest rather than hidden.

- Run 1 (apply): panel device type created, rear ports created, front ports
  created with correct `rear_ports` pairing.
- Run 2 (re-run): device type unchanged, all child templates found by
  `(device_type, name)` — **0 created, 0 updated, all unchanged, exit 0**.
- `--dry-run` reports the child plan without writing.

## Definition of done (Slice 2b-local)

- [ ] Step 0 probe confirms field names/behavior on live 4.6.3.
- [ ] Applier upserts device-type child templates (rear before front, front
      paired to rear by name), idempotently.
- [ ] Existing flat device types (Catalyst 9300, MX204, etc.) still apply
      unchanged — the extension does not regress 2a.
- [ ] `python -m scaffold.apply baselines/fakecorp.yaml` creates the panel with
      4 paired front/rear ports; visible and correctly paired in the NetBox UI
      (device type → Front Ports / Rear Ports, pairing shown).
- [ ] Re-run reports 0 changes across all types including child templates.
- [ ] Committed: `Layer 2 Slice 2b-local: device-type front/rear port templates with pairing`.

## Non-goals (do not do in 2b-local)

- No library sourcing (that is 2b-library).
- No port-count generators (explicit lists only this slice).
- No interface templates for switches/routers (comes with 2b-library).
- No device instances, racks, cables, IPAM.
- No real-world data; the panel is synthetic.

## Review checkpoints (where the author slows down)

- **The scoped natural-key lookup** — confirm get-by-`(device_type, name)`
  actually returns the right template and `None` when absent. This is the new
  idempotency primitive; if it is wrong, child re-runs will falsely create
  duplicates or falsely report changes.
- **Front→rear pairing** — verify in the NetBox UI (device type → Front Ports
  shows each front port's paired rear port) or by reading the `rear_ports` field
  on the fetched front-port-template object. The pairing is readable on GET.
  Confirm it persisted correctly at create; diffing the `rear_ports` mapping list
  on re-run is a documented follow-up, not yet implemented.
- **No regression on flat types** — the device types from 2a must still report
  unchanged on re-run after the extension lands.
