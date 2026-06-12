import { describe, expect, it } from "vitest";
import { organismInteriorInvestigationPackage, StaticFixtureDataSource, willOWispInvestigationPackage } from "./index";

describe("StaticFixtureDataSource", () => {
  it("loads the bundled manifest and sample shot", async () => {
    const dataSource = new StaticFixtureDataSource();

    await expect(dataSource.listShots()).resolves.toHaveLength(6);
    await expect(dataSource.getStudyRecord("sample-001")).resolves.toMatchObject({
      context: {
        datasetId: "static-fixture-v0",
        target: {
          type: "static_fixture"
        },
        capabilities: {
          controlFacility: false
        }
      },
      shot: {
        source: {
          provider: "STATIC_FIXTURE",
          inspiredBy: "FAIR_MAST"
        }
      }
    });
    expect(dataSource.manifest.provider).toBe("STATIC_FIXTURE");
  });

  it("loads the synthetic MHD mode shot with its analysis bundle", async () => {
    const dataSource = new StaticFixtureDataSource();

    const record = await dataSource.getStudyRecord("mhd-mode-001");
    expect(record?.shot.source.kind).toBe("synthetic");
    expect(record?.mhd?.arrays[0]?.channels).toHaveLength(8);
    expect(record?.mhd?.claims[0]?.observationModelId).toBe("tm-2-1");
    expect(record?.mhd?.inferences[0]?.lockingDetected).toBe(true);
  });

  it("loads the synthetic ELM H-mode shot with its ELM analysis", async () => {
    const dataSource = new StaticFixtureDataSource();

    const record = await dataSource.getStudyRecord("elm-h-mode-001");
    expect(record?.mhd?.elmAnalyses?.[0]?.classification).toBe("type_I");
    expect(record?.mhd?.elmAnalyses?.[0]?.crashes).toHaveLength(10);
    expect(record?.mhd?.claims[0]?.elmAnalysisId).toBe("elm-d-alpha");
  });

  it("loads the sawtooth, NTM, and density-limit phenomenon shots", async () => {
    const dataSource = new StaticFixtureDataSource();

    const sawtooth = await dataSource.getStudyRecord("sawtooth-001");
    expect(sawtooth?.mhd?.events.every((e) => e.phenomenon === "sawtooth_crash")).toBe(true);
    expect(sawtooth?.mhd?.claims[0]?.eventIds).toHaveLength(12);

    const ntm = await dataSource.getStudyRecord("ntm-3-2-001");
    expect(ntm?.mhd?.inferences[0]?.modeEstimate.toroidalModeNumber).toBe(2);
    expect(ntm?.mhd?.inferences[0]?.modeEstimate.islandWidthM).toBeGreaterThan(0);
    expect(ntm?.mhd?.inferences[0]?.lockingDetected).toBe(false);

    const density = await dataSource.getStudyRecord("density-limit-001");
    expect(density?.mhd?.events.map((e) => e.phenomenon)).toContain("density_limit");
    expect(density?.mhd?.events.map((e) => e.phenomenon)).toContain("radiative_collapse");
  });

  it("returns null for an unknown shot", async () => {
    const dataSource = new StaticFixtureDataSource();

    await expect(dataSource.getStudyRecord("missing-shot")).resolves.toBeNull();
  });

  it("loads the bundled investigation fixture registry", async () => {
    const dataSource = new StaticFixtureDataSource();

    await expect(dataSource.listInvestigationPackages()).resolves.toEqual([
      {
        packageId: "will-o-wisp-001",
        title: "Will-o'-the-wisp first anomaly",
        path: "data/fixtures/static/investigations/will-o-wisp-001/investigation-package.json"
      },
      {
        packageId: "organism-interior-001",
        title: "Large organism interior energy survey",
        path: "data/fixtures/static/investigations/organism-interior-001/investigation-package.json"
      },
      {
        packageId: "solar-inverse-001",
        title: "Solar inverse fusion-condition seed",
        path: "data/fixtures/static/investigations/solar-inverse-001/investigation-package.json"
      }
    ]);
    expect(dataSource.investigationManifest.datasetId).toBe("static-investigation-v0");
  });

  it("loads investigation packages by id", async () => {
    const dataSource = new StaticFixtureDataSource();

    const willOWisp = await dataSource.getInvestigationPackage("will-o-wisp-001");
    expect(willOWisp?.target.targetKind).toBe("atmospheric_light");
    expect(willOWisp?.artifacts.map((artifact) => artifact.artifactId)).toContain("visible-spectrum");

    const organism = await dataSource.getInvestigationPackage("organism-interior-001");
    expect(organism?.target.regions?.map((region) => region.regionId)).toContain("luminous-organ");
    expect(organism?.artifacts.map((artifact) => artifact.artifactId)).toContain("mixed-current-trace");

    const solar = await dataSource.getInvestigationPackage("solar-inverse-001");
    expect(solar?.fusionAssessment.conditionMode).toBe("inverse_from_fusion_condition");
    expect(solar?.fusionAssessment.requiredConditions.map((condition) => condition.parameter)).toContain("gravity");
  });

  it("returns null for an unknown investigation package", async () => {
    const dataSource = new StaticFixtureDataSource();

    await expect(dataSource.getInvestigationPackage("missing-investigation")).resolves.toBeNull();
  });

  it("fails fast when the investigation manifest references a missing package", () => {
    expect(
      () =>
        new StaticFixtureDataSource([], undefined, [], {
          kind: "openplazma.investigation_fixture_manifest",
          version: "0.1.0",
          provider: "STATIC_FIXTURE",
          datasetId: "broken",
          packages: [
            {
              packageId: "missing-investigation",
              title: "Missing investigation",
              path: "data/fixtures/static/investigations/missing/investigation-package.json"
            }
          ]
        })
    ).toThrow("missing-investigation");
  });

  it("fails fast when supplied investigation packages contain duplicate package ids", () => {
    expect(
      () =>
        new StaticFixtureDataSource(
          [],
          undefined,
          [
            willOWispInvestigationPackage,
            {
              ...organismInteriorInvestigationPackage,
              packageId: willOWispInvestigationPackage.packageId,
              title: "Duplicate will-o-wisp payload"
            }
          ],
          {
            kind: "openplazma.investigation_fixture_manifest",
            version: "0.1.0",
            provider: "STATIC_FIXTURE",
            datasetId: "broken",
            packages: [
              {
                packageId: "will-o-wisp-001",
                title: "Will-o'-the-wisp first anomaly",
                path: "data/fixtures/static/investigations/will-o-wisp-001/investigation-package.json"
              }
            ]
          }
        )
    ).toThrow("duplicate investigation package id");
  });

  it("fails fast when investigation manifest metadata drifts from the package payload", () => {
    expect(
      () =>
        new StaticFixtureDataSource(
          [],
          undefined,
          [willOWispInvestigationPackage],
          {
            kind: "openplazma.investigation_fixture_manifest",
            version: "0.1.0",
            provider: "STATIC_FIXTURE",
            datasetId: "broken",
            packages: [
              {
                packageId: "will-o-wisp-001",
                title: "Wrong manifest title",
                path: "data/fixtures/static/investigations/will-o-wisp-001/investigation-package.json"
              }
            ]
          }
        )
    ).toThrow("manifest title");
  });

  it("fails fast when supplied investigation packages are not registered in the manifest", () => {
    expect(
      () =>
        new StaticFixtureDataSource(
          [],
          undefined,
          [willOWispInvestigationPackage, organismInteriorInvestigationPackage],
          {
            kind: "openplazma.investigation_fixture_manifest",
            version: "0.1.0",
            provider: "STATIC_FIXTURE",
            datasetId: "broken",
            packages: [
              {
                packageId: "will-o-wisp-001",
                title: "Will-o'-the-wisp first anomaly",
                path: "data/fixtures/static/investigations/will-o-wisp-001/investigation-package.json"
              }
            ]
          }
        )
    ).toThrow("unregistered investigation package");
  });
});
