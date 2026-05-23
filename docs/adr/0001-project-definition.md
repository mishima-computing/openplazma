# ADR 0001: Project Definition

## Status

Accepted

## Context

OpenPlazma is starting as an open-source learning environment for exploring fusion-data concepts through safe, static signal records and a game-like user interface.

The project must be clear about what it is not. OpenPlazma is not a validated fusion simulator, not a real hardware control system, and not a guide for building or operating hazardous equipment.

## Decision

OpenPlazma will begin as a contract-first monorepo:

- `apps/lab` provides a React and Vite UI shell.
- `packages/core` defines domain contracts.
- `packages/schema` validates those contracts at runtime.
- `packages/data-client` loads local fixture data.
- `packages/signal-viewer` renders simple signal charts.
- `data/fixtures` stores static sample records.

The first implementation will not fetch external data and will not implement physics.

## Consequences

The project can build stable data interfaces before adding richer UI or notebook workflows. Future integrations, including a Jupyter notebook bridge, must consume the same contracts rather than inventing parallel formats.
