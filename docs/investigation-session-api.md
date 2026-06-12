# Investigation Session API

`InvestigationSession` is the neutral boundary for an external application that
wants OpenPlazma to organize observation evidence, conservative assessments, and
evidence-linked reports.

The external application owns its domain state. OpenPlazma owns the read-only
investigation contract:

```text
external target or event
  -> InvestigationTarget
  -> DiagnosticArtifact[]
  -> InvestigationClaim[]
  -> InvestigationSession
  -> InvestigationMeasurementAssessment + InvestigationReport
```

This API does not encode product-specific progression, scoring, hosted service
features, facility telemetry, or control. It accepts neutral diagnostic evidence
and returns neutral evidence state.

## Minimum Flow

```ts
import {
  addDiagnosticArtifact,
  addInvestigationClaim,
  assessInvestigationSession,
  buildInvestigationPackage,
  createInvestigationSession,
  createInvestigationSessionReport,
  recordInvestigationReport
} from "@openplazma/analysis";

const pack = buildInvestigationPackage({
  packageId: "external-session-001",
  title: "External investigation session",
  target,
  questions,
  limitations: ["External target semantics are supplied outside OpenPlazma."]
});

let session = createInvestigationSession({
  sessionId: "session-external-001",
  package: pack,
  requiredObservables: ["visible_light", "electric_current", "neutron_flux"]
});

session = addDiagnosticArtifact(session, artifact);
session = addInvestigationClaim(session, claim);

const assessment = assessInvestigationSession(session);
const report = createInvestigationSessionReport(session);
session = recordInvestigationReport(session, report);
```

## Function Roles

- `buildInvestigationPackage(input)` creates a neutral package from target,
  questions, optional artifacts, optional claims, and an optional fusion
  condition assessment.
- `createInvestigationSession(input)` wraps a package with required observables,
  reports, limitations, and session status.
- `addDiagnosticArtifact(session, artifact)` appends one measured, derived,
  synthetic, testimony, or unknown-provenance artifact.
- `addInvestigationClaim(session, claim)` appends a claim after checking that all
  evidence artifact IDs exist in the package.
- `assessInvestigationSession(session)` returns measurement gaps and whether the
  session is ready for report generation.
- `createInvestigationSessionReport(session, options)` creates an
  evidence-linked report from the session claims.
- `recordInvestigationReport(session, report)` appends a report and moves the
  session to `reported`.

## Status Model

```text
collecting_evidence
  evidence and claims are still incomplete

ready_for_report
  at least one diagnostic artifact and one claim are present

reported
  at least one InvestigationReport is attached
```

The schema enforces that `reported` sessions have reports, and that every report
belongs to the same `packageId` as the session package.

## Boundary Rules

- The external application converts its own objects into `InvestigationTarget`,
  `DiagnosticArtifact`, and `InvestigationClaim`.
- OpenPlazma does not infer source identity from a single artifact.
- Missing observables remain gaps, not proof of absence.
- Claims must keep evidence artifact IDs explicit.
- Reports remain JSON artifacts that an external application can store, display,
  or use for its own progression logic.

## Validation

Use schema validation before persisting or exchanging session JSON:

```ts
import { parseInvestigationSession } from "@openplazma/schema";

const validated = parseInvestigationSession(session);
```

The same fixture/report validation remains available:

```sh
python scripts/validate-investigation-fixtures.py
```
