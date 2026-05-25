# Tracking Notes

OpenPlazma will later introduce a local-first tracking layer. This note points to the current architecture documents; it does not describe implemented tracking code.

Architecture references:

- [ADR-0005: OpenPlazma Tracking Layer and Downstream Target Boundaries](adr/0005-openplazma-tracking-layer-and-downstream-target-boundaries.md)
- [Tracking architecture](tracking-architecture.md)
- [Local RunStore MVP](runstore-mvp.md)
- [Notebook tracking integration](notebook-tracking-integration.md)
- [Observatory UI MVP](observatory-mvp.md)
- [Observatory Compare MVP](observatory-compare-mvp.md)

The Python SDK and local Notebook workflow are the first clients of the tracking layer.

Notebook-generated StudyRecord files remain learning artifacts. The local RunStore can now store StudyRecords, SignalSeries, and notebook outputs as run artifacts in local files.

The local Observatory can export read-only static HTML from local RunStore records, including an optional two-Run compare page. The public Pages demo remains browser/static and does not inspect a user's local `.openplazma/` directory.

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

Future target categories are documented in ADR-0005. Public demo code does not implement external targets.

`facility_control_restricted` is not public core functionality and must not be implemented in public demo code.
