import { describe, expect, it } from "vitest";
import { StaticFixtureDataSource } from "./index";

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
});
