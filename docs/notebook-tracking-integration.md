# Notebook Tracking Integration

M6 makes local Python and local Jupyter notebooks a first-class client of the OpenPlazma RunStore.

The public browser demo remains `STATIC_FIXTURE`-only and does not require persistent local RunStore writes.

## Purpose

The notebook workflow connects:

1. Lab-exported ExperimentContext JSON.
2. STATIC_FIXTURE SignalSeries loading.
3. Human observations and hypothesis text.
4. StudyRecord creation.
5. Local RunStore logging.

The result is an inspectable local Run under `.openplazma/runs/...`.
The local Observatory can export a read-only HTML view of those Runs.

## Local Workflow

From the repository root, after installing the Python SDK:

```sh
python notebooks/examples/local_tracking_notebook.py
```

The shorter compatibility example still works:

```sh
python notebooks/examples/local_runstore_example.py
```

The local StudyTask example loads the Read the Signal task before starting a Run:

```sh
python notebooks/examples/read_the_signal_task.py
```

The local guided StudyFlow example connects the Read the Signal task to RunStore logging and local Observatory comparison:

```sh
python notebooks/examples/read_the_signal_guided_flow.py
```

Both examples load:

- `notebooks/examples/sample-experiment-context.json`
- the matching `STATIC_FIXTURE` SignalSeries from `data/fixtures/static/sample-001/study-record.json`

## What The Notebook Logs

The local Run logs artifacts:

- `study_task` when running the StudyTask example
- `study_flow` and `scenario` when running the guided StudyFlow example
- `experiment_context`
- `signal_series`
- `study_record`

It also logs signal metrics:

- `signal_point_count`
- `signal_min`
- `signal_max`
- `signal_mean`

## Inspecting Output

RunStore output is written under:

```text
.openplazma/
  runs/
    OPR-YYYYMMDD-000001/
      run.json
      config.json
      metrics.jsonl
      events.jsonl
      manifest.json
      artifacts/
        experiment-context.json
        signal-series.json
        study-record.json
```

This directory is ignored by git and should not be committed.

To inspect the local Runs as static HTML:

```sh
python scripts/export-observatory.py --run-store .openplazma
```

Then open `.openplazma/observatory/index.html`.

To compare two local Runs, pass their Run IDs:

```sh
python scripts/export-observatory.py --run-store .openplazma --compare OPR-YYYYMMDD-000001 OPR-YYYYMMDD-000002
```

## Python Helpers

The SDK includes small notebook-oriented helpers:

```python
record = op.create_study_record(
    context=ctx,
    observations=[{"text": "Observed the selected STATIC_FIXTURE signal."}],
    hypothesis="Notebook-side placeholder for decision support, not a standalone validated conclusion.",
)

summary = op.summarize_signal(signal)

with op.start_run(...) as run:
    op.log_context_signal_and_study_record(run, ctx, signal, record)
    run.log_metric("signal_point_count", summary["point_count"])
    run.log_metric("signal_min", summary["min"])
    run.log_metric("signal_max", summary["max"])
    run.log_metric("signal_mean", summary["mean"])
```

The helpers do not fetch external data, change capabilities, or connect to external targets.

See [StudyTask layer](studytask_layer.md) for the Scenario and StudyTask contract.

## Limitations

- Local-only.
- `STATIC_FIXTURE` data only.
- No cloud sync.
- No public data ingestion.
- Read-only local Observatory export only.
- No AI assist.
- Read-only decision support only.
- No command/control actions.
- No hazardous operating procedures.
- Not a standalone authority for safety-critical operation or reactor design decisions.
