# OpenPlazma

[![TypeScript CI](https://github.com/mishima-computing/openplazma/actions/workflows/ci-typescript.yml/badge.svg)](https://github.com/mishima-computing/openplazma/actions/workflows/ci-typescript.yml)
[![Python CI](https://github.com/mishima-computing/openplazma/actions/workflows/ci-python.yml/badge.svg)](https://github.com/mishima-computing/openplazma/actions/workflows/ci-python.yml)
[![Repository Hygiene](https://github.com/mishima-computing/openplazma/actions/workflows/ci-hygiene.yml/badge.svg)](https://github.com/mishima-computing/openplazma/actions/workflows/ci-hygiene.yml)
[![JupyterLite CI](https://github.com/mishima-computing/openplazma/actions/workflows/ci-jupyterlite.yml/badge.svg)](https://github.com/mishima-computing/openplazma/actions/workflows/ci-jupyterlite.yml)
[![Pages Build CI](https://github.com/mishima-computing/openplazma/actions/workflows/ci-pages-build.yml/badge.svg)](https://github.com/mishima-computing/openplazma/actions/workflows/ci-pages-build.yml)
[![Deploy GitHub Pages](https://github.com/mishima-computing/openplazma/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/mishima-computing/openplazma/actions/workflows/deploy-pages.yml)

OpenPlazma is a local-first experiment and learning system for safe plasma and fusion-data workflows. The project starts with data contracts, fixture validation, and a game-like UI shell for exploring signal records.

OpenPlazma is not a validated fusion simulator, not a reactor design tool, and not a real hardware control system. The repository must not include instructions for high voltage, vacuum systems, lasers, radiation sources, hazardous materials, physical plasma hardware, or hazardous experiments.

Live demo: https://mishima-computing.github.io/openplazma/

The public demo uses `STATIC_FIXTURE` data only. It does not fetch external fusion data, does not include AI assist, does not include real hardware instructions, and is not a validated fusion simulator.

Public readiness docs:

- [Public smoke checklist](docs/public-smoke-checklist.md)
- [Feedback intake](docs/feedback-intake.md)
- [Known issues](docs/known-issues.md)
- [0.1-alpha.0 release note draft](docs/releases/0.1-alpha.0.md)
- [Tracking architecture](docs/tracking-architecture.md) and [ADR-0005](docs/adr/0005-openplazma-tracking-layer-and-downstream-target-boundaries.md)
- [Local RunStore MVP](docs/runstore-mvp.md)
- [Notebook tracking integration](docs/notebook-tracking-integration.md)
- [Observatory UI MVP](docs/observatory-mvp.md)
- [Observatory Compare MVP](docs/observatory-compare-mvp.md)

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

Run the local RunStore example from the repository root:

```sh
python notebooks/examples/local_runstore_example.py
```

This writes inspectable local files under `.openplazma/`, which is ignored by git.
For the full local notebook tracking flow, see [Notebook tracking integration](docs/notebook-tracking-integration.md).

Export a read-only local Observatory report:

```sh
python scripts/export-observatory.py --run-store .openplazma
```

This writes local static HTML under `.openplazma/observatory/`. The public Pages demo does not read a user's local `.openplazma/` files.

To compare two local Runs, see [Observatory Compare MVP](docs/observatory-compare-mvp.md).

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

Limitations: this MVP uses `STATIC_FIXTURE` data only, fetches no external data, has no AI assist, and has no real hardware instructions.

## GitHub Pages Static Demo

Public demo:

```text
https://mishima-computing.github.io/openplazma/
```

The static demo contains the OpenPlazma Lab, the JupyterLite Workbench, and a `STATIC_FIXTURE` signal notebook. It is built as static files under `dist/pages/`; that generated output must not be committed.

Build locally:

```sh
python scripts/build-pages-site.py
```

Serve locally:

```sh
python -m http.server -d dist/pages -b 127.0.0.1 8000
```

Limitations: the demo uses `STATIC_FIXTURE` data only, fetches no external fusion data, has no AI assist, has no real hardware instructions, and is not a validated fusion simulator.

## Current Scope

The initial project scope is contract-first. Fixture data is static and local. External data fetching, toy physics, real-device integration, and operational procedures for hazardous equipment are out of scope.

Placeholder records must not claim FAIR MAST provenance. Static examples use `provider: "STATIC_FIXTURE"` and may use `inspiredBy: "FAIR_MAST"` only as non-provenance context.
