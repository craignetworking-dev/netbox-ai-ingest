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
        # Ordered child collections. Applied after the parent device_type upsert.
        # Types without a "children" key follow the existing flat path unchanged.
        "children": [
            {
                "key": "rear_ports",
                "endpoint": "dcim.rear_port_templates",
                "natural_key": "name",       # scoped to parent device_type
                "parent_ref": "device_type", # field name in create/filter
                "diffable": ["type", "positions"],
            },
            {
                "key": "front_ports",
                "endpoint": "dcim.front_port_templates",
                "natural_key": "name",
                "parent_ref": "device_type",
                "diffable": ["type"],
                # rear_ports is a list of mapping dicts built on create.
                # Within each mapping, "rear_port" is a sibling name resolved to
                # a rear-port-template id from the rear_ports sibling cache.
                # Diffing the rear_ports list on re-run is a deferred follow-up.
                "mapping_list": {
                    "field": "rear_ports",
                    "sibling_ref": {"key": "rear_port", "collection": "rear_ports"},
                },
            },
        ],
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
