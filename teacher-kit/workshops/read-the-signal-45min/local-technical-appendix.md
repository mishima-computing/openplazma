# Local Technical Appendix

## What The Local Technical Path Does

The local technical path runs the existing guided StudyFlow twice, writes local Runs, exports Observatory, and exports a two-Run Compare page.

It writes only under `.openplazma/`.

## Run The Local Mission

From the repository root:

```sh
python scripts/run-guided-study-flow.py --run-store .openplazma --clean
```

## Generated Files

- `.openplazma/runs/...`
- `.openplazma/observatory/index.html`
- `.openplazma/observatory/compare/...`

## Inspect RunStore

Useful files:

- `run.json`: Run metadata, source, target, status, limitations, and Capability values.
- `metrics.jsonl`: logged Metrics.
- `manifest.json`: Artifact records and hashes.
- `artifacts/`: saved StudyFlow, StudyTask, Scenario, ExperimentContext, SignalSeries, and StudyRecord files.

Useful commands:

```sh
find .openplazma -maxdepth 5 -type f
cat .openplazma/runs/*/run.json
cat .openplazma/runs/*/metrics.jsonl
cat .openplazma/runs/*/manifest.json
```

Open:

```text
.openplazma/observatory/index.html
.openplazma/observatory/compare/...
```

## Cleanup

```sh
rm -rf .openplazma
```

## Limitations

- Local-only.
- No cloud sync.
- No external data.
- Read-only analysis and decision support only.
- No command/control path or hazardous operating procedure.
- Not a standalone authority for safety-critical operation or reactor design.
- Generated output is ignored by git and should not be committed.
