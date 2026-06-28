# Layer 4 — FakeCorp synthetic dataset (planned)

A fully synthetic demo network — sites, devices, interfaces, cables — used to
demonstrate the pipeline end-to-end. No real-world data, ever.

FakeCorp's org hierarchy (regions, site groups, sites, locations) lives in
`baselines/fakecorp.yaml` and is applied by the Layer 2 provisioning engine.
This directory is reserved for Layer 4 device-level data: racks, devices,
interfaces, and cables that sit on top of that baseline.
