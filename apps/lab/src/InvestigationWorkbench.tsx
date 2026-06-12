import { useEffect, useMemo, useState } from "react";
import { assessInvestigationMeasurements } from "@openplazma/analysis";
import type {
  DiagnosticArtifact,
  InvestigationClaim,
  InvestigationClaimStatus,
  InvestigationClaimType,
  InvestigationPackage,
  InvestigationPackageMetadata,
  InvestigationReport,
  MeasuredObservable
} from "@openplazma/core";
import type { StaticFixtureDataSource } from "@openplazma/data-client";
import { parseInvestigationReport } from "@openplazma/schema";

const fusionScreenObservables: MeasuredObservable[] = [
  "visible_light",
  "electric_current",
  "neutron_flux",
  "gamma_ray",
  "neutrino_flux"
];

function joinValues(values: readonly string[] | undefined): string {
  return values && values.length > 0 ? values.join(", ") : "None";
}

function downloadJson(filename: string, value: unknown) {
  const blob = new Blob([JSON.stringify(value, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function ArtifactRow({ artifact }: { artifact: DiagnosticArtifact }) {
  const analyses = artifact.frequencyAnalyses ?? [];
  const contributions = artifact.contributions ?? [];

  return (
    <article className="investigation-artifact">
      <div className="investigation-artifact-main">
        <div>
          <h3>{artifact.label}</h3>
          <p>{artifact.description}</p>
        </div>
        <span className="artifact-kind">{artifact.artifactKind}</span>
      </div>
      <dl className="investigation-meta-grid">
        <div>
          <dt>Instrument</dt>
          <dd>{artifact.instrument?.label ?? "None"}</dd>
        </div>
        <div>
          <dt>Calibration</dt>
          <dd>{artifact.instrument?.calibration.status ?? "missing"}</dd>
        </div>
        <div>
          <dt>Observables</dt>
          <dd>{joinValues(artifact.instrument?.observables)}</dd>
        </div>
        <div>
          <dt>Region</dt>
          <dd>{artifact.targetRegionId ?? "Whole target"}</dd>
        </div>
      </dl>
      {contributions.length > 0 ? (
        <ul className="investigation-token-list" aria-label={`${artifact.label} contributions`}>
          {contributions.map((contribution, index) => (
            <li key={`${contribution.contributionKind}-${index}`}>
              <span>{contribution.contributionKind}</span>
              <small>
                {contribution.role} / {contribution.status}
              </small>
            </li>
          ))}
        </ul>
      ) : null}
      {analyses.length > 0 ? (
        <ul className="frequency-list" aria-label={`${artifact.label} frequency analyses`}>
          {analyses.map((analysis) => (
            <li key={analysis.analysisId}>
              <strong>{analysis.domain}</strong>
              <span>{analysis.method}</span>
              <span>{analysis.peaks.length} peaks</span>
              <span>{analysis.bands.length} bands</span>
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}

function ClaimRow({ claim }: { claim: InvestigationClaim }) {
  return (
    <li className={`claim-row claim-${claim.status}`}>
      <span className="claim-status">{claim.status}</span>
      <span>{claim.statement}</span>
    </li>
  );
}

export function InvestigationWorkbench({ dataSource }: { dataSource: StaticFixtureDataSource }) {
  const [entries, setEntries] = useState<InvestigationPackageMetadata[]>([]);
  const [selectedPackageId, setSelectedPackageId] = useState("");
  const [pack, setPack] = useState<InvestigationPackage | null>(null);
  const [claimType, setClaimType] = useState<InvestigationClaimType>("source_identity");
  const [claimStatus, setClaimStatus] = useState<InvestigationClaimStatus>("inconclusive");
  const [claimStatement, setClaimStatement] = useState("");
  const [selectedEvidenceIds, setSelectedEvidenceIds] = useState<string[]>([]);
  const [reportAssumption, setReportAssumption] = useState("");
  const [reportLimitation, setReportLimitation] = useState("");
  const [nextObservation, setNextObservation] = useState("");

  useEffect(() => {
    void dataSource.listInvestigationPackages().then((loadedEntries) => {
      setEntries(loadedEntries);
      setSelectedPackageId((current) => current || loadedEntries[0]?.packageId || "");
    });
  }, [dataSource]);

  useEffect(() => {
    if (selectedPackageId === "") {
      return;
    }
    void dataSource.getInvestigationPackage(selectedPackageId).then(setPack);
  }, [dataSource, selectedPackageId]);

  useEffect(() => {
    if (!pack) {
      return;
    }
    const seedClaim = pack.claims[0];
    setClaimType(seedClaim?.claimType ?? "source_identity");
    setClaimStatus(seedClaim?.status ?? "inconclusive");
    setClaimStatement(seedClaim?.statement ?? "");
    setSelectedEvidenceIds(pack.artifacts.slice(0, 2).map((artifact) => artifact.artifactId));
    setReportAssumption("The supplied static investigation package is the evidence set under review.");
    setReportLimitation("Read-only static fixture report; no facility telemetry or control path.");
    setNextObservation(
      pack.fusionAssessment.unknowns[0]
        ? `Add a calibrated diagnostic for ${pack.fusionAssessment.unknowns[0]}.`
        : "Add a calibrated diagnostic for the largest unresolved claim."
    );
  }, [pack]);

  const assessment = useMemo(() => {
    return pack ? assessInvestigationMeasurements(pack, fusionScreenObservables) : null;
  }, [pack]);

  const currentPack = pack;
  const currentAssessment = assessment;
  const canExportReport =
    claimStatement.trim().length > 0 && selectedEvidenceIds.length > 0 && reportLimitation.trim().length > 0;
  const reportPreview = useMemo(() => {
    if (!currentPack || !canExportReport) {
      return "";
    }
    return JSON.stringify(buildReport(currentPack), null, 2);
  }, [
    canExportReport,
    claimStatement,
    claimStatus,
    claimType,
    currentPack,
    nextObservation,
    reportAssumption,
    reportLimitation,
    selectedEvidenceIds
  ]);

  if (!currentPack || !currentAssessment) {
    return null;
  }

  function toggleEvidence(artifactId: string) {
    setSelectedEvidenceIds((current) =>
      current.includes(artifactId) ? current.filter((id) => id !== artifactId) : [...current, artifactId]
    );
  }

  function buildReport(currentPack: InvestigationPackage): InvestigationReport {
    const report = parseInvestigationReport({
      kind: "openplazma.investigation_report",
      version: "0.1.0",
      reportId: `report-${currentPack.packageId}`,
      packageId: currentPack.packageId,
      createdAt: new Date().toISOString(),
      claims: [
        {
          kind: "openplazma.investigation_claim",
          version: "0.1.0",
          claimId: `claim-${currentPack.packageId}-draft`,
          claimType,
          statement: claimStatement.trim(),
          status: claimStatus,
          evidenceArtifactIds: selectedEvidenceIds,
          assumptions: reportAssumption.trim() ? [reportAssumption.trim()] : [],
          limitations: reportLimitation.trim() ? [reportLimitation.trim()] : ["No report limitation supplied."]
        }
      ],
      assumptions: reportAssumption.trim() ? [reportAssumption.trim()] : [],
      limitations: reportLimitation.trim() ? [reportLimitation.trim()] : ["No report limitation supplied."],
      nextObservations: nextObservation.trim() ? [nextObservation.trim()] : []
    });
    return report;
  }

  function exportReport() {
    if (currentPack === null) {
      return;
    }
    const report = buildReport(currentPack);
    downloadJson(`${currentPack.packageId}-investigation-report.json`, report);
  }

  return (
    <section className="panel investigation-panel" aria-labelledby="investigation-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Investigation Workbench</p>
          <h2 id="investigation-heading">{currentPack.title}</h2>
        </div>
        <div className="signal-tabs" role="list" aria-label="Investigation packages">
          {entries.map((entry) => (
            <button
              key={entry.packageId}
              type="button"
              className={entry.packageId === selectedPackageId ? "signal-tab is-active" : "signal-tab"}
              onClick={() => setSelectedPackageId(entry.packageId)}
            >
              {entry.packageId}
            </button>
          ))}
        </div>
      </div>

      <section className="investigation-summary" aria-label="Investigation target">
        <div>
          <p className="eyebrow">Target</p>
          <h3>{currentPack.target.label}</h3>
          <p>{currentPack.target.description}</p>
        </div>
        <dl className="investigation-meta-grid">
          <div>
            <dt>Kind</dt>
            <dd>{currentPack.target.targetKind}</dd>
          </div>
          <div>
            <dt>Sources</dt>
            <dd>{joinValues(currentPack.target.candidateEnergySources)}</dd>
          </div>
          <div>
            <dt>Fusion status</dt>
            <dd>{currentPack.fusionAssessment.fusionStatus}</dd>
          </div>
          <div>
            <dt>Condition mode</dt>
            <dd>{currentPack.fusionAssessment.conditionMode}</dd>
          </div>
        </dl>
      </section>

      {currentPack.target.regions && currentPack.target.regions.length > 0 ? (
        <ul className="region-list" aria-label="Target regions">
          {currentPack.target.regions.map((region) => (
            <li key={region.regionId}>
              <strong>{region.label}</strong>
              <span>{region.regionId}</span>
            </li>
          ))}
        </ul>
      ) : null}

      <dl className="measurement-strip" aria-label="Measurement assessment">
        <div>
          <dt>Missing observables</dt>
          <dd>{joinValues(currentAssessment.missingObservables)}</dd>
        </div>
        <div>
          <dt>Unresolved artifacts</dt>
          <dd>{joinValues(currentAssessment.unresolvedArtifactIds)}</dd>
        </div>
      </dl>

      <section className="investigation-artifact-list" aria-label="Diagnostic artifacts">
        {currentPack.artifacts.map((artifact) => (
          <ArtifactRow key={artifact.artifactId} artifact={artifact} />
        ))}
      </section>

      <ul className="claim-list" aria-label="Investigation claims">
        {currentPack.claims.map((claim) => (
          <ClaimRow key={claim.claimId} claim={claim} />
        ))}
      </ul>

      <section className="report-builder" aria-labelledby="report-builder-heading">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Report Builder</p>
            <h3 id="report-builder-heading">Evidence report</h3>
          </div>
          <button type="button" className="primary-action" onClick={exportReport} disabled={!canExportReport}>
            Export Report JSON
          </button>
        </div>
        <div className="report-form-grid">
          <label>
            Claim type
            <select value={claimType} onChange={(event) => setClaimType(event.currentTarget.value as InvestigationClaimType)}>
              <option value="source_identity">source_identity</option>
              <option value="plasma_presence">plasma_presence</option>
              <option value="fusion_status">fusion_status</option>
              <option value="fusion_conditions">fusion_conditions</option>
              <option value="plasma_maintenance">plasma_maintenance</option>
            </select>
          </label>
          <label>
            Status
            <select
              value={claimStatus}
              onChange={(event) => setClaimStatus(event.currentTarget.value as InvestigationClaimStatus)}
            >
              <option value="inconclusive">inconclusive</option>
              <option value="support">support</option>
              <option value="contradict">contradict</option>
              <option value="untested">untested</option>
            </select>
          </label>
        </div>
        <label>
          Claim
          <textarea value={claimStatement} onChange={(event) => setClaimStatement(event.currentTarget.value)} rows={3} />
        </label>
        <fieldset className="evidence-fieldset">
          <legend>Evidence artifacts</legend>
          <div className="evidence-checkbox-grid">
            {currentPack.artifacts.map((artifact) => (
              <label key={artifact.artifactId} className="evidence-checkbox">
                <input
                  type="checkbox"
                  checked={selectedEvidenceIds.includes(artifact.artifactId)}
                  onChange={() => toggleEvidence(artifact.artifactId)}
                />
                <span>{artifact.artifactId}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <div className="report-form-grid">
          <label>
            Assumption
            <textarea value={reportAssumption} onChange={(event) => setReportAssumption(event.currentTarget.value)} rows={3} />
          </label>
          <label>
            Limitation
            <textarea value={reportLimitation} onChange={(event) => setReportLimitation(event.currentTarget.value)} rows={3} />
          </label>
        </div>
        <label>
          Next observation
          <input value={nextObservation} onChange={(event) => setNextObservation(event.currentTarget.value)} />
        </label>
        <pre aria-label="Investigation report preview">
          {reportPreview || "Complete claim, evidence, and limitation to preview the report."}
        </pre>
      </section>
    </section>
  );
}
