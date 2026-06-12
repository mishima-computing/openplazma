import { useEffect, useMemo, useState } from "react";
import { assessInvestigationMeasurements } from "@openplazma/analysis";
import type {
  DiagnosticArtifact,
  InvestigationClaim,
  InvestigationPackage,
  InvestigationPackageMetadata,
  MeasuredObservable
} from "@openplazma/core";
import type { StaticFixtureDataSource } from "@openplazma/data-client";

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

  const assessment = useMemo(() => {
    return pack ? assessInvestigationMeasurements(pack, fusionScreenObservables) : null;
  }, [pack]);

  if (!pack || !assessment) {
    return null;
  }

  return (
    <section className="panel investigation-panel" aria-labelledby="investigation-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Investigation Workbench</p>
          <h2 id="investigation-heading">{pack.title}</h2>
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
          <h3>{pack.target.label}</h3>
          <p>{pack.target.description}</p>
        </div>
        <dl className="investigation-meta-grid">
          <div>
            <dt>Kind</dt>
            <dd>{pack.target.targetKind}</dd>
          </div>
          <div>
            <dt>Sources</dt>
            <dd>{joinValues(pack.target.candidateEnergySources)}</dd>
          </div>
          <div>
            <dt>Fusion status</dt>
            <dd>{pack.fusionAssessment.fusionStatus}</dd>
          </div>
          <div>
            <dt>Condition mode</dt>
            <dd>{pack.fusionAssessment.conditionMode}</dd>
          </div>
        </dl>
      </section>

      {pack.target.regions && pack.target.regions.length > 0 ? (
        <ul className="region-list" aria-label="Target regions">
          {pack.target.regions.map((region) => (
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
          <dd>{joinValues(assessment.missingObservables)}</dd>
        </div>
        <div>
          <dt>Unresolved artifacts</dt>
          <dd>{joinValues(assessment.unresolvedArtifactIds)}</dd>
        </div>
      </dl>

      <section className="investigation-artifact-list" aria-label="Diagnostic artifacts">
        {pack.artifacts.map((artifact) => (
          <ArtifactRow key={artifact.artifactId} artifact={artifact} />
        ))}
      </section>

      <ul className="claim-list" aria-label="Investigation claims">
        {pack.claims.map((claim) => (
          <ClaimRow key={claim.claimId} claim={claim} />
        ))}
      </ul>
    </section>
  );
}
