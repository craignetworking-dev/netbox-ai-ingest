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

        for obj in objects:
            slug = obj["slug"]
            live = endpoint.get(slug=slug)

            if not live:
                if not dry_run:
                    payload = _build_payload(obj, entry, id_cache)
                    created = endpoint.create(**payload)
                    id_cache.setdefault(type_key, {})[slug] = created.id
                else:
                    # None sentinel: slug is "known" so children can pass topo-sort,
                    # but ID is unavailable until an actual write occurs.
                    id_cache.setdefault(type_key, {})[slug] = None
                counts[type_key]["created"] += 1

            else:
                id_cache.setdefault(type_key, {})[slug] = live.id
                diff = _diff(obj, live, entry, id_cache)
                if diff:
                    if not dry_run:
                        live.update(diff)
                    counts[type_key]["updated"] += 1
                else:
                    counts[type_key]["unchanged"] += 1

    return counts
