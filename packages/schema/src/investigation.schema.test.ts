import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  fusionConditionAssessmentSchema,
  investigationFixtureManifestSchema,
  investigationPackageSchema,
  parseInvestigationFixtureManifest,
  parseInvestigationPackage
} from "./index";

function readFixtureJson(path: string): unknown {
  return JSON.parse(readFileSync(join(process.cwd(), path), "utf8")) as unknown;
}

function willOWispPackage() {
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
          assumptions: [],
          limitations: ["The spectrum is too coarse to infer ion temperature."]
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
        assumptions: ["The supplied artifact set is complete for this mission step."],
        limitations: ["Absence of evidence is not proof that no fusion source exists."]
      }
    ],
    limitations: ["Educational investigation package only.", "No real hardware control path."]
  };
}

function inverseFusionAssessment() {
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

function organismInteriorPackage() {
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
          assumptions: ["The derived composition profile is representative of the luminous region."],
          limitations: ["No direct fuel sample exists."]
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
          assumptions: ["The mixed current trace bounds one possible energy-input channel."],
          limitations: ["The current may be induced by heat, light, gravity-like coupling, or noise."]
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
        assumptions: [],
        limitations: ["Thermal and composition evidence can support multiple non-fusion explanations."]
      }
    ],
    limitations: ["Remote biological investigation package only.", "No command/control path."]
  };
}

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
});
