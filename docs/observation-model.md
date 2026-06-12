# Observation Model Direction

This document defines the observation-model direction. Parts of this direction
are now implemented for MHD analysis and unknown-energy investigations; see
the MHD contracts and [Investigation Model](investigation-model.md).

OpenPlazma should not treat a sensor signal as a direct copy of a theory variable. Fusion development often works with a latent physical state that is not directly observable. The useful engineering question is how that state appears through diagnostics, simulated diagnostics, derived signals, and interpretation layers.

## Core Principle

Theory and sensor data are not one-to-one.

OpenPlazma should preserve the chain from theory to observation and back to evidence:

```text
latent state or theory
-> observable phenomenon
-> diagnostic or sensor channel
-> raw signal
-> derived signal
-> inference
-> claim
```

The same theory can appear in multiple diagnostics. The same signal can support multiple competing interpretations. OpenPlazma should make that many-to-many relationship inspectable instead of hiding it behind a single "this signal equals this physical quantity" field.

## Forward And Inverse Directions

Forward direction:

```text
theory or latent state -> expected sensor signature
```

Inverse direction:

```text
sensor data -> plausible theory or latent state
```

Both directions are model-dependent. A signal can be consistent with a hypothesis under one observation model and inconclusive under another.

## Future Concepts

These concepts should guide future schemas and APIs.

LatentState:
The physical state or theory-side quantity that OpenPlazma users want to reason about. Examples include temperature, density, confinement, instability modes, impurity transport, or simulation state variables. OpenPlazma may never know the true latent state for measured experiments.

Observable:
A physical effect that can be observed from the latent state, such as emitted photons, induced voltage, particle flux, heat, phase shift, image pattern, spectral line shape, or magnetic fluctuation.

DiagnosticChannel:
The measurement or synthetic diagnostic path that turns an observable into data. Examples include magnetic probes, spectroscopy, cameras, interferometry, bolometers, neutron diagnostics, ADC channels, or virtual diagnostics in a simulator.

RawSignal:
The data closest to the diagnostic output, such as voltage, current, counts, pixels, spectra, waveforms, or arrays.

DerivedSignal:
A signal produced from raw data by calibration, processing, fitting, inversion, or transformation. A derived signal must keep links to source artifacts, calibration metadata, assumptions, and validation status.

ObservationModel:
A model that describes how a theory-side state should appear in one or more diagnostic channels. It may be analytical, empirical, synthetic, simulator-backed, or approximate.

Inference:
The process that maps signals back toward a theory-side statement. Examples include fitting, inversion, Bayesian inference, simulation matching, or ML estimation.

Claim:
A human or machine-readable statement about what the evidence supports. Claims must not be stored as if they were raw measurements.

EvidenceLink:
The relationship between a claim, an observation model, the supporting or contradicting signal evidence, and the relevant time range or artifact range.

## Sensor And Simulator Equivalence

At the signal-handling layer, measured diagnostics and simulated diagnostics should share the same basic contracts:

```text
source -> signal -> artifact -> metrics -> comparison -> report
```

The difference belongs in provenance and claim boundaries:

- measured or simulated source kind
- known or unknown latent state
- diagnostic model identity and version
- calibration status
- validation status
- assumptions
- limitations

A simulator can expose a virtual diagnostic. A facility can expose a measured diagnostic. OpenPlazma should be able to compare their signal artifacts, but it must not collapse their provenance or validation status.

## Sweep Direction

Future sweep support should start with simulation, synthetic diagnostics, and analysis parameters, not facility control.

A future SweepRun should record:

- simulator or analysis backend identity
- input parameters
- diagnostic model and version
- solver, mesh, timestep, or seed settings when applicable
- produced signal artifacts
- metrics
- observation models used for interpretation
- assumptions
- limitations
- comparison report

Sweep support must keep these capability boundaries explicit:

```json
{
  "readData": true,
  "writeArtifacts": true,
  "runSimulation": true,
  "submitComputeJob": false,
  "readFacilityTelemetry": false,
  "controlFacility": false
}
```

If a future backend submits remote compute jobs, that requires an explicit `submitComputeJob` milestone. Facility control remains a separate restricted capability and is not part of public core functionality.

## Implementation Policy

Future implementation should follow these rules:

- Do not model a theory variable as identical to a sensor signal.
- Do not store a derived physical quantity without the transformation, calibration, or inference metadata that produced it.
- Do not store a claim without links to evidence, assumptions, limitations, and observation models.
- Preserve raw signals as artifacts whenever possible.
- Preserve derived signals as separate artifacts rather than overwriting raw data.
- Keep measured, simulated, synthetic, and derived provenance distinguishable.
- Allow one hypothesis to link to many signals.
- Allow one signal to link to many hypotheses.
- Treat support, contradiction, and inconclusive evidence as first-class outcomes.
- Keep command/control capabilities separate from signal analysis and simulation runs.

## Example: Spectroscopy

```text
latent state:
  impurity species, ion temperature, plasma rotation

observable:
  emitted spectral lines, line broadening, line shift, intensity

diagnostic channel:
  optics and spectrometer

raw signal:
  detector counts by wavelength and time

derived signal:
  line center, line width, line intensity

inference:
  species identification, temperature estimate, velocity estimate

claim:
  this interval is consistent with species X and ion-temperature range Y-Z
```

That claim is only valid under the observation model, calibration, assumptions, and limitations used to interpret the spectrum.

## Example: Magnetic Fluctuation

```text
latent state:
  instability mode or current-profile change

observable:
  magnetic-field fluctuation

diagnostic channel:
  magnetic pickup coil or synthetic magnetic probe

raw signal:
  voltage or current waveform

derived signal:
  fluctuation amplitude, frequency, phase, mode estimate

inference:
  comparison against an instability hypothesis or simulation output

claim:
  this signal supports, contradicts, or is inconclusive for the proposed mode
```

The same waveform may support different hypotheses under different observation models. OpenPlazma should preserve that ambiguity rather than remove it too early.
