# Investigation Model

This document describes the first implemented core investigation contracts in
`packages/core/src/investigation.ts` and `packages/schema/src/investigation.schema.ts`.

OpenPlazma is core infrastructure for people who want to observe plasma,
fusion, or plasma-like energy phenomena. The model must work for laboratory
plasmas, fusion devices, atmospheric lights, anomalous artifacts, spacecraft
signatures, stellar observations, and organism interiors. It must not assume
that a target is a reactor, that a glow is plasma, or that plasma implies
fusion.

## Two Uncertainties

OpenPlazma investigations have two separate questions:

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

The first unknown-energy investigation family can start with a
will-o'-the-wisp-like atmospheric light. It should teach restraint:

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

## Targets And Regions

`InvestigationTarget` is intentionally broader than a reactor. Initial target
kinds include:

- `lab_plasma`
- `fusion_device`
- `atmospheric_light`
- `organism`
- `organism_interior`
- `artifact`
- `spacecraft`
- `stellar_object`
- `unknown`

Targets may define `regions[]`. Regions let a package say where a diagnostic
applies without claiming that the region's nature is already understood.

Examples:

```text
stellar_object
  core
  photosphere
  corona

organism_interior
  abdomen
  luminous-organ

fusion_device
  core-plasma
  edge
  divertor
```

Region references are checked by schema so a diagnostic cannot silently point
to a non-existent target region.

## Diagnostic Artifact Families

The first diagnostic artifact families cover direct signals, derived maps, and
remote observation products:

- signal series
- spectra and gamma spectra
- image frames and thermal maps
- field maps and magnetograms
- particle, neutron, neutrino, and gravity traces
- pressure, acoustic, and helioseismic traces
- tomographic volumes
- composition profiles
- event logs and motion tracks

This list is not a claim that all diagnostics are equally available for every
target. It is a vocabulary for recording what evidence a package actually has.

## Instruments And Mixed Signals

A diagnostic artifact is not raw truth. It is produced through an instrument or
observer:

```text
target region
  -> observable quantity
  -> instrument response and calibration
  -> artifact
  -> contribution decomposition
  -> claim
```

The model therefore records optional `instrument`, `contributions`, and
`frequencyAnalyses` fields on `DiagnosticArtifact`.

Examples of observables include visible light, heat, electric current, magnetic
field, gravity, particle flux, pressure, acoustic waves, composition, density,
and temperature. Examples of contributions include plasma emission, thermal
emission, photoelectric coupling, gravity coupling, background, aliasing, motion
artifacts, reconstruction artifacts, and instrument noise.

This matters because an apparent current or brightness trace may be mixed:

```text
measured current = thermal coupling
                 + photoelectric coupling
                 + electric or magnetic coupling
                 + gravity-like coupling
                 + instrument noise
```

The contract should keep those contributors separate until evidence resolves
them. A current trace is not automatically electrical source power. A thermal
map is not automatically a reactor. A luminous image is not automatically
plasma.

Human vision is also an instrument. A `human_eye` artifact can be valuable
testimony, but its calibration is usually `uncalibrated`; it cannot separate
plasma light, thermal glow, chemical luminescence, background light, and
fusion-product signatures by itself.

## Frequency Analysis

Light is not a boolean. It has electromagnetic carrier frequency, and its
intensity can also vary over time. These are different domains:

```text
electromagnetic_carrier: optical, ultraviolet, x-ray, gamma carrier frequency
intensity_modulation:    brightness or radiance changing over time
electric_variation:      current or electric-field modulation over time
gravity_variation:       gravimeter or inferred gravity-like modulation
acoustic_modulation:     pressure or acoustic oscillation
spatial_frequency:       image, tomography, or field-map structure
```

`FrequencyAnalysis` records the decomposition method, such as FFT, STFT,
wavelet analysis, periodograms, harmonic fits, Lomb-Scargle analysis, spectral
line fits, or tomographic inversion. It can store frequency bands and detected
peaks, but every peak remains evidence, not identity:

```text
flicker peak -> modulation exists
flicker peak -/-> plasma
flicker peak -/-> fusion
visible carrier lines -> spectral structure exists
visible carrier lines -/-> fusion products
```

Fusion-relevant claims still need the right product diagnostics, condition
checks, and calibration story.

## Organism Interiors

Large-organism or "kaiju" investigations are not a joke path in the core model.
They stress-test the same rule that applies to fusion devices and stars:

```text
heat + light + motion does not identify an energy source
```

An organism interior package can carry thermal maps, acoustic traces,
composition profiles, field maps, motion correlations, and other artifacts. The
core must keep several explanations alive:

- ordinary metabolism
- chemical luminescence
- external-field response
- internal plasma
- fusion
- sensor or reconstruction artifact

The model should support the uncomfortable middle state:

```text
plasma remains plausible
fusion remains untested
necessary fusion diagnostics are missing
```

## Contract Roles

`InvestigationPackage` groups the neutral investigation material:

- `InvestigationTarget`: what is being investigated
- `DiagnosticArtifact`: supplied evidence such as signal series, spectra,
  image frames, thermal maps, field maps, particle flux, gravity traces, event
  logs, motion tracks, instrument metadata, mixed-signal contributions, and
  frequency analyses
- `InvestigationQuestion`: what the user must decide
- `FusionConditionAssessment`: whether fusion is unsupported, contradicted,
  plausible, supported, or still unknown, plus condition reasoning
- `InvestigationClaim`: claim statements and their evidence artifact links

These contracts are core infrastructure. They do not implement gameplay,
narrative progression, Steam features, facility telemetry, or control.

## Static Investigation Fixtures

The first schema-validated investigation fixtures live under:

```text
data/fixtures/static/investigations/
  manifest.json
  will-o-wisp-001/investigation-package.json
  organism-interior-001/investigation-package.json
  solar-inverse-001/investigation-package.json
```

The fixture manifest is intentionally separate from the shot manifest. Shot
fixtures carry signal records for the Real Signal Room; investigation fixtures
carry evidence packages for unknown-energy reasoning. Both use repo-root
relative paths and `STATIC_FIXTURE` provenance.

`StaticFixtureDataSource` exposes these packages through:

```text
listInvestigationPackages()
getInvestigationPackage(packageId)
```

This keeps investigation package loading read-only and fixture-backed until a
future ADR approves external data sources.

The Python SDK exposes the same static package path for notebooks and local
scripts:

```python
import openplazma as op

package = op.load_static_investigation_package(repo_root, "will-o-wisp-001")
summary = op.summarize_investigation_package(package)
report = op.create_investigation_report(package)
op.save_investigation_report(report, ".openplazma/investigation-reports/report.json", package=package)
```

For the first guided investigation path, see
[Investigate Will-o'-the-wisp](tutorials/investigate-will-o-wisp.md).

CI validates all static investigation packages and draft report shape with:

```sh
python scripts/validate-investigation-fixtures.py
```

`@openplazma/analysis` also provides read-only helpers for deriving
`FrequencyAnalysis` objects from signal-shaped records:

```text
analyzeTemporalFrequency(signal, { domain })
buildElectromagneticCarrierAnalysis(...)
```

These helpers identify bands and candidate peaks. They do not identify plasma,
fusion, or source identity without additional evidence.

The same package exposes mixed-signal assessment helpers:

```text
assessDiagnosticArtifact(artifact, requiredObservables)
assessInvestigationMeasurements(package, requiredObservables)
```

These helpers summarize measured observables, missing observables, calibration
state, unresolved contributions, and noise/contaminant contributions. The
result is deliberately conservative: a mixed or uncalibrated artifact cannot
identify an energy source by itself.
