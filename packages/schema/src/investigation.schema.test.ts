import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import type { FusionConditionAssessment, InvestigationPackage } from "@openplazma/core";
import {
  fusionConditionAssessmentSchema,
  investigationFixtureManifestSchema,
  investigationPackageSchema,
  investigationReportSchema,
  investigationSessionSchema,
  parseInvestigationFixtureManifest,
  parseInvestigationPackage,
  parseInvestigationReport,
  parseInvestigationSession,
  parseObservationLineageAudit
} from "./index";

function readFixtureJson(path: string): unknown {
  return JSON.parse(readFileSync(join(process.cwd(), path), "utf8")) as unknown;
}

function willOWispPackage(): InvestigationPackage {
  return {
    kind: "openplazma.investigation_package",
    version: "0.1.0",
    packageId: "will-o-wisp-001",
    title: "Will-o'-the-wisp first anomaly",
    target: {
      kind: "openplazma.investigation_target",
      version: "0.1.0",
      targetId: "marsh-light",
      targetKind: "atmospheric_light",
      label: "Marsh light",
      description: "A reported floating light with weak field notes and simple optical measurements.",
      candidateEnergySources: [
        "chemical_luminescence",
        "combustion",
        "electrical_discharge",
        "plasma",
        "sensor_artifact",
        "fusion"
      ],
      limitations: ["Witness reports are not physical diagnostics.", "No direct internal measurement exists."]
    },
    questions: [
      {
        questionId: "q-source",
        questionKind: "energy_source_classification",
        text: "What energy source is consistent with the supplied observations?"
      },
      {
        questionId: "q-plasma",
        questionKind: "is_plasma",
        text: "Is there evidence for an ionized plasma?"
      },
      {
        questionId: "q-fusion",
        questionKind: "is_fusion",
        text: "Is the fusion claim supported or contradicted?"
      }
    ],
    artifacts: [
      {
        kind: "openplazma.diagnostic_artifact",
        version: "0.1.0",
        artifactId: "witness-eye-report",
        artifactKind: "event_log",
        label: "Human visual report",
        provenanceKind: "testimony",
        instrument: {
          instrumentKind: "human_eye",
          label: "Unaided human eye",
          observables: ["visible_light"],
          calibration: {
            status: "uncalibrated",
            responseKnown: false,
            correctionApplied: false,
            description: "The observer's visual response is not instrument-calibrated.",
            limitations: ["Human vision cannot separate plasma emission, thermal glow, and fusion-product signatures unaided."]
          }
        },
        contributions: [
          {
            contributionKind: "plasma_emission",
            role: "candidate",
            status: "unresolved",
            description: "The visible glow may include plasma emission.",
            limitations: ["A visual report alone cannot identify the emitting mechanism."]
          },
          {
            contributionKind: "chemical_emission",
            role: "candidate",
            status: "unresolved",
            description: "The visible glow may be chemical luminescence.",
            limitations: ["No calibrated spectrum is available in the testimony."]
          }
        ],
        description: "Witness report of a floating visible light.",
        limitations: ["This is a subjective visual observation, not a calibrated optical diagnostic."]
      },
      {
        kind: "openplazma.diagnostic_artifact",
        version: "0.1.0",
        artifactId: "emission-timeseries",
        artifactKind: "signal_series",
        label: "Emission intensity",
        provenanceKind: "measured",
        instrument: {
          instrumentKind: "visible_camera",
          label: "Low-rate visible camera",
          observables: ["visible_light"],
          calibration: {
            status: "estimated",
            responseKnown: false,
            correctionApplied: false,
            description: "Camera response is estimated from field notes rather than a lab calibration.",
            limitations: ["Brightness changes are comparable only within this trace."]
          }
        },
        contributions: [
          {
            contributionKind: "plasma_emission",
            role: "candidate",
            status: "unresolved",
            description: "Ionized emission is a candidate contributor to the brightness trace.",
            limitations: ["The trace has no line-resolved spectral evidence."]
          },
          {
            contributionKind: "thermal_emission",
            role: "candidate",
            status: "unresolved",
            description: "Thermal glow can modulate the visible brightness.",
            limitations: ["The camera is not a bolometer."]
          },
          {
            contributionKind: "instrument_noise",
            role: "noise",
            status: "unresolved",
            description: "Sensor noise and compression may create or smear small peaks.",
            limitations: ["No dark-frame correction is supplied."]
          }
        ],
        frequencyAnalyses: [
          {
            analysisId: "brightness-fft",
            domain: "intensity_modulation",
            method: "fft",
            sourceQuantity: "brightness",
            sampleRateHz: 20,
            windowSeconds: 12,
            frequencyResolutionHz: 0.08333333333333333,
            bands: [
              {
                bandId: "visible-flicker",
                domain: "intensity_modulation",
                label: "Visible brightness flicker",
                lowerFrequencyHz: 0.1,
                upperFrequencyHz: 2,
                quantity: "brightness modulation",
                unit: "a.u.",
                description: "Temporal brightness variation of the visible light.",
                limitations: ["A flicker frequency is not an energy-source identity."]
              }
            ],
            peaks: [
              {
                peakId: "dominant-flicker",
                frequencyHz: 0.67,
                amplitude: 0.12,
                signalToNoiseRatio: 3.1,
                interpretation: "Dominant unresolved brightness modulation.",
                limitations: ["The peak may be source modulation, motion, aliasing, or instrument response."]
              }
            ],
            description: "Fourier decomposition of the visible brightness trace.",
            assumptions: ["The field sample rate is approximately stable."],
            limitations: ["FFT peaks constrain modulation; they do not prove plasma or fusion."]
          }
        ],
        signalIds: ["emission-intensity"],
        quantity: "brightness",
        unit: "a.u.",
        description: "A low-rate optical brightness trace.",
        limitations: ["Brightness alone cannot identify fusion."]
      },
      {
        kind: "openplazma.diagnostic_artifact",
        version: "0.1.0",
        artifactId: "visible-spectrum",
        artifactKind: "spectrum",
        label: "Visible spectrum",
        provenanceKind: "measured",
        instrument: {
          instrumentKind: "spectrometer",
          label: "Coarse visible spectrometer",
          observables: ["visible_light"],
          calibration: {
            status: "estimated",
            responseKnown: true,
            correctionApplied: true,
            description: "A coarse wavelength response correction has been applied.",
            limitations: ["The correction is insufficient for fusion-product discrimination."]
          }
        },
        contributions: [
          {
            contributionKind: "plasma_emission",
            role: "candidate",
            status: "unresolved",
            description: "Line-like visible features could be plasma emission.",
            limitations: ["Visible lines alone do not imply fusion."]
          },
          {
            contributionKind: "background",
            role: "contaminant",
            status: "modeled",
            description: "Ambient sky and reflected light contribute to the spectrum.",
            limitations: ["The background model is field-derived."]
          }
        ],
        frequencyAnalyses: [
          {
            analysisId: "visible-carrier-spectrum",
            domain: "electromagnetic_carrier",
            method: "spectral_line_fit",
            sourceQuantity: "spectral_radiance",
            bands: [
              {
                bandId: "visible-optical-band",
                domain: "electromagnetic_carrier",
                label: "Visible optical carrier band",
                lowerFrequencyHz: 4.0e14,
                upperFrequencyHz: 7.9e14,
                quantity: "optical carrier frequency",
                unit: "Hz",
                description: "Carrier-frequency range for the visible spectrum.",
                limitations: ["Visible carrier frequencies do not by themselves identify the source."]
              }
            ],
            peaks: [
              {
                peakId: "green-line-candidate",
                frequencyHz: 5.45e14,
                amplitude: 0.4,
                interpretation: "Candidate visible emission feature.",
                limitations: ["The feature is not reaction-product evidence."]
              }
            ],
            description: "Frequency-domain representation of the visible electromagnetic carrier.",
            assumptions: ["Wavelength-to-frequency conversion uses vacuum light speed approximation."],
            limitations: ["The carrier spectrum must be combined with particle or high-energy diagnostics for fusion claims."]
          }
        ],
        quantity: "spectral_radiance",
        unit: "a.u.",
        description: "Coarse visible spectrum captured near the reported light.",
        limitations: ["No neutron, gamma, or particle diagnostics are supplied."]
      }
    ],
    observations: [
      {
        kind: "openplazma.observation_statement",
        version: "0.1.0",
        readoutId: "brightness-flicker-readout",
        artifactId: "emission-timeseries",
        signalId: "emission-intensity",
        observable: "visible_light",
        readoutKind: "frequency_peak",
        method: "fft",
        selector: "frequencyAnalyses[brightness-fft].peaks[dominant-flicker]",
        status: "candidate",
        value: 0.67,
        unit: "Hz",
        assumptions: ["The field sample rate is approximately stable."],
        limitations: ["The peak is a mediated brightness readout, not source identity."],
        alternatives: ["motion", "aliasing", "instrument response"]
      },
      {
        kind: "openplazma.observation_statement",
        version: "0.1.0",
        readoutId: "visible-spectrum-readout",
        artifactId: "visible-spectrum",
        observable: "visible_light",
        readoutKind: "spectral_feature",
        method: "spectral_line_fit",
        selector: "frequencyAnalyses[visible-carrier-spectrum].peaks[green-line-candidate]",
        status: "candidate",
        value: 5.45e14,
        unit: "Hz",
        assumptions: ["Wavelength-to-frequency conversion uses vacuum light speed approximation."],
        limitations: ["The feature is visible-light evidence, not reaction-product evidence."],
        alternatives: ["chemical emission", "thermal emission", "background reflection"]
      }
    ],
    fusionAssessment: {
      kind: "openplazma.fusion_condition_assessment",
      version: "0.1.0",
      assessmentId: "fusion-assessment",
      fusionStatus: "unsupported",
      conditionMode: "not_applicable",
      reactionCandidates: ["unknown"],
      observedOrInferredConditions: [
        {
          parameter: "ion_temperature",
          status: "unknown",
          logicalRole: "unknown",
          evidenceArtifactIds: ["visible-spectrum"],
          evidenceReadoutIds: ["visible-spectrum-readout"],
          method: "coarse_spectrum_review",
          assumptions: [],
          limitations: ["The spectrum is too coarse to infer ion temperature."],
          alternatives: ["chemical emission", "thermal emission"]
        }
      ],
      requiredConditions: [],
      unknowns: ["fuel mix", "density", "confinement time", "particle products"],
      assumptions: ["A glowing atmospheric event is not automatically plasma or fusion."],
      limitations: ["Fusion is treated as a claim to test, not as a premise."]
    },
    claims: [
      {
        kind: "openplazma.investigation_claim",
        version: "0.1.0",
        claimId: "claim-fusion-unsupported",
        claimType: "fusion_status",
        statement: "The supplied will-o'-the-wisp evidence does not support a fusion claim.",
        status: "support",
        evidenceArtifactIds: ["emission-timeseries", "visible-spectrum"],
        evidenceReadoutIds: ["brightness-flicker-readout", "visible-spectrum-readout"],
        method: "evidence_gap_review",
        assumptions: ["The supplied artifact set is complete for this mission step."],
        limitations: ["Absence of evidence is not proof that no fusion source exists."],
        alternatives: ["chemical_luminescence", "electrical_discharge", "sensor_artifact"]
      }
    ],
    limitations: ["Educational investigation package only.", "No real hardware control path."]
  };
}

