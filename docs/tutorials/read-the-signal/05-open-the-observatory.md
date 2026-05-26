# 05 Open The Observatory

Open the local Observatory:

```text
.openplazma/observatory/index.html
```

## Inspect The Run List

Look for:

- Run IDs.
- Project and Campaign.
- Run status.
- Source provider.
- Target type.
- Artifact count.
- Metric count.

## Open A Run Detail Page

The detail page shows:

- Run metadata.
- Source and Target.
- Capabilities.
- Limitations.
- Metrics.
- Artifacts.
- Events.

## Capability Check

Confirm the safe Capability boundary:

- `controlFacility` is false.
- `readFacilityTelemetry` is false.
- `submitComputeJob` is false.
- `runSimulation` is false.

## Mission Boundary

Observatory is local, static, and read-only.
The generated HTML does not require external network references.
The public Pages demo does not inspect a user's local `.openplazma/` directory.
