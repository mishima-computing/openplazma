import { describe, expect, it } from "vitest";
import {
  fusionConditionAssessmentSchema,
  investigationPackageSchema,
  parseInvestigationPackage
} from "./index";

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
        artifactId: "emission-timeseries",
        artifactKind: "signal_series",
        label: "Emission intensity",
        provenanceKind: "measured",
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

describe("InvestigationPackage schema", () => {
  it("keeps will-o'-the-wisp plasma and fusion as separate questions", () => {
    const pack = parseInvestigationPackage(willOWispPackage());

    expect(pack.target.targetKind).toBe("atmospheric_light");
    expect(pack.questions.map((question) => question.questionKind)).toContain("is_plasma");
    expect(pack.questions.map((question) => question.questionKind)).toContain("is_fusion");
    expect(pack.fusionAssessment.fusionStatus).toBe("unsupported");
    expect(pack.fusionAssessment.limitations.join(" ")).toContain("not as a premise");
  });

  it("allows inverse reasoning from a fusion-holds premise", () => {
    const assessment = fusionConditionAssessmentSchema.parse(inverseFusionAssessment());

    expect(assessment.conditionMode).toBe("inverse_from_fusion_condition");
    expect(assessment.requiredConditions.map((condition) => condition.parameter)).toContain("gravity");
    expect(assessment.limitations.join(" ")).toContain("does not prove the premise");
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
});