function inverseFusionAssessment(): FusionConditionAssessment {
  return {
    kind: "openplazma.fusion_condition_assessment",
    version: "0.1.0",
    assessmentId: "solar-inverse",
    fusionStatus: "plausible",
    conditionMode: "inverse_from_fusion_condition",
    reactionCandidates: ["proton_proton_chain"],
    observedOrInferredConditions: [],
    requiredConditions: [
      {
        parameter: "gravity",
        status: "required",
        logicalRole: "necessary",
        unit: "m/s^2",
        evidenceArtifactIds: ["gravity-mode-trace"],
        assumptions: ["Self-gravity supplies the confinement context."],
        limitations: ["This is an inverse condition requirement, not a direct core measurement."]
      },
      {
        parameter: "triple_product",
        status: "required",
        logicalRole: "necessary",
        evidenceArtifactIds: ["gravity-mode-trace"],
        assumptions: ["Fusion is assumed for the inverse stage."],
        limitations: ["Required conditions must still be checked against observations."]
      }
    ],
    unknowns: ["core composition", "central temperature", "central density"],
    assumptions: ["The stage begins from a fusion-holds premise and works backward."],
    limitations: ["Inverse reasoning does not prove the premise by itself."]
  };
}

function organismInteriorPackage(): InvestigationPackage {
  return {
    kind: "openplazma.investigation_package",
    version: "0.1.0",
    packageId: "organism-interior-001",
    title: "Large organism interior energy survey",
    target: {
      kind: "openplazma.investigation_target",
      version: "0.1.0",
      targetId: "large-organism",
      targetKind: "organism_interior",
      label: "Large organism internal cavity",
      description: "A biological target with reported internal heat, light, and magnetic signatures.",
      candidateEnergySources: ["metabolism", "chemical_luminescence", "external_field", "plasma", "fusion", "sensor_artifact"],
      regions: [
        {
          regionId: "abdomen",
          label: "Abdominal cavity",
          description: "Primary internal observation region.",
          limitations: ["All internal diagnostics are remote or derived."]
        },
        {
          regionId: "luminous-organ",
          label: "Luminous organ candidate",
          description: "Localized region with higher emission and temperature signatures.",
          parentRegionId: "abdomen",
          limitations: ["The region may be an imaging artifact or external-field response."]
        }
      ],
      limitations: [
        "Biological behavior can correlate with signals without causing them.",
        "Internal energy-source claims require evidence beyond heat and light."
      ]
    },
    questions: [
      {
        questionId: "q-source",
        questionKind: "energy_source_classification",
        text: "Which energy-source candidates remain plausible after internal diagnostics?"
      },
      {
        questionId: "q-maintenance",
        questionKind: "plasma_maintenance",
        text: "If the luminous region is plasma, what would have to maintain it?"
      },
      {
        questionId: "q-fusion",
        questionKind: "is_fusion",
        text: "Does the internal evidence support a fusion claim?"
      }
    ],
    artifacts: [
      {
        kind: "openplazma.diagnostic_artifact",
        version: "0.1.0",
        artifactId: "thermal-map",
        artifactKind: "thermal_map",
        targetRegionId: "luminous-organ",
        label: "Internal thermal map",
        provenanceKind: "derived",
        quantity: "temperature",
        unit: "K",
        description: "Derived internal temperature map around the luminous region.",
        limitations: ["Thermal maps do not identify the energy source by themselves."]
      },
      {
        kind: "openplazma.diagnostic_artifact",
        version: "0.1.0",
        artifactId: "acoustic-trace",
        artifactKind: "acoustic_trace",
        targetRegionId: "abdomen",
        label: "Internal acoustic trace",
        provenanceKind: "measured",
        quantity: "pressure_wave",
        unit: "a.u.",
        description: "Remote acoustic measurement of internal pulses.",
        limitations: ["Motion and physiology can mimic source periodicity."]
      },
      {
        kind: "openplazma.diagnostic_artifact",
        version: "0.1.0",
        artifactId: "composition-profile",
        artifactKind: "composition_profile",
        targetRegionId: "luminous-organ",
        label: "Atmospheric composition profile",
        provenanceKind: "derived",
        quantity: "composition",
        unit: "fraction",
        description: "Estimated local gas composition near the luminous region.",
        limitations: ["Composition is inferred, not sampled directly."]
      },
      {
        kind: "openplazma.diagnostic_artifact",
        version: "0.1.0",
        artifactId: "mixed-current-trace",
        artifactKind: "signal_series",
        targetRegionId: "luminous-organ",
        label: "Mixed current trace",
        provenanceKind: "measured",
        instrument: {
          instrumentKind: "current_probe",
          label: "Shielded current probe",
          observables: ["electric_current"],
          calibration: {
            status: "estimated",
            responseKnown: false,
            correctionApplied: false,
            description: "Probe response is estimated under unknown internal-field coupling.",
            limitations: ["The current channel may respond to thermal, optical, gravitational, or motion-coupled effects."]
          }
        },
        contributions: [
          {
            contributionKind: "thermal_coupling",
            role: "candidate",
            status: "unresolved",
            description: "Internal heat may induce current through thermal coupling.",
            limitations: ["Thermal coupling has not been independently calibrated."]
          },
          {
            contributionKind: "photoelectric_coupling",
            role: "candidate",
            status: "unresolved",
            description: "Light from the luminous region may drive a photoelectric response.",
            limitations: ["The optical path and sensor response are not separated."]
          },
          {
            contributionKind: "gravity_coupling",
            role: "candidate",
            status: "unresolved",
            description: "Gravity-like variation is retained as a possible coupling term.",
            limitations: ["No independent gravimeter trace is available for this region."]
          },
          {
            contributionKind: "instrument_noise",
            role: "noise",
            status: "unresolved",
            description: "Electronics noise and shielding leakage may contribute.",
            limitations: ["The noise floor is only estimated."]
          }
        ],
        frequencyAnalyses: [
          {
            analysisId: "current-stft",
            domain: "electric_variation",
            method: "stft",
            sourceQuantity: "electric_current",
            sampleRateHz: 200,
            windowSeconds: 4,
            frequencyResolutionHz: 0.25,
            bands: [
              {
                bandId: "low-frequency-current-band",
                domain: "electric_variation",
                label: "Low-frequency current modulation",
                lowerFrequencyHz: 0.25,
                upperFrequencyHz: 20,
                quantity: "current modulation",
                unit: "A",
                description: "Temporal frequency range of the internal current trace.",
                limitations: ["The band can contain source behavior, coupling, motion, and noise."]
              }
            ],
            peaks: [
              {
                peakId: "current-3hz",
                frequencyHz: 3.2,
                amplitude: 0.03,
                signalToNoiseRatio: 2.4,
                interpretation: "Weak current modulation candidate.",
                limitations: ["This peak is below a source-identification threshold."]
              }
            ],
            description: "Short-time Fourier analysis of the mixed current channel.",
            assumptions: ["Sampling intervals are stable after timestamp correction."],
            limitations: ["Current modulation does not distinguish heat, light, gravity, and instrument coupling by itself."]
          }
        ],
        signalIds: ["internal-current"],
        quantity: "electric_current",
        unit: "A",
        description: "Electrical current trace near the luminous internal region.",
        limitations: ["This trace is explicitly modeled as mixed-source until decomposed."]
      }
    ],
    observations: [
      {
        kind: "openplazma.observation_statement",
        version: "0.1.0",
        readoutId: "composition-profile-readout",
        artifactId: "composition-profile",
        targetRegionId: "luminous-organ",
        observable: "composition",
        readoutKind: "summary_statistic",
        method: "derived_profile_review",
        status: "candidate",
        assumptions: ["The derived profile is representative of the luminous region."],
        limitations: ["Composition is inferred, not sampled directly."],
        alternatives: ["external-field response", "imaging artifact"]
      },
      {
        kind: "openplazma.observation_statement",
        version: "0.1.0",
        readoutId: "thermal-map-readout",
        artifactId: "thermal-map",
        targetRegionId: "luminous-organ",
        observable: "temperature",
        readoutKind: "thermal_feature",
        method: "derived_thermal_map_review",
        status: "candidate",
        assumptions: ["The thermal reconstruction is spatially aligned."],
        limitations: ["Thermal maps do not identify the energy source by themselves."],
        alternatives: ["metabolism", "thermal coupling", "external heating"]
      },
      {
        kind: "openplazma.observation_statement",
        version: "0.1.0",
        readoutId: "acoustic-trace-readout",
        artifactId: "acoustic-trace",
        targetRegionId: "abdomen",
        observable: "acoustic_wave",
        readoutKind: "frequency_band",
        method: "remote_acoustic_review",
        status: "candidate",
        assumptions: ["The acoustic channel is time-aligned with the thermal map."],
        limitations: ["Motion and physiology can mimic source periodicity."],
        alternatives: ["motion", "physiology", "sensor coupling"]
      },
      {
        kind: "openplazma.observation_statement",
        version: "0.1.0",
        readoutId: "mixed-current-readout",
        artifactId: "mixed-current-trace",
        signalId: "internal-current",
        targetRegionId: "luminous-organ",
        observable: "electric_current",
        readoutKind: "frequency_peak",
        method: "stft",
        selector: "frequencyAnalyses[current-stft].peaks[current-3hz]",
        status: "candidate",
        value: 3.2,
        unit: "Hz",
        assumptions: ["Sampling intervals are stable after timestamp correction."],
        limitations: ["Current modulation does not distinguish heat, light, gravity, and instrument coupling by itself."],
        alternatives: ["thermal coupling", "photoelectric coupling", "gravity coupling", "instrument noise"]
      }
    ],
    fusionAssessment: {
      kind: "openplazma.fusion_condition_assessment",
      version: "0.1.0",
      assessmentId: "organism-fusion-assessment",
      fusionStatus: "unknown",
      conditionMode: "forward_from_observations",
      reactionCandidates: ["unknown"],
      observedOrInferredConditions: [
        {
          parameter: "composition",
          status: "inferred",
          logicalRole: "supporting",
          evidenceArtifactIds: ["composition-profile"],
          evidenceReadoutIds: ["composition-profile-readout"],
          method: "derived_profile_review",
          assumptions: ["The derived composition profile is representative of the luminous region."],
          limitations: ["No direct fuel sample exists."],
          alternatives: ["imaging artifact", "external-field response"]
        },
        {
          parameter: "confinement_mechanism",
          status: "unknown",
          logicalRole: "unknown",
          evidenceArtifactIds: ["thermal-map", "acoustic-trace"],
          assumptions: [],
          limitations: ["Heat and acoustic periodicity do not establish plasma confinement."]
        },
        {
          parameter: "energy_input",
          status: "bounded",
          logicalRole: "supporting",
          evidenceArtifactIds: ["mixed-current-trace"],
          evidenceReadoutIds: ["mixed-current-readout"],
          method: "stft",
          assumptions: ["The mixed current trace bounds one possible energy-input channel."],
          limitations: ["The current may be induced by heat, light, gravity-like coupling, or noise."],
          alternatives: ["thermal coupling", "photoelectric coupling", "gravity coupling", "instrument noise"]
        }
      ],
      requiredConditions: [
        {
          parameter: "ion_temperature",
          status: "required",
          logicalRole: "necessary",
          evidenceArtifactIds: [],
          assumptions: ["A thermonuclear interpretation would require fusion-relevant ion temperatures."],
          limitations: ["The current artifact set does not measure ion temperature."]
        },
        {
          parameter: "particle_loss",
          status: "required",
          logicalRole: "necessary",
          evidenceArtifactIds: [],
          assumptions: ["Sustained internal plasma would require a loss balance."],
          limitations: ["Particle losses are not measured."]
        }
      ],
      unknowns: ["ion temperature", "particle products", "confinement mechanism", "loss balance"],
      assumptions: ["The organism may be a source, a reactor, a shielded cavity, or a passive responder."],
      limitations: ["The package does not prove plasma or fusion."]
    },
    claims: [
      {
        kind: "openplazma.investigation_claim",
        version: "0.1.0",
        claimId: "claim-internal-fusion-untested",
        claimType: "fusion_status",
        statement: "Internal fusion remains untested because necessary diagnostics are missing.",
        status: "inconclusive",
        evidenceArtifactIds: ["thermal-map", "composition-profile", "mixed-current-trace"],
        evidenceReadoutIds: ["thermal-map-readout", "composition-profile-readout", "mixed-current-readout"],
        method: "evidence_gap_review",
        assumptions: [],
        limitations: ["Thermal and composition evidence can support multiple non-fusion explanations."],
        alternatives: ["metabolism", "chemical_luminescence", "external_field", "sensor_artifact"]
      }
    ],
    limitations: ["Remote biological investigation package only.", "No command/control path."]
  };
}

