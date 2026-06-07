# ADR-0005: OpenPlazma Tracking Layer and Downstream Target Boundaries

## Status

Proposed

## Context

OpenPlazma is built around a safe Lab-to-Notebook flow:

- The Lab creates an ExperimentContext.
- The Notebook Workbench reads the ExperimentContext.
- The current notebook examples can create StudyRecord files.
- Current public-demo records use `STATIC_FIXTURE` data only.
- Local Python workflows can import CSV signals as `LOCAL_SIGNAL_FILE` with SHA-256 provenance and schema-validation status.

M4.6a made the current contracts tracking-ready by clarifying source provenance, safe targets, capabilities, artifact kind and version fields, and public-demo boundaries. Before implementing a RunStore, OpenPlazma needs a clear architecture decision for what a tracked run means and what downstream targets are allowed to imply.

OpenPlazma is a read-only analysis and decision-support workbench. It can organize evidence, provenance, assumptions, comparisons, and validation boundaries for qualified human review, but it is not a command/control system and is not a standalone authority for safety-critical operation or reactor design decisions. OpenPlazma does not provide instructions for high-voltage systems, vacuum systems, lasers, radiation sources, hazardous materials, physical plasma hardware, or real facility operation.

## Decision

OpenPlazma will introduce a local-first tracking layer for Runs, Artifacts, Metrics, Reports, Campaigns, Lineage, Targets, Capabilities, and an inspectable RunStore.

The Notebook Workbench is the first major client of this layer.

The default downstream endpoint of a Run is an inspectable OpenPlazma RunStore, not a physical device, facility, machine, or reactor.

OpenPlazma remains connectable by design through explicit Target and Capability metadata, but public core functionality does not include facility control.

## Rationale

OpenPlazma already has the foundation of a tracking flow: Lab -> ExperimentContext -> Notebook -> StudyRecord. That flow should become inspectable, replayable, comparable, and shareable without assuming any physical downstream system exists.

M4.6a established contract fields that make this possible, including `target`, `capabilities`, `kind`, `version`, `createdAt`, and explicit `STATIC_FIXTURE` source provenance. The read-only decision-support boundary also permits `LOCAL_SIGNAL_FILE` records for local Python analysis when provenance, validation status, and limitations are preserved.

Future RunStore work needs boundary decisions before implementation so that tracked records do not casually imply facility operation, validated simulation, or reactor design. Future integrations must be described explicitly through Target and Capability metadata rather than assumed from project context.

The current public demo remains `STATIC_FIXTURE`-only. Local Python analysis may import local CSV signal files, but that does not add public-data ingestion, network fetches, facility telemetry, or command/control behavior.

## OpenPlazma Tracking Vocabulary

Run:
A tracked execution or analysis event.

RunRecord:
Inspectable metadata describing a Run.

Artifact:
A saved input or output from a Run.

ArtifactRecord:
Metadata describing an Artifact, including type, location, checksum, provenance, and producing Run.

Metric:
A numeric or structured measurement logged during a Run.

MetricRecord:
A timestamped or step-indexed metric entry.

Campaign:
A named collection of related Runs.

Report:
A human-readable summary of observations, hypotheses, metrics, artifacts, and limitations.

Lineage:
The relationship between source data, derived signals, notebooks, StudyRecords, plots, and reports.

Target:
The downstream endpoint or context a Run is associated with.

Capability:
Explicit metadata describing what a Run is allowed to do.

RunStore:
A local-first, inspectable store of RunRecords, artifacts, metrics, events, and reports.

Observatory:
A future UI or workspace for exploring Runs, Artifacts, Reports, Metrics, and Lineage.

## Target Categories

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

Target rules:

- `static_fixture` is the current public demo target.
- `local_run_store` is the expected default tracking endpoint.
- `public_data_source` must require provenance, source terms, and limitations.
- `simulator` and `compute_backend` may be introduced only in reviewed future milestones.
- `digital_twin` is future research infrastructure, not public demo scope.
- `facility_telemetry_readonly` is read-only and partner-specific.
- `facility_control_restricted` is not public core functionality, must not be implemented in public demo code, must not be enabled by default, and requires separate governance if ever discussed.

## Capability Model

The intended public-demo capability shape is:

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

Public demo contexts must keep `controlFacility` false.
Public demo contexts must keep `readFacilityTelemetry` false.
Public demo contexts must keep `submitComputeJob` false.
Public demo contexts must keep `runSimulation` false unless a future reviewed safe virtual model milestone changes this.

Capabilities are safety and boundary metadata. They are not UI toggles.

## Initial Local RunStore Direction

The future RunStore should start as an inspectable local directory. A possible MVP layout is:

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

RunStore direction:

- JSON and JSONL first.
- Inspectable by default.
- No binary-first run format in the MVP.
- No cloud dependency in the MVP.
- No account required in the MVP.
- Future sync and export adapters may be discussed later, but are out of scope for ADR-0005 implementation.

## Notebook Relationship

The Notebook Workbench is the first major future client of the tracking layer.

Expected future flow:

1. Lab creates an ExperimentContext.
2. Notebook reads the ExperimentContext.
3. Notebook starts an OpenPlazma Run.
4. Notebook logs SignalSeries, StudyRecord, plots, observations, hypotheses, metrics, and notebook outputs as artifacts.
5. RunStore keeps inspectable local records.
6. Observatory later compares Runs, Artifacts, Reports, Metrics, and Lineage.

Notebook-generated StudyRecords in the current project are transitional artifacts. A future RunStore will store StudyRecords, SignalSeries, plots, and Notebook outputs as run artifacts.

## Lineage Examples

Current public demo lineage:

```text
STATIC_FIXTURE signal
-> ExperimentContext
-> Notebook Workbench
-> StudyRecord
-> future RunRecord
-> future Report
```

Current local file lineage:

```text
LOCAL_SIGNAL_FILE CSV
-> schema-validated SignalSeries
-> ExperimentContext
-> local notebook analysis Run
-> metrics
-> StudyRecord
-> Report
```

Future public-data lineage:

```text
public_data_source shot metadata
-> derived SignalSeries
-> ExperimentContext
-> Notebook analysis Run
-> metrics
-> StudyRecord
-> Report
```

The future public-data example is architectural only and is not implemented today.

## Consequences

- RunRecord will become the unit of tracked execution.
- ArtifactRecord will track saved inputs and outputs.
- MetricRecord will track numeric and structured summaries.
- StudyRecord remains the human observation artifact.
- ExperimentContext remains the Lab-to-Notebook bridge.
- SignalSeries remains a signal artifact.
- Notebook outputs will become artifacts.
- RunStore will be local-first and inspectable.
- Observatory will be a later UI for comparing Runs, Artifacts, Reports, Metrics, and Lineage.
- Public demo targets are limited to `static_fixture` and `local_run_store`.
- Local Python workflows may use `LOCAL_SIGNAL_FILE` source provenance for read-only signal files.
- Future public-data milestones may introduce `public_data_source` with provenance.
- Future research milestones may discuss `simulator`, `compute_backend`, `digital_twin`, and `facility_telemetry_readonly`.
- Facility control is excluded from public core functionality.

## Non-Goals

ADR-0005 does not add public data ingestion, external network data fetching, simulation, AI assist, JupyterHub, local notebook server launching, facility operation, or hardware integration.
