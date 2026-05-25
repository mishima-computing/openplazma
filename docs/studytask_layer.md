# Scenario And StudyTask Layer

M9 adds the first OpenPlazma Scenario and StudyTask layer.

The layer defines what a learner should observe, which artifacts should be produced, which metrics are suggested, and how a local Notebook workflow can connect a learning task to the RunStore and Observatory.

M10 adds a first StudyFlow companion for this layer. See [Guided StudyFlow](guided-study-flow.md).

## Purpose

A Scenario is a named learning context. A StudyTask is a concrete task inside that Scenario.

A StudyFlow is an ordered path through one or more StudyTasks and the local OpenPlazma surfaces used to complete them.

The first Scenario is:

- `read-the-signal`

The first StudyTask is:

- `read-the-signal-static-v0.1`

Both are `STATIC_FIXTURE`-only and safe for public educational use.

## Relationship To Notebook And RunStore

The local StudyTask workflow connects:

1. StudyTask JSON defines prompts, suggested metrics, required artifacts, limitations, source, target, and capabilities.
2. Notebook or local Python loads the StudyTask.
3. Notebook reads the ExperimentContext named by the StudyTask.
4. Notebook loads the selected `STATIC_FIXTURE` SignalSeries.
5. Notebook writes observations and a hypothesis using the StudyTask prompts.
6. Notebook creates a StudyRecord.
7. Notebook starts a local Run.
8. RunStore logs the StudyTask, ExperimentContext, SignalSeries, StudyRecord, and suggested metrics.
9. Observatory can display the StudyTask as a normal artifact.

The public browser demo does not need persistent local RunStore writes for this workflow to exist.

## Local Workflow

From the repository root:

```sh
rm -rf .openplazma
python notebooks/examples/read_the_signal_task.py
```

The example writes a local Run under:

```text
.openplazma/runs/OPR-YYYYMMDD-000001/
```

Inspect it with the local Observatory:

```sh
python scripts/export-observatory.py --run-store .openplazma
```

Then open:

```text
.openplazma/observatory/index.html
```

## Artifacts Logged

The local StudyTask example logs:

- `study_task`
- `experiment_context`
- `signal_series`
- `study_record`

## Suggested Metrics

The Read the Signal task suggests:

- `signal_point_count`
- `signal_min`
- `signal_max`
- `signal_mean`

These are learning workflow metrics, not validated scientific results.

## Boundaries

StudyTask definitions include source, target, capability, and limitation metadata.

Current safe targets remain:

- `static_fixture`
- `local_run_store`

Current StudyTask capabilities keep:

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

## Limitations

- `STATIC_FIXTURE` data only.
- No public data ingestion.
- No grading or scoring.
- No cloud sync.
- No hosted Observatory.
- No AI assist.
- No real hardware instructions.
- Not a validated fusion simulator.
- Not a reactor design tool.
- Not a real hardware control system.
