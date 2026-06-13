# Local RunStore

The M5 RunStore is a local-first, inspectable tracking layer for Python and local Notebook workflows. It records Runs, metrics, artifacts, events, and manifests as JSON and JSONL files.

The local Observatory can read RunStore output, and the Python SDK can log read-only local signal imports. The RunStore itself does not add cloud sync, network data ingestion, AI assist, simulation, facility operation, or command/control actions.

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

## Integrity, Locking, And Scale Boundaries

The local RunStore is still file-based, but it fails closed for the main corruption cases that can happen during notebook use.

Writes and reads share a local `.openplazma/.write.lock` directory lock. The lock is re-entrant inside one thread, so internal read-after-write validation can run without deadlocking. Other threads or processes wait for the lock before reading or writing, which prevents readers from observing half-written `run.json`, `manifest.json`, `metrics.jsonl`, or `events.jsonl` state.

The lock owner records host, process id, token, and creation time. A lock from the same host with a dead owner pid is treated as stale and cleared. A malformed lock owner is cleared only after a grace period. A live local owner pid is not cleared automatically; callers wait until the lock is released or until the lock timeout is reached. A lock from another host is not cleared by PID inference.

RunStore metadata is written to `.openplazma/runstore.json` and includes a stable `storeId`, backend kind, and local machine identity. New Run records can also carry `runGroupId`, `machineId`, and `partitionId` so multiple machines can produce collision-resistant records for one logical campaign.

OpenPlazma no longer treats fixed metric-count, artifact-count, or artifact-byte constants as correctness boundaries. Scaling must be expressed through backend policy and through bounded APIs:

- `iter_metrics` and `iter_events` stream JSONL records.
- `iter_runs` scans runs without forcing a full-store materialization.
- `list_runs_page` returns stable cursor pages.
- `list_metrics_page` and `list_events_page` return bounded cursor pages for long Runs.
- `list_run_group` and `summarize_run_group` group machine or partition runs for one logical campaign.
- content-addressed artifact blobs store large payload bytes once under `.openplazma/blobs/sha256/...`, while Run manifests keep small artifact records and pointer files.
- `merge_run_store` imports another local RunStore without overwriting colliding Run IDs; identical run trees are skipped, different run trees fail closed.

JSON files are written through atomic replace. Multi-file Run mutations such as `log_metric`, `log_artifact`, `finish`, and `fail` snapshot the affected files and roll back if a later write step fails. JSONL files must end with a newline, malformed or truncated JSONL records are rejected with an explicit validation error, and artifact byte size plus SHA-256 metadata is validated on read.

Write paths update `run.json` through shallow RunRecord validation instead of calling the deep `load_run` consistency path. Deep validation still remains available through explicit read APIs, but logging one more metric or closing a Run does not materialize all prior metrics, events, and artifacts.

## Directory Layout

Each Run is written as inspectable files:

```text
.openplazma/
  runstore.json
  blobs/
    sha256/
      ab/
        abcdef...
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
    OPR-YYYYMMDD-node-a-abcdef123456/
      run.json
      config.json
      metrics.jsonl
      events.jsonl
      artifacts/
        large-signal.json
      manifest.json
```

For ordinary small JSON artifacts, `artifacts/<name>.json` remains the artifact body. For content-addressed artifacts, `artifacts/<name>.json` is a small `openplazma.artifact_pointer` JSON file whose `blobRef` points to the immutable blob under `.openplazma/blobs/sha256/...`.

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

for metric in op.iter_metrics(runs[0]["runId"]):
    ...

page = op.list_runs_page(page_size=100)
metric_page = op.list_metrics_page(runs[0]["runId"], page_size=1000)
event_page = op.list_events_page(runs[0]["runId"], page_size=1000)
group_summary = op.summarize_run_group("will-o-wisp-campaign")

artifact = run.log_artifact(
    "large_signal",
    "signal_blob",
    "large-signal.bin",
    content_addressed=True,
    media_type="application/octet-stream",
)
blob_path = op.load_artifact_blob(artifact)

merge_summary = op.merge_run_store("worker-a/.openplazma", ".openplazma")
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
- Multi-machine identity and collision-resistant IDs are recorded, but the default local filesystem backend is not a distributed workflow engine.
- No fixed default metric, artifact, or byte-size cap; operational resource ceilings must be explicit backend or operator policy.
- Content-addressed blobs deduplicate and validate large artifact bytes, but the local filesystem backend is still not an object-store ledger or repair engine.
- Local RunStore merge rejects colliding Run IDs unless the run directories are byte-identical; it does not remap historical IDs.
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
