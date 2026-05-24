# Observatory UI MVP

M7 adds the first read-only local Observatory for inspecting OpenPlazma RunStore output.

The Observatory MVP is a local Python workflow that exports static HTML. It is not a hosted service, does not require an account, does not sync to a cloud service, and does not inspect a user's local filesystem from the public Pages demo.

## Purpose

The Observatory helps a local user inspect Runs created by the Python and local Jupyter notebook workflow.

It reads:

- RunRecord files
- MetricRecord JSONL
- ArtifactRecord manifest entries
- event JSONL
- source metadata
- target metadata
- capability metadata

It does not edit, delete, or submit Runs.

## Local Workflow

From the repository root:

```sh
rm -rf .openplazma
python notebooks/examples/local_runstore_example.py
python notebooks/examples/local_tracking_notebook.py
python scripts/export-observatory.py --run-store .openplazma
```

Then open:

```text
.openplazma/observatory/index.html
```

## Generated Output

The exporter writes:

```text
.openplazma/
  observatory/
    index.html
    runs/
      OPR-YYYYMMDD-000001.html
    assets/
      observatory.css
```

This output is local generated output and must not be committed.

## What It Shows

The index page summarizes:

- project
- campaign
- runId
- runType
- status
- createdAt
- finishedAt
- source provider
- target type
- artifact count
- metric count

Run detail pages show:

- Run metadata
- source
- target
- capabilities
- limitations
- metrics
- artifacts
- events

Artifact links are local relative links to files inside `.openplazma/runs/...`.

## Public Demo Boundary

The GitHub Pages public demo remains browser/static and `STATIC_FIXTURE`-only. It does not read a user's local `.openplazma/` RunStore.

The local Observatory export is a local Python workflow.

## Limitations

- Local only.
- Read-only.
- No cloud sync.
- No hosted service.
- No account requirement.
- No public data ingestion.
- No Observatory edit actions.
- No AI assist.
- No real hardware instructions.
- Not a validated fusion simulator.
- Not a reactor design tool.
- Not a real hardware control system.
