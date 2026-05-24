# Tracking Notes

OpenPlazma will later introduce a local-first tracking layer. This note points to the current architecture documents; it does not describe implemented tracking code.

Architecture references:

- [ADR-0005: OpenPlazma Tracking Layer and Downstream Target Boundaries](adr/0005-openplazma-tracking-layer-and-downstream-target-boundaries.md)
- [Tracking architecture](tracking-architecture.md)

The Notebook Workbench is expected to be the first major client of the tracking layer.

Current Notebook-generated StudyRecord files are transitional artifacts. A future RunStore will store StudyRecords, SignalSeries, plots, and Notebook outputs as run artifacts.

OpenPlazma-native tracking concepts:

- Run
- RunRecord
- Artifact
- ArtifactRecord
- Metric
- MetricRecord
- Campaign
- Report
- Lineage
- Target
- Capability
- RunStore
- Observatory

The default endpoint of a run is an inspectable RunStore, not a physical device or facility.

Current public demo targets remain:

- `static_fixture`
- `local_run_store`

Future target categories are documented in ADR-0005. Public demo code does not implement them.

`facility_control_restricted` is not public core functionality and must not be implemented in public demo code.
