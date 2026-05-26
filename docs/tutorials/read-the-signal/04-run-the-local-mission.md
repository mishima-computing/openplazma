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
