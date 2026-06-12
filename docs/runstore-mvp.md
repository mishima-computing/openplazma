# Local RunStore MVP

The M5 RunStore is a local-first, inspectable tracking layer for Python and local Notebook workflows. It records Runs, metrics, artifacts, events, and manifests as JSON and JSONL files.

This MVP is intentionally small. The local Observatory can read RunStore output, and the Python SDK can log read-only local signal imports. The RunStore itself does not add cloud sync, network data ingestion, AI assist, simulation, facility operation, or command/control actions.

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

## Integrity, Locking, And Limits

The local RunStore is still a file-based MVP, but it now fails closed for the main corruption cases that can happen during notebook use.

Writes and reads share a local `.openplazma/.write.lock` directory lock. The lock is re-entrant inside one thread, so internal read-after-write validation can run without deadlocking. Other threads or processes wait for the lock before reading or writing, which prevents readers from observing half-written `run.json`, `manifest.json`, `metrics.jsonl`, or `events.jsonl` state.

The lock owner is recorded as `pid=<process id>`. A lock with a dead owner pid is treated as stale and cleared. A malformed lock owner is cleared only after a grace period. A live owner pid is not cleared automatically; callers wait until the lock is released or until the lock timeout is reached.

The current local limits are:

- metrics per Run: `100000`
- artifacts per Run: `10000`
- artifact file size: `64 MiB`

The SDK enforces these limits both when writing and when reading existing RunStore files. A RunStore that exceeds the limits is rejected instead of being partially loaded into memory.

JSON files are written through atomic replace. Multi-file Run mutations such as `log_metric`, `log_artifact`, `finish`, and `fail` snapshot the affected files and roll back if a later write step fails. JSONL files must end with a newline, and malformed or truncated JSONL records are rejected with an explicit validation error.

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

## Local Signal Import Example

Local Python workflows can import a user-provided CSV signal as `provider: "LOCAL_SIGNAL_FILE"` and then log it to the RunStore:

```python
import openplazma as op

imported = op.import_local_signal_csv(
    "loop_voltage.csv",
    signal_id="loop-voltage",
    label="Loop voltage",
    quantity="voltage",
    unit="V",
)

ctx = imported["context"]
signal = imported["signal"]
record = op.create_study_record(context=ctx, observations=["Reviewed imported local signal."])

with op.start_run(
    project="openplazma-local",
    campaign="local-signal-import",
    run_type="notebook_analysis",
    context=ctx,
) as run:
    op.log_context_signal_and_study_record(run, ctx, signal, record)
```

The import validates CSV shape and numeric samples, records the file SHA-256 digest, and keeps all facility-control capabilities false. It does not validate physical calibration or facility state.

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

The public demo remains `STATIC_FIXTURE`-only. Local Python workflows may log `LOCAL_SIGNAL_FILE` records. The RunStore does not connect to external facilities, machines, reactors, hardware, or cloud services.

OpenPlazma is read-only analysis and decision support. It can preserve evidence, assumptions, metrics, and limitations for qualified review, but it is not a command/control system or a standalone authority for safety-critical operation or reactor design decisions.

## Limitations

- Local files only.
- JSON and JSONL only.
- File-based lock, not a database transaction log.
- Read-only local Observatory export and two-Run compare page only.
- No automatic repair of corrupted RunStore records.
- No public data ingestion.
- No external network data fetch.
- No cloud sync.
- No local notebook server launching.
- No JupyterHub integration.
- No AI assist.
- No predictive physics model in this MVP.
- No command/control actions.
- No hazardous operating procedures.
