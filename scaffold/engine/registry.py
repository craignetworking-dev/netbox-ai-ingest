REGISTRY = {
    "regions": {
        "endpoint": "dcim.regions",
        "natural_key": "slug",
        "required": ["name", "slug"],
        "refs": {"parent": "regions"},
    },
    "site_groups": {
        "endpoint": "dcim.site_groups",
        "natural_key": "slug",
        "required": ["name", "slug"],
        "refs": {"parent": "site_groups"},
    },
    "sites": {
        "endpoint": "dcim.sites",
        "natural_key": "slug",
        "required": ["name", "slug", "status"],
        "refs": {"region": "regions", "group": "site_groups"},
    },
    "locations": {
        "endpoint": "dcim.locations",
        "natural_key": "slug",
        "required": ["name", "slug", "site"],
        "refs": {"site": "sites", "parent": "locations"},
    },
}

# Fixed application order — inter-type foreign keys require this sequence.
# Slice 2 types (tenant_groups, tenants, manufacturers, etc.) append here.
APPLY_ORDER = ["regions", "site_groups", "sites", "locations"]
