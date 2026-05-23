# OpenPlazma

OpenPlazma is an OSS fusion-data learning lab. The project starts with data contracts, fixture validation, and a game-like UI shell for exploring signal records.

OpenPlazma is not a validated fusion simulator. It is not a real hardware control system. The repository must not include instructions for high voltage, vacuum systems, lasers, radiation sources, or hazardous experiments.

## Workspace

- `apps/lab`: React, TypeScript, Vite Real Signal Room app.
- `packages/core`: Domain TypeScript contracts.
- `packages/schema`: Zod schemas for runtime validation.
- `packages/data-client`: Fixture-backed data source.
- `packages/signal-viewer`: Simple React signal chart component.
- `data/fixtures/static`: Static sample signal records with `provider: "STATIC_FIXTURE"`.
- `docs/adr`: Architecture decision records.
- `docs/safety`: Safety boundaries.

## Commands

```sh
pnpm install
pnpm typecheck
pnpm test
pnpm --filter @openplazma/lab dev
```

## Notebook Bridge MVP

The notebook bridge reads Lab-exported ExperimentContext JSON, loads a matching `STATIC_FIXTURE` signal, plots it, and saves a notebook-side StudyRecord JSON. It does not start Jupyter, fetch external data, run JupyterLite, or perform AI-assisted analysis.

Install and test the Python SDK locally:

```sh
cd python/openplazma
python -m pip install -e ".[dev]"
python -m pytest
```

Run the Jupytext percent-format template as a plain Python script from the repository root after installing the SDK:

```sh
python notebooks/templates/experiment_notebook.py
```

The template uses `notebooks/examples/sample-experiment-context.json`, which mirrors the Lab-exported context shape for selecting `sample-001` and one static signal. This M2 bridge uses `provider: "STATIC_FIXTURE"` only.

## Development Checks

Run these before opening or updating a pull request:

```sh
corepack pnpm typecheck
corepack pnpm test
(cd python/openplazma && python -m pytest)
python scripts/check-public-repo-hygiene.py
```

## JupyterLite Workbench MVP

The JupyterLite Workbench is a browser-only notebook surface for `STATIC_FIXTURE` OpenPlazma examples. It lets the Lab pass a selected ExperimentContext into `apps/workbench-lite/files/openplazma/experiment_notebook.ipynb` through browser `localStorage` and an `opContext` URL query parameter.

Build and serve it locally:

```sh
python scripts/prepare-workbench-lite.py
cd apps/workbench-lite
python -m pip install -r requirements.txt
jupyter lite build --lite-dir . --output-dir _output
jupyter lite serve --lite-dir . --output-dir _output
```

Point the Lab at the local Workbench:

```sh
VITE_OPENPLAZMA_WORKBENCH_LITE_URL=http://127.0.0.1:8000/lab/index.html?path=openplazma/experiment_notebook.ipynb
```

Limitations: this MVP uses `STATIC_FIXTURE` data only, fetches no external data, has no AI assist, has no real hardware instructions, and does not deploy to GitHub Pages yet.

## Current Scope

The initial project scope is contract-first. Fixture data is static and local. External data fetching, toy physics, real-device integration, and operational procedures for hazardous equipment are out of scope.

Placeholder records must not claim FAIR MAST provenance. Static examples use `provider: "STATIC_FIXTURE"` and may use `inspiredBy: "FAIR_MAST"` only as non-provenance context.
