# Guided Study Flow

M10 adds the first guided OpenPlazma StudyFlow.

The first guided flow is `read-the-signal-guided-v0.1`. It connects the existing Read the Signal StudyTask, Scenario, Notebook workflow, local RunStore, Observatory, and Observatory Compare into one local path.

For a first-time user walkthrough, see the mission-style [Read the Signal tutorial](tutorials/read-the-signal/README.md).
For a 45-minute facilitated session, see the [Teacher / Workshop Pack](../teacher-kit/README.md).

## Purpose

A StudyFlow describes the ordered learning path around one or more StudyTasks.

The Read the Signal guided flow helps a local Python or local Jupyter user:

1. Inspect the `STATIC_FIXTURE` signal in the Lab.
2. Use the ExperimentContext in the Notebook workflow.
3. Follow StudyTask prompts.
4. Create a StudyRecord.
5. Log a local Run with artifacts and metrics.
6. Export the local Observatory.
7. Compare two local Runs.

## Relationship Between Concepts

- Scenario: the named learning context, currently `read-the-signal`.
- StudyTask: the concrete task, currently `read-the-signal-static-v0.1`.
- StudyFlow: the ordered path that connects Lab, Notebook, RunStore, Observatory, and Compare.
- RunStore: the local inspectable store where the guided workflow logs Runs.
- Observatory: the local static report that reads RunStore output.
- Observatory Compare: the local static comparison page for two Runs.

The public Pages demo remains browser/static and does not inspect a user's local `.openplazma/` directory.

## Run The Local Guided Flow

From the repository root:

```sh
rm -rf .openplazma
python notebooks/examples/read_the_signal_guided_flow.py
```

This writes one local Run under:

```text
.openplazma/runs/OPR-YYYYMMDD-000001/
```

The guided example logs:

- `study_flow`
- `study_task`
- `scenario`
- `experiment_context`
- `signal_series`
- `study_record`

The guided example logs these metrics:

- `signal_point_count`
- `signal_min`
- `signal_max`
- `signal_mean`

## Run The Full Local Smoke Workflow

To create two local Runs, export the Observatory, and export a compare page:

```sh
python scripts/run-guided-study-flow.py --run-store .openplazma --clean
```

The script prints:

- Run directories
- Observatory index path
- Observatory Compare page path

It does not start a server, open a browser, use an account, sync to a cloud service, or fetch external data.

## Inspect And Compare

Export the Observatory after one or more local Runs:

```sh
python scripts/export-observatory.py --run-store .openplazma
```

Open:

```text
.openplazma/observatory/index.html
```

To compare two Runs, use:

```sh
python scripts/export-observatory.py --run-store .openplazma --compare RUN_A RUN_B
```

## Limitations

- `STATIC_FIXTURE` data only.
- No grading or scoring.
- No public data ingestion.
- No cloud sync.
- No hosted Observatory.
- No AI assist.
- No real hardware instructions.
- Not a validated fusion simulator.
- Not a reactor design tool.
- Not a real hardware control system.
