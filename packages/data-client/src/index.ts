import type {
  FixtureManifest,
  FusionDataSource,
  InvestigationDataSource,
  InvestigationFixtureManifest,
  InvestigationPackage,
  InvestigationPackageMetadata,
  ShotMetadata,
  StudyRecord
} from "@openplazma/core";
import {
  parseFixtureManifest,
  parseInvestigationFixtureManifest,
  parseInvestigationPackage,
  parseStudyRecord
} from "@openplazma/schema";
import fixtureManifestJson from "../../../data/fixtures/static/manifest.json";
import investigationManifestJson from "../../../data/fixtures/static/investigations/manifest.json";
import organismInteriorInvestigationJson from "../../../data/fixtures/static/investigations/organism-interior-001/investigation-package.json";
import solarInverseInvestigationJson from "../../../data/fixtures/static/investigations/solar-inverse-001/investigation-package.json";
import willOWispInvestigationJson from "../../../data/fixtures/static/investigations/will-o-wisp-001/investigation-package.json";
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
export const staticInvestigationFixtureManifest = parseInvestigationFixtureManifest(investigationManifestJson);
export const willOWispInvestigationPackage = parseInvestigationPackage(willOWispInvestigationJson);
export const organismInteriorInvestigationPackage = parseInvestigationPackage(organismInteriorInvestigationJson);
export const solarInverseInvestigationPackage = parseInvestigationPackage(solarInverseInvestigationJson);

export class StaticFixtureDataSource implements FusionDataSource, InvestigationDataSource {
  private readonly records: Map<string, StudyRecord>;
  private readonly investigationPackages: Map<string, InvestigationPackage>;
  readonly manifest: FixtureManifest;
  readonly investigationManifest: InvestigationFixtureManifest;

  constructor(
    records: StudyRecord[] = [
      sampleFixtureStudyRecord,
      mhdFixtureStudyRecord,
      elmFixtureStudyRecord,
      sawtoothFixtureStudyRecord,
      ntmFixtureStudyRecord,
      densityLimitFixtureStudyRecord
    ],
    manifest = staticFixtureManifest,
    investigationPackages: InvestigationPackage[] = [
      willOWispInvestigationPackage,
      organismInteriorInvestigationPackage,
      solarInverseInvestigationPackage
    ],
    investigationManifest = staticInvestigationFixtureManifest
  ) {
    this.manifest = manifest;
    this.investigationManifest = investigationManifest;
    this.records = new Map(records.map((record) => [record.shot.shotId, record]));
    this.investigationPackages = new Map<string, InvestigationPackage>();
    for (const pack of investigationPackages) {
      if (this.investigationPackages.has(pack.packageId)) {
        throw new Error(`duplicate investigation package id '${pack.packageId}'`);
      }
      this.investigationPackages.set(pack.packageId, pack);
    }
    for (const entry of this.investigationManifest.packages) {
      const pack = this.investigationPackages.get(entry.packageId);
      if (pack === undefined) {
        throw new Error(`Investigation fixture manifest references missing package '${entry.packageId}'`);
      }
      if (pack.title !== entry.title) {
        throw new Error(`Investigation fixture manifest title for package '${entry.packageId}' does not match the package payload title`);
      }
    }
  }

  async listShots(): Promise<ShotMetadata[]> {
    return Array.from(this.records.values()).map((record) => record.shot);
  }

  async getStudyRecord(shotId: string): Promise<StudyRecord | null> {
    return this.records.get(shotId) ?? null;
  }

  async listInvestigationPackages(): Promise<InvestigationPackageMetadata[]> {
    return [...this.investigationManifest.packages];
  }

  async getInvestigationPackage(packageId: string): Promise<InvestigationPackage | null> {
    return this.investigationPackages.get(packageId) ?? null;
  }
}
