import type { FixtureManifest, FusionDataSource, ShotMetadata, StudyRecord } from "@openplazma/core";
import { parseFixtureManifest, parseStudyRecord } from "@openplazma/schema";
import fixtureManifestJson from "../../../data/fixtures/static/manifest.json";
import sampleStudyRecordJson from "../../../data/fixtures/static/sample-001/study-record.json";

export const staticFixtureManifest = parseFixtureManifest(fixtureManifestJson);
export const sampleFixtureStudyRecord = parseStudyRecord(sampleStudyRecordJson);

export class StaticFixtureDataSource implements FusionDataSource {
  private readonly records: Map<string, StudyRecord>;
  readonly manifest: FixtureManifest;

  constructor(records: StudyRecord[] = [sampleFixtureStudyRecord], manifest = staticFixtureManifest) {
    this.manifest = manifest;
    this.records = new Map(records.map((record) => [record.shot.shotId, record]));
  }

  async listShots(): Promise<ShotMetadata[]> {
    return Array.from(this.records.values()).map((record) => record.shot);
  }

  async getStudyRecord(shotId: string): Promise<StudyRecord | null> {
    return this.records.get(shotId) ?? null;
  }
}
