# Tracking Notes

OpenPlazma will later introduce a local-first tracking layer. This milestone only records the architecture direction; it does not implement tracking code.

The Notebook Workbench is expected to be the first major client of that layer.

Future OpenPlazma-native concepts:

- Run
- RunRecord
- Artifact
- ArtifactRecord
- Metric
- Campaign
- Report
- Lineage
- Target
- Capability
- RunStore
- Observatory

The default endpoint of a run is an inspectable RunStore, not a physical device or facility.

Public demo targets remain:

- `static_fixture`
- `local_run_store`

Future target categories may be documented later:

- `public_data_source`
- `simulator`
- `compute_backend`
- `digital_twin`
- `facility_telemetry_readonly`

`facility_control_restricted` is not public core functionality and must not be implemented in this milestone.

ADR-0005 will be created in a later milestone before tracking code is implemented.
