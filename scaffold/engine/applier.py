import pynetbox

from scaffold.engine.registry import APPLY_ORDER, REGISTRY


def _get_endpoint(nb: pynetbox.api, endpoint_path: str):
    """Navigate nb.<app>.<resource> from a dotted string like 'dcim.regions'."""
    app, resource = endpoint_path.split(".")
    return getattr(getattr(nb, app), resource)


def topo_sort(type_key: str, objects: list[dict], entry: dict) -> list[dict]:
    """
    Return objects sorted so parents precede children within a self-nesting type.
    Non-self-nesting types are returned as-is.
    Raises ValueError loudly if a parent reference never resolves (cycle or typo).
    """
    # Find the field whose ref points back to this same type (e.g. regions.parent -> regions).
    self_ref_field = next(
        (f for f, t in entry["refs"].items() if t == type_key), None
    )
    if self_ref_field is None:
        return objects  # no self-nesting; inter-type ordering is handled by APPLY_ORDER

    ordered: list[dict] = []
    remaining = list(objects)
    applied: set[str] = set()

    while remaining:
        progress = False
        next_remaining: list[dict] = []
        for obj in remaining:
            parent_slug = obj.get(self_ref_field)
            if parent_slug is None or parent_slug in applied:
                ordered.append(obj)
                applied.add(obj["slug"])
                progress = True
            else:
                next_remaining.append(obj)
        if not progress:
            stuck = [obj["slug"] for obj in next_remaining]
            raise ValueError(
                f"{type_key}: parent reference cycle or unresolvable parent for: {stuck}"
            )
        remaining = next_remaining

    return ordered


def _live_val(live_obj, field):
    """
    Extract a scalar from a live pynetbox field for comparison.
    pynetbox returns choice fields (e.g. status) as ChoiceValue objects whose
    .value attribute holds the raw key ("active") that the baseline uses.
    """
    val = getattr(live_obj, field, None)
    if val is None:
        return None
    if hasattr(val, "value"):  # ChoiceValue
        return val.value
    return val


def _build_payload(obj: dict, entry: dict, id_cache: dict) -> dict:
    """
    Build a create payload, resolving every ref slug to its NetBox ID.
    Raises if a ref can't be resolved — that means dependency ordering is wrong.
    """
    payload = {}
    for field, val in obj.items():
        if field in entry["refs"]:
            ref_type = entry["refs"][field]
            resolved_id = id_cache.get(ref_type, {}).get(val)
            if resolved_id is None:
                raise ValueError(
                    f"Cannot resolve ref '{field}: {val}' ({ref_type}) — "
                    f"ensure the referenced object is created before this one"
                )
            payload[field] = resolved_id
        else:
            payload[field] = val
    return payload


def _diff(desired: dict, live, entry: dict, id_cache: dict) -> dict:
    """
    Return only the fields that differ between desired and live, ready for PATCH.

    Ref fields are compared by ID. If the desired ref's ID is None (a dry-run
    sentinel for an object that would be created), that field is skipped —
    we conservatively assume no change rather than failing.

    Known limitation (dry-run only): in a mixed create/update run, an existing
    object whose ref field points to a not-yet-created object will have that ref
    field skipped in the diff. The change will be under-reported (shown as
    unchanged when it may actually need updating). Real applies are unaffected —
    by the time _diff runs in non-dry-run mode, the referenced object has already
    been created and its ID is in id_cache.
    """
    changes = {}
    for field, desired_val in desired.items():
        if field == "slug":
            continue  # natural key; never patched
        if field in entry["refs"]:
            ref_type = entry["refs"][field]
            desired_id = id_cache.get(ref_type, {}).get(desired_val)
            if desired_id is None:
                continue  # dry-run: ref not yet created; skip comparison
            live_ref = getattr(live, field, None)
            live_id = live_ref.id if live_ref else None
            if desired_id != live_id:
                changes[field] = desired_id
        else:
            if desired_val != _live_val(live, field):
                changes[field] = desired_val
    return changes


def _build_child_payload(
    obj: dict, child_desc: dict, parent_id: int, sibling_caches: dict
) -> dict:
    """
    Build a create payload for a child template object.
    For children with a mapping_list (e.g. front_ports.rear_ports), builds the
    list with sibling refs resolved to IDs from sibling_caches.
    """
    payload = {child_desc["parent_ref"]: parent_id}
    mapping_list_desc = child_desc.get("mapping_list")
    for field, val in obj.items():
        if mapping_list_desc and field == mapping_list_desc["field"]:
            sibling_ref = mapping_list_desc["sibling_ref"]
            sibling_cache = sibling_caches.get(sibling_ref["collection"], {})
            resolved = []
            for mapping in val:
                resolved_mapping = {}
                for mk, mv in mapping.items():
                    if mk == sibling_ref["key"]:
                        resolved_id = sibling_cache.get(mv)
                        if resolved_id is None:
                            raise ValueError(
                                f"Cannot resolve sibling ref '{mk}: {mv}' from "
                                f"{sibling_ref['collection']} — was it created?"
                            )
                        resolved_mapping[mk] = resolved_id
                    else:
                        resolved_mapping[mk] = mv
                resolved.append(resolved_mapping)
            payload[field] = resolved
        else:
            payload[field] = val
    return payload


