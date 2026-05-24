# OpenPlazma Tracking Architecture

This document is a readable companion to [ADR-0005](adr/0005-openplazma-tracking-layer-and-downstream-target-boundaries.md). It describes the tracking direction and the first local RunStore MVP.

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

The Notebook Workbench is expected to be the first major client of the tracking layer.

Planned flow:

1. Lab creates an ExperimentContext.
2. Notebook reads the ExperimentContext.
3. Notebook starts an OpenPlazma Run.
4. Notebook logs SignalSeries, StudyRecord, plots, observations, hypotheses, metrics, and notebook outputs as artifacts.
5. RunStore keeps inspectable local records.
6. Observatory later compares Runs, Artifacts, Reports, Metrics, and Lineage.

Notebook-generated StudyRecord files in the current project are transitional artifacts. A future RunStore will store StudyRecords, SignalSeries, plots, and Notebook outputs as run artifacts.

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

See [Local RunStore MVP](runstore-mvp.md) for Python API examples and current limitations.

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

- Extend local RunStore records only after the MVP has been reviewed.
- Connect Notebook Workbench outputs to RunStore in a later milestone.
- Build Observatory later for comparing Runs, Artifacts, Reports, Metrics, and Lineage.
