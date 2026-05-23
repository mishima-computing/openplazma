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

## Current Scope

The initial project scope is contract-first. Fixture data is static and local. External data fetching, toy physics, real-device integration, and operational procedures for hazardous equipment are out of scope.

Placeholder records must not claim FAIR MAST provenance. Static examples use `provider: "STATIC_FIXTURE"` and may use `inspiredBy: "FAIR_MAST"` only as non-provenance context.
