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
    "tenant_groups": {
        "endpoint": "tenancy.tenant_groups",
        "natural_key": "slug",
        "required": ["name", "slug"],
        "refs": {"parent": "tenant_groups"},
    },
    "tenants": {
        "endpoint": "tenancy.tenants",
        "natural_key": "slug",
        "required": ["name", "slug"],
        "refs": {"group": "tenant_groups"},
    },
    "manufacturers": {
        "endpoint": "dcim.manufacturers",
        "natural_key": "slug",
        "required": ["name", "slug"],
        "refs": {},
    },
    "device_roles": {
        "endpoint": "dcim.device_roles",
        "natural_key": "slug",
        "required": ["name", "slug"],
        "refs": {},
    },
    "device_types": {
        "endpoint": "dcim.device_types",
        "natural_key": "slug",
        "required": ["manufacturer", "model", "slug"],
        "refs": {"manufacturer": "manufacturers"},
    },
}

# Fixed application order — inter-type foreign keys require this sequence.
# Tenancy comes before sites because sites can reference a tenant.
# Slice 2b (device-type templates) will require applier extension, not an entry here.
APPLY_ORDER = [
    "regions",
    "site_groups",
    "tenant_groups",
    "tenants",
    "sites",
    "locations",
    "manufacturers",
    "device_roles",
    "device_types",
]
