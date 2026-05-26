# Local RunStore MVP

The M5 RunStore is a local-first, inspectable tracking layer for Python and local Notebook workflows. It records Runs, metrics, artifacts, events, and manifests as JSON and JSONL files.

This MVP is intentionally small. The local Observatory can read RunStore output, but the RunStore itself does not add cloud sync, external data ingestion, AI assist, simulation, facility operation, or real hardware control.

## Purpose

The RunStore lets a local notebook record what it did:

- which ExperimentContext it used
- which SignalSeries it inspected
- which StudyRecord it produced
- which metrics were logged
- which artifacts were saved

The first client is the Python SDK. The Lab and browser Workbench do not need to use the RunStore for the public demo to work.

M10 adds a guided StudyFlow example that logs StudyFlow, Scenario, StudyTask, ExperimentContext, SignalSeries, StudyRecord, and signal metrics into the same local RunStore layout.

## Local-First Behavior

By default, Runs are written under:

```text
.openplazma/
```

This directory is ignored by git. It is local output, not source code.

RunStore records do not require an account, cloud service, external sync, or external data fetch.

## Directory Layout

Each Run is written as inspectable files:

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
      manifest.json
```

## Python API Example

```python
import openplazma as op

ctx = op.load_experiment_context("notebooks/examples/sample-experiment-context.json")
signal = op.load_static_signal(
    repo_root=".",
    shot_id=ctx["shotRef"]["shotId"],
    signal_id=ctx["signals"][0]["signalId"],
)

with op.start_run(
    project="openplazma-public-demo",
    campaign="read-the-signal",
    run_type="notebook_analysis",
    context=ctx,
    config={"source": "local notebook"},
) as run:
    record = op.create_study_record(
        context=ctx,
        observations=[{"text": "Observed the selected STATIC_FIXTURE signal."}],
    )
    summary = op.summarize_signal(signal)
    op.log_context_signal_and_study_record(run, ctx, signal, record)
    run.log_metric("signal_point_count", summary["point_count"])
    run.log_metric("signal_min", summary["min"])
    run.log_metric("signal_max", summary["max"])
    run.log_metric("signal_mean", summary["mean"])
```

Read records back:

```python
runs = op.list_runs()
record = op.load_run(runs[0]["runId"])
metrics = op.load_metrics(runs[0]["runId"])
manifest = op.load_manifest(runs[0]["runId"])
```

See [Notebook tracking integration](notebook-tracking-integration.md) for the full local notebook workflow. See [Observatory UI MVP](observatory-mvp.md) for read-only local HTML inspection and [Observatory Compare MVP](observatory-compare-mvp.md) for comparing two local Runs.

## Safety And Scope

Current safe targets are:

- `static_fixture`
- `local_run_store`

Default capabilities keep:

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

The public demo remains `STATIC_FIXTURE`-only. The RunStore does not connect to external facilities, machines, reactors, hardware, or cloud services.

OpenPlazma is not a validated fusion simulator, not a reactor design tool, and not a real hardware control system.

## Limitations

- Local files only.
- JSON and JSONL only.
- Read-only local Observatory export and two-Run compare page only.
- No public data ingestion.
- No external data fetch.
- No cloud sync.
- No local notebook server launching.
- No JupyterHub integration.
- No AI assist.
- No toy physics.
- No real hardware instructions.
