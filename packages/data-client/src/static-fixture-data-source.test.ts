import { describe, expect, it } from "vitest";
import { StaticFixtureDataSource } from "./index";

describe("StaticFixtureDataSource", () => {
  it("loads the bundled manifest and sample shot", async () => {
    const dataSource = new StaticFixtureDataSource();

    await expect(dataSource.listShots()).resolves.toHaveLength(1);
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

  it("returns null for an unknown shot", async () => {
    const dataSource = new StaticFixtureDataSource();

    await expect(dataSource.getStudyRecord("missing-shot")).resolves.toBeNull();
  });
});