function runStoreArtifactRef(name: string, artifactType: string, index: number): Record<string, unknown> {
  return {
    artifactName: name,
    artifactType,
    path: `artifacts/${name}.json`,
    sha256: index.toString(16).padStart(64, "0"),
    runArtifactId: `OPA-20260613-${index.toString().padStart(6, "0")}`
  };
}

function observationLineageAudit(): Record<string, unknown> {
  return {
    kind: "openplazma.observation_lineage_audit",
    version: "0.1.0",
    auditId: "obs-lineage-audit-late-mixed",
    runId: "OPR-20260613-000001",
    runGroupId: "public-observation-lineage-audit-noaa-swpc-l1-6h-20260612",
    partitionId: "late-mixed",
    timeWindow: [14400, 21360],
    sourceRefs: [
      {
        ...runStoreArtifactRef("public_snapshot", "public_observation_snapshot", 1),
        sourceRefId: "public-snapshot",
        sourceKind: "public_snapshot",
        datasetId: "real-observation-v0",
        shotId: "noaa-swpc-l1-6h-20260612",
        recordPath: "data/fixtures/real/noaa-swpc-l1-6h-20260612/study-record.json",
        bundleSha256: "4310e71e623ce08b50613f1a6e1109bbf6c9cd7609683eb62f628562c198e5e9"
      },
      {
        ...runStoreArtifactRef("source_provenance", "source_provenance", 2),
        sourceRefId: "source-provenance",
        sourceKind: "source_provenance",
        provider: "NOAA_SWPC",
        sourceLabel: "NOAA SWPC RTSW and GOES X-ray 6-hour public JSON snapshot",
        provenancePath: "data/fixtures/real/noaa-swpc-l1-6h-20260612/source-provenance.json",
        bundleSha256: "4310e71e623ce08b50613f1a6e1109bbf6c9cd7609683eb62f628562c198e5e9",
        rawFileRefs: [
          {
            name: "plasma-6-hour.json",
            path: "data/fixtures/real/noaa-swpc-l1-6h-20260612/raw/plasma-6-hour.json",
            sha256: "6326a9400c3abd8a27b5dd286ac35416b4f74e3d557fbe7e69b5eea428927b00",
            bytes: 17377
          }
        ]
      }
    ],
    transformRefs: [
      {
        ...runStoreArtifactRef("signal_series_solar-wind-proton-density", "signal_series", 3),
        transformId: "signal-series:solar-wind-proton-density",
        transformKind: "signal_series",
        status: "carried_forward",
        method: "frozen_public_snapshot_selection",
        sourceRefIds: ["public-snapshot", "source-provenance"],
        inputSignalIds: ["solar-wind-proton-density"],
        limitationReasons: ["Signal series is copied from the frozen normalized public observation record."]
      },
      {
        ...runStoreArtifactRef("signal_spectrum_solar-wind-proton-density", "signal_spectrum", 4),
        transformId: "signal-spectrum:solar-wind-proton-density",
        transformKind: "signal_spectrum",
        status: "not_computed",
        method: "unknown",
        sourceRefIds: ["public-snapshot", "source-provenance"],
        inputSignalIds: ["solar-wind-proton-density"],
        limitationReasons: ["SignalSpectrum requires an evenly sampled SignalSeries."]
      },
      {
        ...runStoreArtifactRef("investigation_package", "investigation_package", 5),
        transformId: "investigation-package",
        transformKind: "investigation_package",
        status: "computed",
        method: "build_public_observation_campaign",
        sourceRefIds: ["public-snapshot", "source-provenance"],
        inputSignalIds: ["solar-wind-proton-density"],
        limitationReasons: ["Package is conservative evidence review, not fusion validation."]
      }
    ],
    diagnosticArtifactRefs: [
      {
        diagnosticArtifactId: "public-signal-solar-wind-proton-density",
        artifactKind: "signal_series",
        sourceKind: "public_snapshot",
        signalIds: ["solar-wind-proton-density"],
        sourceRefIds: ["public-snapshot", "source-provenance"],
        transformRefIds: [
          "signal-series:solar-wind-proton-density",
          "signal-spectrum:solar-wind-proton-density",
          "investigation-package"
        ],
        calibrationStatus: "unknown",
        calibrationResponseKnown: false,
        uncertaintyStatus: "not_independently_quantified",
        limitationReasons: ["This artifact cannot support a positive fusion claim by itself."]
      }
    ],
    mediatedReadoutRefs: [
      {
        readoutId: "readout-solar-wind-proton-density",
        diagnosticArtifactId: "public-signal-solar-wind-proton-density",
        signalId: "solar-wind-proton-density",
        observable: "density",
        readoutKind: "frequency_band",
        method: "signal_window_summary",
        status: "inconclusive",
        transformRefIds: [
          "signal-series:solar-wind-proton-density",
          "signal-spectrum:solar-wind-proton-density",
          "investigation-package"
        ],
        limitationReasons: ["The readout does not support a positive fusion claim."]
      }
    ],
    spectrumLineage: [
      {
        spectrumId: "public-spectrum-solar-wind-proton-density",
        sourceSignalId: "solar-wind-proton-density",
        status: "not_computed",
        method: "unknown",
        transformRefId: "signal-spectrum:solar-wind-proton-density",
        timeRange: [14400, 21360],
        limitationReasons: ["SignalSpectrum requires an evenly sampled SignalSeries."],
        supportsPositiveFusionInference: false
      }
    ],
    claimAudits: [
      {
        claimId: "claim-solar-wind-proton-density-fusion-unsupported",
        claimSource: "InvestigationPackage.claims",
        claimType: "fusion_status",
        claimStatus: "support",
        statement: "The public solar-wind proton-density readout does not support a fusion claim.",
        positiveFusionClaim: false,
        evidenceArtifactIds: ["public-signal-solar-wind-proton-density"],
        evidenceReadoutIds: ["readout-solar-wind-proton-density"],
        admissibility: "admissible",
        failureReasons: []
      }
    ],
    calibrationSummary: {
      status: "unknown",
      responseKnown: false,
      correctionApplied: false,
      limitationReasons: ["Frozen public products have no independent instrument response model here."]
    },
    uncertaintySummary: {
      status: "limited",
      limitationReasons: ["No independent uncertainty propagation is attached to this audit slice."]
    },
    fusionAssessment: {
      fusionStatus: "unsupported",
      positiveFusionInference: false,
      missingObservables: ["neutron_flux", "gamma_ray", "temperature"],
      requiredProductObservables: ["gamma_ray", "neutron_flux"],
      requiredConditionObservables: ["confinement_time", "density", "ion_temperature", "temperature"]
    },
    status: "passed",
    failureReasons: []
  };
}

