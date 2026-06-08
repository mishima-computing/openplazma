import type { FixtureManifest, FusionDataSource, ShotMetadata, StudyRecord } from "@openplazma/core";
import { parseFixtureManifest, parseStudyRecord } from "@openplazma/schema";
import fixtureManifestJson from "../../../data/fixtures/static/manifest.json";
import sampleStudyRecordJson from "../../../data/fixtures/static/sample-001/study-record.json";
import mhdStudyRecordJson from "../../../data/fixtures/static/mhd-mode-001/study-record.json";
import elmStudyRecordJson from "../../../data/fixtures/static/elm-h-mode-001/study-record.json";
import sawtoothStudyRecordJson from "../../../data/fixtures/static/sawtooth-001/study-record.json";
import ntmStudyRecordJson from "../../../data/fixtures/static/ntm-3-2-001/study-record.json";
import densityLimitStudyRecordJson from "../../../data/fixtures/static/density-limit-001/study-record.json";

export const staticFixtureManifest = parseFixtureManifest(fixtureManifestJson);
export const sampleFixtureStudyRecord = parseStudyRecord(sampleStudyRecordJson);
export const mhdFixtureStudyRecord = parseStudyRecord(mhdStudyRecordJson);
export const elmFixtureStudyRecord = parseStudyRecord(elmStudyRecordJson);
export const sawtoothFixtureStudyRecord = parseStudyRecord(sawtoothStudyRecordJson);
export const ntmFixtureStudyRecord = parseStudyRecord(ntmStudyRecordJson);
export const densityLimitFixtureStudyRecord = parseStudyRecord(densityLimitStudyRecordJson);

export class StaticFixtureDataSource implements FusionDataSource {
  private readonly records: Map<string, StudyRecord>;
  readonly manifest: FixtureManifest;

  constructor(
    records: StudyRecord[] = [
      sampleFixtureStudyRecord,
      mhdFixtureStudyRecord,
      elmFixtureStudyRecord,
      sawtoothFixtureStudyRecord,
      ntmFixtureStudyRecord,
      densityLimitFixtureStudyRecord
    ],
    manifest = staticFixtureManifest
  ) {
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
