# OpenPlazma Tracking Architecture

This document is a readable companion to [ADR-0005](adr/0005-openplazma-tracking-layer-and-downstream-target-boundaries.md). It describes the tracking direction, the first local RunStore MVP, and the read-only local Observatory export.

## Why Tracking Exists

OpenPlazma runs should end in inspectable learning outputs: records, notebooks, artifacts, metrics, StudyRecords, reports, scenarios, and lineage. The tracking layer will make those outputs easier to inspect, replay, compare, and share.

The default endpoint is a local-first OpenPlazma RunStore. It is not a physical device, facility, machine, or reactor.

## Current State After M4.6a

Current public-demo contracts already describe:

- `STATIC_FIXTURE` source provenance.
- Safe `target` metadata.
- Public-demo `capabilities` where facility control is false.
- `kind`, `version`, and creation metadata on major JSON artifacts.
- StudyRecord files as human observation and learning artifacts.

The public demo remains `STATIC_FIXTURE`-only and does not fetch external fusion data.

## Planned Tracking Concepts

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

RunRecord will become the unit of tracked execution. ArtifactRecord will describe saved inputs and outputs. MetricRecord will describe timestamped or step-indexed numeric and structured measurements. StudyRecord remains the human observation artifact.

## Notebook As First Tracking Client

The local Python and local Jupyter notebook workflow is the first major client of the tracking layer.

Planned flow:

1. Lab creates an ExperimentContext.
2. Notebook reads the ExperimentContext.
3. Notebook starts an OpenPlazma Run.
4. Notebook logs SignalSeries, StudyRecord, plots, observations, hypotheses, metrics, and notebook outputs as artifacts.
5. RunStore keeps inspectable local records.
6. Observatory exports read-only local HTML for Runs, Artifacts, Metrics, and events.

Notebook-generated StudyRecord files can now be stored as local RunStore artifacts. Browser JupyterLite remains a STATIC_FIXTURE-only public demo and does not need persistent local RunStore writes.

## Target And Capability Boundaries

Current safe targets:

- `static_fixture`
- `local_run_store`

Future possible targets:

- `public_data_source`
- `simulator`
- `compute_backend`
- `digital_twin`
- `facility_telemetry_readonly`

Restricted and non-public-core category:

- `facility_control_restricted`

Public demo contexts must keep:

```json
{
  "readData": true,
  "writeArtifacts": true,
  "runSimulation": false,
  "submitComputeJob": false,
  "readFacilityTelemetry": false,
  "controlFacility": false
}
```

Capabilities are safety and boundary metadata, not UI toggles.

## Local-First RunStore Direction

The first RunStore MVP uses inspectable local files:

```text
.openplazma/
  runs/
    OPR-YYYYMMDD-000001/
      run.json
      config.json
      metrics.jsonl
      events.jsonl
      artifacts/
        experiment-context.json
        signal-series.json
        study-record.json
        plot.png
      manifest.json
```

Direction:

- JSON and JSONL first.
- Inspectable by default.
- No binary-first run format in the MVP.
- No cloud dependency in the MVP.
- No account required in the MVP.

See [Local RunStore MVP](runstore-mvp.md), [Notebook tracking integration](notebook-tracking-integration.md), and [Observatory UI MVP](observatory-mvp.md) for Python API examples and current limitations.

## Out Of Scope

The tracking architecture does not add:

- public data ingestion
- real hardware control
- validated simulation
- facility operation
- cloud account dependency
- external product dependency
- AI assist

OpenPlazma remains a local-first experiment and learning system for safe plasma and fusion-data workflows.

## Next Milestones

- Extend local RunStore and Observatory records only after the read-only local workflow has been reviewed.
- Future Observatory work may add richer comparison of Runs, Artifacts, Reports, Metrics, and Lineage.
