# ADR 0001: Project Definition

## Status

Accepted

## Context

OpenPlazma is starting as an open-source workbench for read-only plasma signal analysis and decision support. The first public surface uses static signal records and a guided interface, but the project direction is evidence handling for real engineering and scientific judgment, not a toy simulation.

The project must be clear about the boundary. OpenPlazma does not control equipment, generate hazardous operating procedures, or act as the sole authority for safety-critical operation or reactor design decisions. It should help qualified users inspect signals, compare runs, document assumptions, and understand validation limits.

## Decision

OpenPlazma will begin as a contract-first monorepo:

- `apps/lab` provides a React and Vite UI shell.
- `packages/core` defines domain contracts.
- `packages/schema` validates those contracts at runtime.
- `packages/data-client` loads local fixture data.
- `packages/signal-viewer` renders simple signal charts.
- `data/fixtures` stores static sample records.

The first implementation will not fetch external data, control equipment, or implement predictive physics. It establishes the contracts needed for read-only analysis, provenance, and decision-support workflows.

## Consequences

The project can build stable data interfaces before adding richer UI, notebook, or real-data workflows. Future integrations, including a Jupyter notebook bridge and read-only data connectors, must consume the same contracts rather than inventing parallel formats.
