# Local Signal Import

OpenPlazma can import a local CSV signal as read-only decision-support evidence.

This is the first feature enabled by the read-only decision-support boundary beyond the bundled public fixture path. It lets a local notebook use a user-provided signal file without adding command/control behavior, external network fetching, facility telemetry, AI assist, or hazardous operating procedures.

## Provider

Local imports use:

```json
{
  "provider": "LOCAL_SIGNAL_FILE",
  "validationStatus": "schema_validated"
}
```

OpenPlazma validates the file shape, numeric samples, monotonic time values, safe capabilities, and local RunStore records. It does not validate physical provenance, calibration, device state, facility operation, or engineering correctness of the original measurement.

## CSV Format

The default CSV format is:

```csv
time,value
0.0,1.0
0.5,2.5
1.0,4.0
```

`time` is seconds. Both columns must be finite numeric values, and time must be strictly increasing.

## Python Example

```python
import openplazma as op

imported = op.import_local_signal_csv(
    "loop_voltage.csv",
    signal_id="loop-voltage",
    label="Loop voltage",
    quantity="voltage",
    unit="V",
    shot_id="local-shot-001",
    observations=["Imported a local read-only signal."],
)

context = imported["context"]
signal = imported["signal"]

record = op.create_study_record(
    context=context,
    observations=["Peak value appears near the end of the imported interval."],
)

with op.start_run(
    project="openplazma-local",
    campaign="local-signal-import",
    run_type="notebook_analysis",
    context=context,
) as run:
    op.log_context_signal_and_study_record(run, context, signal, record)
    summary = op.summarize_signal(signal)
    run.log_metric("signal_point_count", summary["point_count"])
    run.log_metric("signal_min", summary["min"])
    run.log_metric("signal_max", summary["max"])
    run.log_metric("signal_mean", summary["mean"])
```

The generated ExperimentContext and RunRecord preserve:

- `provider: "LOCAL_SIGNAL_FILE"`
- a local source label
- a local source URI such as `local-file:loop_voltage.csv`
- the CSV file SHA-256 digest
- `validationStatus: "schema_validated"`
- safe capabilities where facility telemetry and control remain false
- limitations that state this is read-only decision support

## Boundary

This feature is in scope:

- read a local CSV signal
- validate schema and numeric shape
- preserve provenance metadata and SHA-256
- log the context, signal, StudyRecord, metrics, and artifacts to a local RunStore
- inspect and compare the resulting local Runs

This feature is out of scope:

- live device or facility connections
- control commands
- external network data fetching
- safety-critical monitoring or interlocks
- calibration validation
- autonomous operation or reactor-design decisions
- hazardous setup, troubleshooting, or operating procedures
