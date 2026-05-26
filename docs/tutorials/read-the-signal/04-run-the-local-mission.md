# 04 Run The Local Mission

This step is for local technical users.

## Setup

Clone the repository:

```sh
git clone https://github.com/mishima-computing/openplazma.git
cd openplazma
```

Install and check the TypeScript workspace:

```sh
corepack pnpm install --frozen-lockfile
corepack pnpm typecheck
corepack pnpm test
```

Install and check the Python SDK:

```sh
cd python/openplazma
python -m pip install -e ".[dev]"
python -m pytest
cd ../..
```

Run the repository hygiene check:

```sh
python scripts/check-public-repo-hygiene.py
```

If plain `pnpm` is unavailable, use `corepack pnpm`. On Windows, if `python` is not available, use the Python launcher available in your environment.

Do not add credentials or secrets to the repository.

## Run The Mission

```sh
rm -rf .openplazma
python scripts/run-guided-study-flow.py --run-store .openplazma --clean
```

The script creates two local Runs.

It logs:

- `study_flow`
- `study_task`
- `scenario`
- `experiment_context`
- `signal_series`
- `study_record`

It logs Metrics:

- `signal_point_count`
- `signal_min`
- `signal_max`
- `signal_mean`

It exports:

- `.openplazma/observatory/index.html`
- `.openplazma/observatory/compare/...`

Generated output is local and should not be committed.

## Inspect The RunStore

RunStore output is written under `.openplazma/runs/...`.
It is local generated output and is ignored by git.

Useful inspection commands:

```sh
find .openplazma -maxdepth 5 -type f
cat .openplazma/runs/*/run.json
cat .openplazma/runs/*/metrics.jsonl
cat .openplazma/runs/*/manifest.json
```

Files to look for:

- `run.json`: Run metadata, source, target, status, limitations, and Capability values.
- `config.json`: local Run configuration.
- `metrics.jsonl`: logged Metrics such as `signal_point_count`, `signal_min`, `signal_max`, and `signal_mean`.
- `events.jsonl`: local Run events.
- `manifest.json`: Artifact records and hashes.
- `artifacts/`: saved StudyFlow, StudyTask, Scenario, ExperimentContext, SignalSeries, and StudyRecord files.

Capability boundary:

- `controlFacility` is false.
- `readFacilityTelemetry` is false.
- `submitComputeJob` is false.
- `runSimulation` is false.