def _diff_child(obj: dict, live, child_desc: dict) -> dict:
    """
    Return only the diffable fields that differ between desired and live.
    Fields not in diffable (e.g. front-port rear_ports mapping list) are not
    compared — diffing the mapping list is a deferred follow-up per spec.
    """
    changes = {}
    for field in child_desc["diffable"]:
        if field in obj and obj[field] != _live_val(live, field):
            changes[field] = obj[field]
    return changes


def _apply_child_collection(
    child_desc: dict,
    child_objects: list[dict],
    parent_id: int | None,
    nb: pynetbox.api,
    sibling_caches: dict,
    dry_run: bool,
) -> tuple[dict, dict]:
    """
    Upsert one child collection (rear_ports or front_ports) for one device type.

    Children are identified by scoped natural key (devicetype_id + name).
    Sibling refs (rear_port resolved by name) come from sibling_caches.
    Returns (counts, name->id cache) for this collection.
    """
    endpoint = _get_endpoint(nb, child_desc["endpoint"])
    natural_key = child_desc["natural_key"]
    counts = {"created": 0, "updated": 0, "unchanged": 0}
    cache: dict[str, int | None] = {}

    for obj in child_objects:
        name = obj[natural_key]

        # If the parent was "would create" in dry-run, its id is unknown;
        # all children must also be created — no point querying NetBox.
        # Sibling refs (e.g. rear_port name->id) are not resolved here — consistent
        # with the dry-run under-reporting noted in _diff. Real applies unaffected.
        if parent_id is None:
            cache[name] = None
            counts["created"] += 1
            continue

        live = endpoint.get(devicetype_id=parent_id, **{natural_key: name})

        if not live:
            if not dry_run:
                payload = _build_child_payload(obj, child_desc, parent_id, sibling_caches)
                created = endpoint.create(**payload)
                cache[name] = created.id
            else:
                cache[name] = None
            counts["created"] += 1
        else:
            cache[name] = live.id
            diff = _diff_child(obj, live, child_desc)
            if diff:
                if not dry_run:
                    live.update(diff)
                counts["updated"] += 1
            else:
                counts["unchanged"] += 1

    return counts, cache


def apply(baseline: dict, nb: pynetbox.api, dry_run: bool = False) -> dict:
    """
    Apply all objects in baseline to NetBox in dependency order.

    For each object: get by slug, create if absent, PATCH only changed fields
    if present, leave unchanged if identical. Returns per-type counts of
    {created, updated, unchanged}.

    dry_run=True performs all reads and comparisons but no writes.
    """
    counts: dict[str, dict[str, int]] = {}

    # Maps type_key -> {slug -> id}.
    # In dry-run, "would create" objects are stored with id=None so downstream
    # topo-sort passes and ref existence checks still work, but we skip ref-field
    # comparison for them (we don't know the ID yet).
    id_cache: dict[str, dict[str, int | None]] = {}

    for type_key in APPLY_ORDER:
        if type_key not in baseline:
            continue

        entry = REGISTRY[type_key]
        endpoint = _get_endpoint(nb, entry["endpoint"])
        objects = topo_sort(type_key, baseline[type_key], entry)
        counts[type_key] = {"created": 0, "updated": 0, "unchanged": 0}
        child_keys = {c["key"] for c in entry.get("children", [])}

        for obj in objects:
            slug = obj["slug"]
            live = endpoint.get(slug=slug)

            if not live:
                if not dry_run:
                    parent_obj = {k: v for k, v in obj.items() if k not in child_keys}
                    payload = _build_payload(parent_obj, entry, id_cache)
                    created = endpoint.create(**payload)
                    parent_id = created.id
                    id_cache.setdefault(type_key, {})[slug] = parent_id
                else:
                    # None sentinel: slug is "known" so downstream topo-sort passes,
                    # but ID is unavailable until an actual write occurs.
                    parent_id = None
                    id_cache.setdefault(type_key, {})[slug] = None
                counts[type_key]["created"] += 1

            else:
                parent_id = live.id
                id_cache.setdefault(type_key, {})[slug] = parent_id
                parent_obj = {k: v for k, v in obj.items() if k not in child_keys}
                diff = _diff(parent_obj, live, entry, id_cache)
                if diff:
                    if not dry_run:
                        live.update(diff)
                    counts[type_key]["updated"] += 1
                else:
                    counts[type_key]["unchanged"] += 1

            # Upsert child collections declared in registry and present in baseline.
            if child_keys:
                sibling_caches: dict[str, dict] = {}
                for child_desc in entry["children"]:
                    child_key = child_desc["key"]
                    child_objects = obj.get(child_key, [])
                    if not child_objects:
                        continue
                    child_counts, child_cache = _apply_child_collection(
                        child_desc, child_objects, parent_id, nb, sibling_caches, dry_run
                    )
                    sibling_caches[child_key] = child_cache
                    if child_key not in counts:
                        counts[child_key] = {"created": 0, "updated": 0, "unchanged": 0}
                    for k, v in child_counts.items():
                        counts[child_key][k] += v

    return counts
