# ADR 0002: Real Signal First

## Status

Accepted

## Context

Analysis and decision-support tools become misleading when they start from invented physics or unlabeled data. OpenPlazma needs signal records that make provenance, units, sampling, assumptions, and validation boundaries explicit.

## Decision

OpenPlazma will prefer real-signal-shaped records and validated metadata before any simulation or control features. Initial fixtures are static, local, and intentionally small. They exist to prove the contract, not to claim physical accuracy.

Predictive physics models are out of scope until the project has mature contracts, provenance expectations, validation language, and documentation explaining the difference between measured, derived, synthetic, and illustrative data.

## Consequences

Early work focuses on schemas, fixtures, validation tests, and read-only workflows. UI features should display source, assumptions, and limitations so users can decide how much weight a record deserves in analysis or engineering judgment.