describe("ObservationLineageAudit schema", () => {
  it("accepts public NOAA lineage with explicit not_computed spectrum state", () => {
    const audit = parseObservationLineageAudit(observationLineageAudit());

    expect(audit.kind).toBe("openplazma.observation_lineage_audit");
    expect(audit.status).toBe("passed");
    expect(audit.spectrumLineage[0]?.status).toBe("not_computed");
    expect(audit.claimAudits[0]?.admissibility).toBe("admissible");
  });

  it("rejects admitted positive fusion claims from public observation windows", () => {
    const audit = observationLineageAudit();
    const claimAudits = audit["claimAudits"] as Array<Record<string, unknown>>;
    claimAudits[0]!.statement = "Fusion is occurring in the public observation window.";
    claimAudits[0]!.positiveFusionClaim = true;
    claimAudits[0]!.admissibility = "admissible";

    expect(() => parseObservationLineageAudit(audit)).toThrow(/positive fusion claim/);
  });

  it("rejects claim audit rows that omit the audited claim statement", () => {
    const audit = observationLineageAudit();
    const claimAudits = audit["claimAudits"] as Array<Record<string, unknown>>;
    delete claimAudits[0]!.statement;

    expect(() => parseObservationLineageAudit(audit)).toThrow(/statement/);
  });

  it("rejects claim audit rows that omit the audited claim source", () => {
    const audit = observationLineageAudit();
    const claimAudits = audit["claimAudits"] as Array<Record<string, unknown>>;
    delete claimAudits[0]!.claimSource;

    expect(() => parseObservationLineageAudit(audit)).toThrow(/claimSource/);
  });

  it("rejects claim audit rows whose positive fusion flag contradicts the statement", () => {
    const audit = observationLineageAudit();
    const claimAudits = audit["claimAudits"] as Array<Record<string, unknown>>;
    claimAudits[0]!.statement = "Fusion is occurring in the public observation window.";
    claimAudits[0]!.positiveFusionClaim = false;
    claimAudits[0]!.admissibility = "admissible";

    expect(() => parseObservationLineageAudit(audit)).toThrow(/positiveFusionClaim/);
  });

  it("rejects claim audit rows that cite unknown diagnostic artifact evidence", () => {
    const audit = observationLineageAudit();
    const claimAudits = audit["claimAudits"] as Array<Record<string, unknown>>;
    claimAudits[0]!.evidenceArtifactIds = ["ghost-diagnostic-artifact"];

    expect(() => parseObservationLineageAudit(audit)).toThrow(/unknown diagnostic artifact/);
  });

  it("rejects source and transform refs without complete RunStore artifact metadata", () => {
    const missingPath = observationLineageAudit();
    const sourceRefs = missingPath["sourceRefs"] as Array<Record<string, unknown>>;
    delete sourceRefs[0]!.path;

    expect(() => parseObservationLineageAudit(missingPath)).toThrow(/path/);

    const nullSha = observationLineageAudit();
    const transformRefs = nullSha["transformRefs"] as Array<Record<string, unknown>>;
    transformRefs[0]!.sha256 = null;

    expect(() => parseObservationLineageAudit(nullSha)).toThrow(/sha256/);
  });

  it("rejects RunStore artifact paths outside artifacts", () => {
    const audit = observationLineageAudit();
    const sourceRefs = audit["sourceRefs"] as Array<Record<string, unknown>>;
    sourceRefs[0]!.path = "data/public_snapshot.json";

    expect(() => parseObservationLineageAudit(audit)).toThrow(/artifacts/);
  });

  it("rejects ghost source and signal lineage edges", () => {
    const ghostSource = observationLineageAudit();
    const diagnosticRefs = ghostSource["diagnosticArtifactRefs"] as Array<Record<string, unknown>>;
    diagnosticRefs[0]!.sourceRefIds = ["ghost-source"];

    expect(() => parseObservationLineageAudit(ghostSource)).toThrow(/unknown sourceRef/);

    const ghostDiagnosticSignal = observationLineageAudit();
    const ghostDiagnosticRefs = ghostDiagnosticSignal["diagnosticArtifactRefs"] as Array<Record<string, unknown>>;
    ghostDiagnosticRefs[0]!.signalIds = ["ghost-signal"];

    expect(() => parseObservationLineageAudit(ghostDiagnosticSignal)).toThrow(/unknown signal/);

    const ghostReadoutSignal = observationLineageAudit();
    const readoutRefs = ghostReadoutSignal["mediatedReadoutRefs"] as Array<Record<string, unknown>>;
    readoutRefs[0]!.signalId = "ghost-signal";

    expect(() => parseObservationLineageAudit(ghostReadoutSignal)).toThrow(/unknown signal/);

    const ghostSpectrumSignal = observationLineageAudit();
    const spectrumLineage = ghostSpectrumSignal["spectrumLineage"] as Array<Record<string, unknown>>;
    spectrumLineage[0]!.sourceSignalId = "ghost-signal";

    expect(() => parseObservationLineageAudit(ghostSpectrumSignal)).toThrow(/unknown source signal/);
  });

  it("rejects not_computed spectra that self-report positive fusion support", () => {
    const audit = observationLineageAudit();
    const spectrumLineage = audit["spectrumLineage"] as Array<Record<string, unknown>>;
    spectrumLineage[0]!.status = "not_computed";
    spectrumLineage[0]!.supportsPositiveFusionInference = true;

    expect(() => parseObservationLineageAudit(audit)).toThrow(/not_computed spectrum lineage/);
  });
});

