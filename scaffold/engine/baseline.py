from pathlib import Path

import yaml

from scaffold.engine.registry import REGISTRY


def load(path: str | Path) -> dict:
    path = Path(path)
    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a YAML mapping")

    # First pass: collect slugs per type and check for duplicates.
    slugs_by_type: dict[str, set[str]] = {}
    for type_key, objects in data.items():
        if type_key not in REGISTRY:
            raise ValueError(f"Unknown type '{type_key}' — add it to registry.py first")
        seen: set[str] = set()
        for obj in objects:
            slug = obj.get("slug")
            if not slug:
                raise ValueError(f"{type_key}: object missing 'slug': {obj}")
            if slug in seen:
                raise ValueError(f"{type_key}: duplicate slug '{slug}'")
            seen.add(slug)
        slugs_by_type[type_key] = seen

    # Second pass: required fields + ref resolution.
    for type_key, objects in data.items():
        entry = REGISTRY[type_key]
        for obj in objects:
            slug = obj.get("slug", "?")

            for field in entry["required"]:
                if field not in obj:
                    raise ValueError(
                        f"{type_key}/{slug}: missing required field '{field}'"
                    )

            # Refs are validated within the baseline only; refs to pre-existing
            # NetBox objects (target type absent from this file) are deferred to
            # apply time.
            for field, target_type in entry["refs"].items():
                if field not in obj:
                    continue
                ref_slug = obj[field]
                if target_type not in slugs_by_type:
                    continue
                if ref_slug not in slugs_by_type[target_type]:
                    raise ValueError(
                        f"{type_key}/{slug}: '{field}: {ref_slug}' not found in "
                        f"{target_type} — define it in the baseline or ensure it "
                        f"exists in NetBox before applying"
                    )

    return data
