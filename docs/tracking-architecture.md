# OpenPlazma Tracking Architecture

This document is a readable companion to [ADR-0005](adr/0005-openplazma-tracking-layer-and-downstream-target-boundaries.md). It describes the tracking direction, the first local RunStore MVP, and the read-only local Observatory export.

## Why Tracking Exists

OpenPlazma runs should end in inspectable learning outputs: records, notebooks, artifacts, metrics, StudyRecords, reports, scenarios, and lineage. The tracking layer will make those outputs easier to inspect, replay, compare, and share.

The default endpoint is a local-first OpenPlazma RunStore. It is not a physical device, facility, machine, or reactor.

## Current State After M4.6a

Current public-demo contracts already describe:

- `STATIC_FIXTURE` source provenance.
- `LOCAL_SIGNAL_FILE` source provenance for local Python-only read-only imports.
- Safe `target` metadata.
- Public-demo `capabilities` where facility control is false.
- `kind`, `version`, and creation metadata on major JSON artifacts.
- StudyRecord files as human observation and learning artifacts.

The public demo remains `STATIC_FIXTURE`-only and does not fetch external fusion data. Local Python workflows may import local CSV signals as `LOCAL_SIGNAL_FILE` with SHA-256 provenance and schema-validation status.

## Planned Tracking Concepts

OpenPlazma-native tracking concepts:

- Scenario
- StudyTask
- StudyFlow
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
- ObservationModel
- EvidenceLink

Scenario and StudyTask define local learning context. StudyFlow defines an ordered path across Lab, Notebook, RunStore, Observatory, and Compare. RunRecord is the unit of tracked execution. ArtifactRecord describes saved inputs and outputs. MetricRecord describes timestamped or step-indexed numeric and structured measurements. StudyRecord remains the human observation artifact.

Future observation-model work should preserve theory-to-observation traceability: latent state or theory, observable phenomenon, diagnostic channel, raw signal, derived signal, inference, and claim. Theory variables and sensor signals are many-to-many, not one-to-one. See [Observation Model Direction](observation-model.md).

## Notebook As First Tracking Client

The local Python and local Jupyter notebook workflow is the first major client of the tracking layer.

Planned flow:

1. StudyFlow defines the ordered local path.
2. StudyTask defines prompts, suggested metrics, expected artifacts, limitations, source, target, and capabilities.
3. Lab creates an ExperimentContext.
4. Notebook reads the StudyFlow, StudyTask, and ExperimentContext.
5. Notebook starts an OpenPlazma Run.
6. Notebook logs StudyFlow, Scenario, StudyTask, SignalSeries, StudyRecord, plots, observations, hypotheses, metrics, and notebook outputs as artifacts.
7. RunStore keeps inspectable local records.
8. Observatory exports read-only local HTML for Runs, Artifacts, Metrics, events, and a two-Run comparison page.

Notebook-generated StudyRecord files can now be stored as local RunStore artifacts. Browser JupyterLite remains a STATIC_FIXTURE-only public demo and does not need persistent local RunStore writes.

## Target And Capability Boundaries

Current safe targets:

- `static_fixture`
- `local_run_store`

Current safe source providers:

- `STATIC_FIXTURE`
- `LOCAL_SIGNAL_FILE`

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

The first RunStore backend uses inspectable local files:

```text
.openplazma/
  runstore.json
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
    OPR-YYYYMMDD-node-a-abcdef123456/
      run.json
      config.json
      metrics.jsonl
      events.jsonl
      artifacts/
      manifest.json
```

Direction:

- JSON and JSONL first.
- Inspectable by default.
- Collision-resistant Run IDs for machine-scoped writers.
- `storeId`, `machineId`, `runGroupId`, and `partitionId` on Run records when scale-out workflows need them.
- Streaming and paged read APIs instead of fixed global caps.
- No binary-first run format in the local backend.
- No cloud dependency in the local backend.
- No account required in the local backend.

Removing fixed caps is not the same thing as claiming unlimited local filesystem scale. If a backend or operator needs resource ceilings, those ceilings must be explicit policy. They must not be hidden correctness constants that make long campaigns invalid by default.

The local filesystem backend is a safe default and compatibility layer. It records multi-machine identity and refuses to clear remote-host locks by PID inference, but it is not a scheduler, workflow engine, object-store ledger, or facility integration layer.

See [Local RunStore MVP](runstore-mvp.md), [Notebook tracking integration](notebook-tracking-integration.md), [StudyTask layer](studytask_layer.md), [Guided StudyFlow](guided-study-flow.md), [Observatory UI MVP](observatory-mvp.md), and [Observatory Compare MVP](observatory-compare-mvp.md) for Python API examples and current limitations.

See [Observation Model Direction](observation-model.md) for the future implementation policy around theory, diagnostics, raw signals, derived signals, inference, claims, simulator sweeps, and evidence links.

## Out Of Scope

The tracking architecture does not add:

- public data ingestion
- external network data fetching
- grading or scoring
- command/control actions
- validated simulation authority
- facility operation
- cloud account dependency
- external product dependency
- AI assist
- hidden metric, artifact, or byte-size caps as architecture
- live facility telemetry or facility control through RunStore records

OpenPlazma remains a local-first workbench for read-only plasma signal analysis, provenance tracking, comparison, and decision support.

## Next Milestones

- Extend local RunStore and Observatory records only after the read-only local workflow has been reviewed.
- Future Observatory work may add richer Reports and Lineage views after the local read-only workflow has been reviewed.
