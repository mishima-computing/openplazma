import { describe, expect, it } from "vitest";
import { StaticFixtureDataSource } from "./index";

describe("StaticFixtureDataSource", () => {
  it("loads the bundled manifest and sample shot", async () => {
    const dataSource = new StaticFixtureDataSource();

    await expect(dataSource.listShots()).resolves.toHaveLength(2);
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

  it("returns null for an unknown shot", async () => {
    const dataSource = new StaticFixtureDataSource();

    await expect(dataSource.getStudyRecord("missing-shot")).resolves.toBeNull();
  });
});
