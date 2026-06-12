# Investigation Model

This document describes the first implemented investigation contracts in
`packages/core/src/investigation.ts` and `packages/schema/src/investigation.schema.ts`.

The model is for unknown energy phenomena. It must not assume that a target is a
reactor, that a glow is plasma, or that plasma implies fusion.

## Two Uncertainties

OpenPlazma Field Lab style investigations have two separate questions:

1. What is the observed energy phenomenon?
2. If fusion is possible or assumed for a stage, what conditions would make that
   fusion or plasma maintenance possible?

The first question is classification and falsification. The second question is
condition assessment and inverse reasoning.

## Logical Guardrails

Definitions:

```text
E  = an energy or luminous phenomenon is observed
P  = the phenomenon is plasma
F  = fusion is occurring
SF = sustained fusion is occurring
C  = the required fusion-condition set is satisfied
M  = the required plasma-maintenance condition set is satisfied
O(x) = x is observed
A(x) = the mission has adequate diagnostics for observing x
```

Allowed implications:

```text
SF -> F
SF -> C
SF -> M
thermonuclear_F -> P
A(product_r) and not O(product_r) -> weaken or contradict F_r
not C_i -> not SF
```

The useful contrapositive is:

```text
SF -> C
therefore not C -> not SF
```

Disallowed shortcuts:

```text
E -> P
P -> F
C -> F
F -> SF
not O(x) -> not x
```

Required fusion conditions are necessary conditions, not sufficient conditions.
That is why `FusionConditionEstimate.logicalRole` exists and why
`requiredConditions[]` entries must use `logicalRole: "necessary"`.

## Will-o'-the-wisp First

The first investigation family starts with a will-o'-the-wisp-like atmospheric
light. It should teach restraint:

- glowing does not imply plasma
- plasma does not imply fusion
- testimony is evidence, but not a physical diagnostic
- a correct report may be that the fusion claim is unsupported

The mission can still include `fusion` as a candidate energy source. Including it
means the claim is testable, not that the premise is accepted.

## Inverse Fusion Stages

Some later stages can start from a fusion-holds premise:

```text
Assume F or SF for the stage.
Work backward to required C and M.
Compare those requirements with available observations.
```

This is useful for solar or original-reactor style stages. It does not prove the
premise by itself. It records which conditions would have to be true, which are
observed, which are inferred, and which remain unknown.

Gravity is a first-class condition parameter because stellar fusion is
gravitationally confined. In artificial or anomalous targets, a gravity-like,
magnetic, inertial, or unknown confinement mechanism may be a competing claim.

## Contract Roles

`InvestigationPackage` groups the neutral investigation material:

- `InvestigationTarget`: what is being investigated
- `DiagnosticArtifact`: supplied evidence such as signal series, spectra,
  image frames, field maps, particle flux, gravity traces, event logs, or motion
  tracks
- `InvestigationQuestion`: what the user must decide
- `FusionConditionAssessment`: whether fusion is unsupported, contradicted,
  plausible, supported, or still unknown, plus condition reasoning
- `InvestigationClaim`: claim statements and their evidence artifact links

These contracts are core infrastructure. They do not implement gameplay,
narrative progression, Steam features, facility telemetry, or control.
