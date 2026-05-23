# ADR 0002: Real Signal First

## Status

Accepted

## Context

Learning tools can become misleading when they start from invented physics or unlabeled data. OpenPlazma needs data records that make provenance, units, sampling, and safety boundaries explicit.

## Decision

OpenPlazma will prefer real-signal-shaped records and validated metadata before any simulation features. Initial fixtures are static, local, and intentionally small. They exist to prove the contract, not to claim physical accuracy.

Toy physics models are out of scope until the project has mature contracts, provenance expectations, and documentation explaining the difference between measured, derived, synthetic, and illustrative data.

## Consequences

Early work focuses on schemas, fixtures, and validation tests. UI features should display the source and limitations of records rather than presenting them as operational or predictive.
