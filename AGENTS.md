# AGENTS.md

## Project Rules

- Treat OpenPlazma as a fusion-data learning lab, not a validated simulator.
- Do not describe, automate, or imply control of real hardware.
- Do not include instructions for high voltage, vacuum systems, lasers, radiation, hazardous materials, or live experiments.
- Do not fetch external data until an explicit data-source ADR and safety review exist.
- Do not add toy physics models before the data contracts and provenance model are stable.
- Prefer real signal-shaped records and explicit metadata over invented simulator output.
- Keep data contracts versioned and validated with Zod schemas.
- Keep UI language educational and clearly non-operational.

## Engineering Conventions

- Use pnpm workspaces.
- Keep package boundaries small and explicit.
- Put domain-only TypeScript types in `packages/core`.
- Put runtime validation in `packages/schema`.
- Keep fixture access in `packages/data-client`.
- Keep visual components in `packages/signal-viewer`.
- Tests should validate representative fixtures against schemas.
