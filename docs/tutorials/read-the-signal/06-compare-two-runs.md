# 06 Compare Two Runs

Open the generated Compare page under:

```text
.openplazma/observatory/compare/
```

## What To Look For

Compare shows:

- Metric comparison.
- Artifact comparison.
- Source comparison.
- Target comparison.
- Capabilities comparison.
- Limitations comparison.

Compare is two-Run only in this MVP.

## Artifact Links

Artifact links are local relative links. They are allowed only when canonical resolution stays inside the intended local RunStore artifact directory.

## Mission Boundary

Compare is local, static, and read-only.
It does not sync to a cloud service.
It does not provide a hosted Observatory.