describe("InvestigationPackage schema", () => {
  it("keeps will-o'-the-wisp plasma and fusion as separate questions", () => {
    const pack = parseInvestigationPackage(willOWispPackage());

    expect(pack.target.targetKind).toBe("atmospheric_light");
    expect(pack.questions.map((question) => question.questionKind)).toContain("is_plasma");
    expect(pack.questions.map((question) => question.questionKind)).toContain("is_fusion");
    expect(pack.fusionAssessment.fusionStatus).toBe("unsupported");
    expect(pack.fusionAssessment.limitations.join(" ")).toContain("not as a premise");
  });

  it("models light as carrier spectra plus brightness modulation, not a binary flag", () => {
    const pack = parseInvestigationPackage(willOWispPackage());
    const eyeReport = pack.artifacts.find((artifact) => artifact.artifactId === "witness-eye-report");
    const brightness = pack.artifacts.find((artifact) => artifact.artifactId === "emission-timeseries");
    const spectrum = pack.artifacts.find((artifact) => artifact.artifactId === "visible-spectrum");

    expect(eyeReport?.instrument?.instrumentKind).toBe("human_eye");
    expect(eyeReport?.instrument?.calibration.status).toBe("uncalibrated");
    expect(brightness?.frequencyAnalyses?.[0]?.domain).toBe("intensity_modulation");
    expect(brightness?.frequencyAnalyses?.[0]?.method).toBe("fft");
    expect(brightness?.frequencyAnalyses?.[0]?.peaks[0]?.frequencyHz).toBeGreaterThan(0);
    expect(spectrum?.frequencyAnalyses?.[0]?.domain).toBe("electromagnetic_carrier");
    expect(spectrum?.frequencyAnalyses?.[0]?.bands[0]?.lowerFrequencyHz).toBeGreaterThan(1e14);
    expect(spectrum?.contributions?.map((contribution) => contribution.contributionKind)).toContain("background");
  });

  it("validates companion signal windows, spectral features, and structured response uncertainty", () => {
    const pack = willOWispPackage();
    pack.artifacts[1]!.companionChannels = [
      {
        channelId: "visible-camera-brightness",
        signalId: "emission-intensity",
        label: "Visible camera brightness channel",
        role: "primary",
        observable: "visible_light",
        quantity: "brightness",
        unit: "a.u.",
        limitations: ["Camera brightness is not source identity."]
      }
    ];
    pack.artifacts[1]!.signalWindows = [
      {
        windowId: "brightness-analysis-window",
        signalId: "emission-intensity",
        channelId: "visible-camera-brightness",
        role: "primary",
        timeRange: [0, 12],
        sampleCount: 240,
        description: "Window used for brightness modulation analysis.",
        limitations: ["Window choice can smear transient behavior."]
      }
    ];
    pack.artifacts[2]!.instrument!.calibration.response = {
      responseKind: "estimated",
      responseQuantity: "spectral_radiance",
      validFrequencyRangeHz: [4.0e14, 7.9e14],
      uncertainty: {
        value: 0.08,
        unit: "a.u.",
        confidenceLevel: 0.95,
        description: "Estimated response uncertainty for the coarse visible band.",
        limitations: ["Field calibration only."]
      },
      description: "Coarse visible-band response estimate.",
      limitations: ["Not adequate for fusion-product discrimination."]
    };
    pack.artifacts[2]!.spectralFeatures = [
      {
        featureId: "green-line-feature",
        observable: "visible_light",
        status: "candidate",
        frequencyHz: 5.45e14,
        wavelengthMeters: 550e-9,
        amplitude: 0.4,
        signalToNoiseRatio: 3.1,
        identification: "candidate visible emission line",
        uncertainty: {
          value: 0.02e14,
          unit: "Hz",
          description: "Coarse frequency uncertainty from spectral binning.",
          limitations: ["Line fit is not high resolution."]
        },
        description: "Candidate visible spectral feature.",
        limitations: ["Visible spectral features are not fusion-product evidence."],
        alternatives: ["chemical emission", "thermal emission", "background reflection"]
      }
    ];

    const parsed = parseInvestigationPackage(pack);

    expect(parsed.artifacts[1]?.signalWindows?.[0]?.windowId).toBe("brightness-analysis-window");
    expect(parsed.artifacts[2]?.spectralFeatures?.[0]?.featureId).toBe("green-line-feature");
    expect(parsed.artifacts[2]?.instrument?.calibration.response?.uncertainty?.confidenceLevel).toBe(0.95);
  });

  it("rejects signal windows that point outside the artifact signal index", () => {
    const pack = willOWispPackage();
    pack.artifacts[1]!.signalWindows = [
      {
        windowId: "bad-window",
        signalId: "missing-signal",
        role: "companion",
        timeRange: [0, 1],
        description: "Invalid signal window.",
        limitations: ["The signal is not exposed by the artifact."]
      }
    ];

    expect(() => investigationPackageSchema.parse(pack)).toThrow("outside artifact");
  });

  it("allows inverse reasoning from a fusion-holds premise", () => {
    const assessment = fusionConditionAssessmentSchema.parse(inverseFusionAssessment());

    expect(assessment.conditionMode).toBe("inverse_from_fusion_condition");
    expect(assessment.requiredConditions.map((condition) => condition.parameter)).toContain("gravity");
    expect(assessment.limitations.join(" ")).toContain("does not prove the premise");
  });

  it("validates organism interior packages with regional diagnostics", () => {
    const pack = parseInvestigationPackage(organismInteriorPackage());

    expect(pack.target.targetKind).toBe("organism_interior");
    expect(pack.target.regions?.map((region) => region.regionId)).toContain("luminous-organ");
    expect(pack.artifacts.map((artifact) => artifact.artifactKind)).toContain("thermal_map");
    expect(pack.artifacts.map((artifact) => artifact.artifactKind)).toContain("acoustic_trace");
    expect(pack.artifacts.map((artifact) => artifact.artifactId)).toContain("mixed-current-trace");
    expect(pack.fusionAssessment.observedOrInferredConditions.map((condition) => condition.parameter)).toContain(
      "confinement_mechanism"
    );
    expect(pack.fusionAssessment.observedOrInferredConditions.map((condition) => condition.parameter)).toContain(
      "energy_input"
    );
  });

  it("rejects inverse fusion-condition stages with no required conditions", () => {
    const assessment = inverseFusionAssessment();
    assessment.requiredConditions = [];

    expect(() => fusionConditionAssessmentSchema.parse(assessment)).toThrow();
  });

  it("rejects required conditions that are not marked as necessary", () => {
    const assessment = inverseFusionAssessment();
    assessment.requiredConditions[0]!.logicalRole = "supporting";

    expect(() => fusionConditionAssessmentSchema.parse(assessment)).toThrow();
  });

  it("rejects supported fusion claims when condition assessment is closed as not applicable", () => {
    const assessment = inverseFusionAssessment();
    assessment.fusionStatus = "supported";
    assessment.conditionMode = "not_applicable";

    expect(() => fusionConditionAssessmentSchema.parse(assessment)).toThrow();
  });

  it("rejects condition evidence that references a missing diagnostic artifact", () => {
    const pack = willOWispPackage();
    pack.fusionAssessment.observedOrInferredConditions[0]!.evidenceArtifactIds = ["missing-artifact"];

    expect(() => investigationPackageSchema.parse(pack)).toThrow();
  });

  it("rejects duplicate diagnostic artifact ids", () => {
    const pack = willOWispPackage();
    pack.artifacts.push({
      ...pack.artifacts[0]!,
      artifactId: pack.artifacts[1]!.artifactId,
      label: "Duplicate artifact"
    });

    expect(() => investigationPackageSchema.parse(pack)).toThrow("duplicate diagnostic artifact id");
  });

  it("rejects diagnostic artifacts that reference missing target regions", () => {
    const pack = organismInteriorPackage();
    pack.artifacts[0]!.targetRegionId = "missing-region";

    expect(() => investigationPackageSchema.parse(pack)).toThrow();
  });

  it("rejects nested target regions with missing parents", () => {
    const pack = organismInteriorPackage();
    pack.target.regions![1]!.parentRegionId = "missing-parent";

    expect(() => investigationPackageSchema.parse(pack)).toThrow();
  });

  it("rejects empty frequency analyses", () => {
    const pack = willOWispPackage();
    pack.artifacts[1]!.frequencyAnalyses![0]!.bands = [];
    pack.artifacts[1]!.frequencyAnalyses![0]!.peaks = [];

    expect(() => investigationPackageSchema.parse(pack)).toThrow();
  });

  it("rejects inverted frequency bands", () => {
    const pack = willOWispPackage();
    pack.artifacts[1]!.frequencyAnalyses![0]!.bands[0]!.lowerFrequencyHz = 10;
    pack.artifacts[1]!.frequencyAnalyses![0]!.bands[0]!.upperFrequencyHz = 1;

    expect(() => investigationPackageSchema.parse(pack)).toThrow();
  });

  it("validates mediated observation statements and structured artifact sources", () => {
    const pack = willOWispPackage();
    pack.artifacts[1]!.source = {
      sourceKind: "local_fixture",
      label: "Will-o-wisp optical trace fixture",
      artifactIds: [],
      signalIds: ["emission-intensity"],
      limitations: ["Synthetic educational fixture."]
    };
    pack.observations = [
      {
        kind: "openplazma.observation_statement",
        version: "0.1.0",
        readoutId: "brightness-flicker-readout",
        artifactId: "emission-timeseries",
        observable: "visible_light",
        readoutKind: "frequency_peak",
        method: "fft",
        selector: "frequencyAnalyses[brightness-fft].peaks[dominant-flicker]",
        status: "candidate",
        value: 0.67,
        unit: "Hz",
        assumptions: ["The field sample rate is approximately stable."],
        limitations: ["The peak is a mediated brightness readout, not source identity."],
        alternatives: ["motion", "aliasing", "instrument response"]
      }
    ];
    pack.claims[0]!.evidenceReadoutIds = ["brightness-flicker-readout"];
    pack.claims[0]!.method = "evidence_gap_review";
    pack.claims[0]!.alternatives = ["chemical_luminescence", "electrical_discharge", "sensor_artifact"];
    pack.fusionAssessment.observedOrInferredConditions[0]!.evidenceReadoutIds = ["brightness-flicker-readout"];
    pack.fusionAssessment.observedOrInferredConditions[0]!.method = "coarse_spectrum_review";
    pack.fusionAssessment.observedOrInferredConditions[0]!.alternatives = ["thermal emission", "chemical emission"];

    const parsed = parseInvestigationPackage(pack);

    expect(parsed.observations?.[0]?.readoutId).toBe("brightness-flicker-readout");
    expect(parsed.artifacts[1]?.source?.sourceKind).toBe("local_fixture");
    expect(parsed.claims[0]?.evidenceReadoutIds).toContain("brightness-flicker-readout");
  });

  it("rejects artifact-only support claims that skip mediated readouts", () => {
    const pack = willOWispPackage();
    pack.claims[0]!.evidenceReadoutIds = [];

    expect(() => investigationPackageSchema.parse(pack)).toThrow("mediated readout");
  });

  it("rejects positive plasma or fusion claims from unaided human-eye evidence alone", () => {
    const pack = willOWispPackage();
    pack.observations = [
      {
        kind: "openplazma.observation_statement",
        version: "0.1.0",
        readoutId: "eye-visible-readout",
        artifactId: "witness-eye-report",
        observable: "visible_light",
        readoutKind: "human_report",
        method: "unaided_visual_report",
        status: "detected",
        assumptions: ["The witness report is sincere."],
        limitations: ["Human vision is uncalibrated."],
        alternatives: ["combustion", "reflection", "sensor artifact"]
      }
    ];
    pack.fusionAssessment.observedOrInferredConditions = [];
    pack.claims = [
      {
        kind: "openplazma.investigation_claim",
        version: "0.1.0",
        claimId: "claim-eye-proves-plasma",
        claimType: "plasma_presence",
        statement: "The unaided eye report proves the phenomenon is plasma.",
        status: "support",
        evidenceArtifactIds: ["witness-eye-report"],
        evidenceReadoutIds: ["eye-visible-readout"],
        method: "visual_identity_shortcut",
        assumptions: ["Visible glow is plasma."],
        limitations: ["No calibrated diagnostic."],
        alternatives: []
      }
    ];

    expect(() => investigationPackageSchema.parse(pack)).toThrow("human-eye");
  });

  it("rejects visible-light, absence-only, and simulation-as-observation shortcuts", () => {
    const visibleLightPack = willOWispPackage();
    visibleLightPack.observations = [
      {
        kind: "openplazma.observation_statement",
        version: "0.1.0",
        readoutId: "visible-spectrum-readout",
        artifactId: "visible-spectrum",
        observable: "visible_light",
        readoutKind: "spectral_feature",
        method: "spectral_line_fit",
        status: "candidate",
        assumptions: ["The visible feature is stable."],
        limitations: ["Visible light alone does not identify plasma or fusion."],
        alternatives: ["chemical emission", "thermal emission"]
      }
    ];
    visibleLightPack.fusionAssessment.observedOrInferredConditions = [];
    visibleLightPack.claims = [
      {
        kind: "openplazma.investigation_claim",
        version: "0.1.0",
        claimId: "claim-visible-proves-fusion",
        claimType: "fusion_status",
        statement: "Visible light proves fusion is occurring.",
        status: "support",
        evidenceArtifactIds: ["visible-spectrum"],
        evidenceReadoutIds: ["visible-spectrum-readout"],
        method: "visible_light_shortcut",
        assumptions: ["Visible light is a fusion signature."],
        limitations: ["No product diagnostics."],
        alternatives: []
      }
    ];

    expect(() => investigationPackageSchema.parse(visibleLightPack)).toThrow("visible light");

    const absencePack = willOWispPackage();
    absencePack.observations = [
      {
        kind: "openplazma.observation_statement",
        version: "0.1.0",
        readoutId: "neutron-absence-readout",
        artifactId: "visible-spectrum",
        observable: "neutron_flux",
        readoutKind: "absence_statement",
        method: "not_measured",
        status: "not_detected",
        assumptions: ["The visible fixture is treated as the only supplied evidence."],
        limitations: ["There is no neutron detector in the artifact set."],
        alternatives: ["missing diagnostic", "below detection threshold"]
      }
    ];
    absencePack.fusionAssessment.observedOrInferredConditions = [];
    absencePack.claims = [
      {
        kind: "openplazma.investigation_claim",
        version: "0.1.0",
        claimId: "claim-absence-proves-no-fusion",
        claimType: "fusion_status",
        statement: "No neutron flux was observed therefore fusion is absent.",
        status: "support",
        evidenceArtifactIds: ["visible-spectrum"],
        evidenceReadoutIds: ["neutron-absence-readout"],
        method: "absence_shortcut",
        assumptions: ["No observation means absence."],
        limitations: ["The diagnostic adequacy is not established."],
        alternatives: []
      }
    ];

    expect(() => investigationPackageSchema.parse(absencePack)).toThrow("absence");

    const simulationPack = willOWispPackage();
    simulationPack.artifacts[1]!.provenanceKind = "synthetic";
    simulationPack.artifacts[1]!.instrument = {
      instrumentKind: "simulation_diagnostic",
      label: "Synthetic diagnostic",
      observables: ["visible_light"],
      calibration: {
        status: "unknown",
        responseKnown: false,
        correctionApplied: false,
        description: "Synthetic output has no physical instrument response.",
        limitations: ["Simulation output is not an observation of the physical phenomenon."]
      }
    };
    simulationPack.fusionAssessment.observedOrInferredConditions = [];
    simulationPack.observations = [
      {
        kind: "openplazma.observation_statement",
        version: "0.1.0",
        readoutId: "synthetic-visible-readout",
        artifactId: "emission-timeseries",
        observable: "visible_light",
        readoutKind: "model_readout",
        method: "synthetic_fixture",
        status: "detected",
        assumptions: ["Synthetic output represents a scenario."],
        limitations: ["Synthetic output is not a physical observation."],
        alternatives: ["model assumption", "fixture artifact"]
      }
    ];
    simulationPack.claims = [
      {
        kind: "openplazma.investigation_claim",
        version: "0.1.0",
        claimId: "claim-simulation-observed-plasma",
        claimType: "plasma_presence",
        statement: "The simulation observed the phenomenon is plasma.",
        status: "support",
        evidenceArtifactIds: ["emission-timeseries"],
        evidenceReadoutIds: ["synthetic-visible-readout"],
        method: "simulation_observation_shortcut",
        assumptions: ["Synthetic output is physical observation."],
        limitations: ["No measured physical diagnostic."],
        alternatives: []
      }
    ];

    expect(() => investigationPackageSchema.parse(simulationPack)).toThrow("simulation");
  });

  it("validates bundled investigation fixtures from the registry", () => {
    const manifest = parseInvestigationFixtureManifest(
      readFixtureJson("data/fixtures/static/investigations/manifest.json")
    );

    expect(manifest.provider).toBe("STATIC_FIXTURE");
    expect(manifest.datasetId).toBe("static-investigation-v0");
    expect(manifest.packages.map((entry) => entry.packageId)).toEqual([
      "will-o-wisp-001",
      "organism-interior-001",
      "solar-inverse-001"
    ]);

    for (const entry of manifest.packages) {
      const pack = parseInvestigationPackage(readFixtureJson(entry.path));
      expect(pack.packageId).toBe(entry.packageId);
      expect(pack.title).toBe(entry.title);
      expect(pack.limitations.join(" ")).toContain("No");
    }
  });

  it("rejects investigation fixture manifests with duplicate package ids", () => {
    const manifest = readFixtureJson("data/fixtures/static/investigations/manifest.json") as {
      packages: Array<{ packageId: string }>;
    };
    manifest.packages[1]!.packageId = manifest.packages[0]!.packageId;

    expect(() => investigationFixtureManifestSchema.parse(manifest)).toThrow();
  });

  it("validates investigation reports with evidence-linked claims", () => {
    const report = parseInvestigationReport({
      kind: "openplazma.investigation_report",
      version: "0.1.0",
      reportId: "report-will-o-wisp-001",
      packageId: "will-o-wisp-001",
      createdAt: "2026-06-12T00:00:00.000Z",
      claims: [
        {
          kind: "openplazma.investigation_claim",
          version: "0.1.0",
          claimId: "claim-visible-light-insufficient",
          claimType: "fusion_status",
          statement: "Visible light and flicker do not support a fusion claim.",
          status: "support",
          evidenceArtifactIds: ["visible-spectrum", "emission-timeseries"],
          evidenceReadoutIds: ["visible-spectrum-readout"],
          method: "evidence_gap_review",
          assumptions: ["The package is complete for this report step."],
          limitations: ["The report does not prove that no fusion source exists."],
          alternatives: ["chemical emission", "thermal emission", "sensor artifact"]
        }
      ],
      assumptions: ["The supplied static fixture is the evidence set under review."],
      limitations: ["Educational static fixture report."],
      nextObservations: ["Add calibrated particle or high-energy photon diagnostics."]
    });

    expect(report.claims[0]?.evidenceArtifactIds).toContain("visible-spectrum");
    expect(report.nextObservations.join(" ")).toContain("diagnostics");
  });

  it("rejects investigation reports without claims", () => {
    expect(() =>
      investigationReportSchema.parse({
        kind: "openplazma.investigation_report",
        version: "0.1.0",
        reportId: "empty-report",
        packageId: "will-o-wisp-001",
        createdAt: "2026-06-12T00:00:00.000Z",
        claims: [],
        assumptions: [],
        limitations: ["A report needs a limitation."],
        nextObservations: []
      })
    ).toThrow();
  });

  it("rejects report support claims that skip mediated readouts", () => {
    expect(() =>
      investigationReportSchema.parse({
        kind: "openplazma.investigation_report",
        version: "0.1.0",
        reportId: "artifact-only-report",
        packageId: "will-o-wisp-001",
        createdAt: "2026-06-12T00:00:00.000Z",
        claims: [
          {
            kind: "openplazma.investigation_claim",
            version: "0.1.0",
            claimId: "claim-artifact-only",
            claimType: "fusion_status",
            statement: "A diagnostic artifact supports this fusion claim.",
            status: "support",
            evidenceArtifactIds: ["visible-spectrum"],
            method: "artifact_shortcut",
            assumptions: [],
            limitations: ["The mediated readout is missing."],
            alternatives: ["chemical emission"]
          }
        ],
        assumptions: [],
        limitations: ["Reports require mediated claims."],
        nextObservations: []
      })
    ).toThrow("mediated readout");
  });

  it("rejects investigation reports with invalid timestamps", () => {
    expect(() =>
      investigationReportSchema.parse({
        kind: "openplazma.investigation_report",
        version: "0.1.0",
        reportId: "bad-time-report",
        packageId: "will-o-wisp-001",
        createdAt: "today",
        claims: [
          {
            kind: "openplazma.investigation_claim",
            version: "0.1.0",
            claimId: "claim",
            claimType: "source_identity",
            statement: "The source is not identified.",
            status: "inconclusive",
            evidenceArtifactIds: [],
            assumptions: [],
            limitations: ["No calibrated diagnostic."]
          }
        ],
        assumptions: [],
        limitations: ["A report needs a limitation."],
        nextObservations: []
      })
    ).toThrow();
  });

  it("validates investigation sessions around packages and reports", () => {
    const session = parseInvestigationSession({
      kind: "openplazma.investigation_session",
      version: "0.1.0",
      sessionId: "session-will-o-wisp-001",
      createdAt: "2026-06-13T00:00:00.000Z",
      updatedAt: "2026-06-13T00:01:00.000Z",
      status: "reported",
      package: willOWispPackage(),
      requiredObservables: ["visible_light", "electric_current", "neutron_flux"],
      reports: [
        {
          kind: "openplazma.investigation_report",
          version: "0.1.0",
          reportId: "report-will-o-wisp-001",
          packageId: "will-o-wisp-001",
          createdAt: "2026-06-13T00:01:00.000Z",
          claims: [
            {
              kind: "openplazma.investigation_claim",
              version: "0.1.0",
              claimId: "claim-visible-light-insufficient",
              claimType: "fusion_status",
              statement: "Visible light and flicker do not support a fusion claim.",
              status: "support",
              evidenceArtifactIds: ["visible-spectrum", "emission-timeseries"],
              evidenceReadoutIds: ["visible-spectrum-readout"],
              method: "evidence_gap_review",
              assumptions: [],
              limitations: ["The report does not prove that no fusion source exists."],
              alternatives: ["chemical emission", "thermal emission", "sensor artifact"]
            }
          ],
          assumptions: [],
          limitations: ["Session report."],
          nextObservations: ["Add calibrated particle diagnostics."]
        }
      ],
      limitations: ["Read-only external investigation session."]
    });

    expect(session.status).toBe("reported");
    expect(session.requiredObservables).toContain("neutron_flux");
    expect(session.reports[0]?.packageId).toBe(session.package.packageId);
  });

  it("accepts collecting-evidence sessions before diagnostic artifacts arrive", () => {
    const basePackage = willOWispPackage();
    const draftPackage = {
      ...basePackage,
      packageId: "draft-external-session-001",
      artifacts: [],
      observations: [],
      claims: [],
      fusionAssessment: {
        ...basePackage.fusionAssessment,
        assessmentId: "draft-external-session-001-fusion-assessment",
        observedOrInferredConditions: [],
        requiredConditions: [],
        unknowns: ["source identity", "plasma presence", "fusion products"]
      }
    };

    const session = parseInvestigationSession({
      kind: "openplazma.investigation_session",
      version: "0.1.0",
      sessionId: "session-draft-external-001",
      createdAt: "2026-06-13T00:00:00.000Z",
      updatedAt: "2026-06-13T00:00:00.000Z",
      status: "collecting_evidence",
      package: draftPackage,
      requiredObservables: ["visible_light", "electric_current", "neutron_flux"],
      reports: [],
      limitations: ["Read-only external investigation session."]
    });

    expect(session.status).toBe("collecting_evidence");
    expect(session.package.artifacts).toEqual([]);
  });

  it("rejects reported sessions without reports", () => {
    expect(() =>
      investigationSessionSchema.parse({
        kind: "openplazma.investigation_session",
        version: "0.1.0",
        sessionId: "empty-reported-session",
        createdAt: "2026-06-13T00:00:00.000Z",
        updatedAt: "2026-06-13T00:00:00.000Z",
        status: "reported",
        package: willOWispPackage(),
        requiredObservables: [],
        reports: [],
        limitations: ["Read-only external investigation session."]
      })
    ).toThrow();
  });

  it("rejects session reports for a different package", () => {
    const session = {
      kind: "openplazma.investigation_session",
      version: "0.1.0",
      sessionId: "mismatched-session",
      createdAt: "2026-06-13T00:00:00.000Z",
      updatedAt: "2026-06-13T00:01:00.000Z",
      status: "reported",
      package: willOWispPackage(),
      requiredObservables: [],
      reports: [
        {
          kind: "openplazma.investigation_report",
          version: "0.1.0",
          reportId: "wrong-report",
          packageId: "other-package",
          createdAt: "2026-06-13T00:01:00.000Z",
          claims: [
            {
              kind: "openplazma.investigation_claim",
              version: "0.1.0",
              claimId: "claim",
              claimType: "source_identity",
              statement: "The source is unresolved.",
              status: "inconclusive",
              evidenceArtifactIds: [],
              assumptions: [],
              limitations: ["No calibrated diagnostic."]
            }
          ],
          assumptions: [],
          limitations: ["Wrong package boundary."],
          nextObservations: []
        }
      ],
      limitations: ["Read-only external investigation session."]
    };

    expect(() => investigationSessionSchema.parse(session)).toThrow();
  });

  it("rejects session reports with claims outside the package evidence boundary", () => {
    const session = {
      kind: "openplazma.investigation_session",
      version: "0.1.0",
      sessionId: "report-evidence-boundary-session",
      createdAt: "2026-06-13T00:00:00.000Z",
      updatedAt: "2026-06-13T00:01:00.000Z",
      status: "reported",
      package: willOWispPackage(),
      requiredObservables: [],
      reports: [
        {
          kind: "openplazma.investigation_report",
          version: "0.1.0",
          reportId: "report-with-missing-artifact",
          packageId: "will-o-wisp-001",
          createdAt: "2026-06-13T00:01:00.000Z",
          claims: [
            {
              kind: "openplazma.investigation_claim",
              version: "0.1.0",
              claimId: "claim-missing-report-artifact",
              claimType: "source_identity",
              statement: "The report references evidence that is not in the package.",
              status: "support",
              evidenceArtifactIds: ["missing-artifact"],
              evidenceReadoutIds: ["brightness-flicker-readout"],
              method: "boundary_review",
              assumptions: [],
              limitations: ["This claim is outside the evidence boundary."],
              alternatives: ["unknown source"]
            }
          ],
          assumptions: [],
          limitations: ["Report evidence must stay inside the package boundary."],
          nextObservations: []
        }
      ],
      limitations: ["Read-only external investigation session."]
    };

    expect(() => investigationSessionSchema.parse(session)).toThrow("unknown diagnostic artifact");
  });
});
