# Investigate Will-o'-the-wisp

Mission: inspect the first unknown-energy investigation package, keep plasma and
fusion claims separate, and write a validated evidence report.

Expected time:

- Browser path: 10 minutes.
- Local Python path: 10 minutes after the SDK is installed.

## What You Will Inspect

The package is `will-o-wisp-001`:

- target: atmospheric light
- candidate sources: chemical luminescence, combustion, electrical discharge,
  plasma, sensor artifact, fusion
- available evidence: human visual report, low-rate brightness trace, coarse
  visible spectrum
- missing or unresolved evidence: calibrated current, fusion products, particle
  diagnostics, gamma diagnostics, neutron diagnostics, and direct plasma
  maintenance conditions

The correct first result can be conservative: the supplied evidence does not
support a fusion claim.

## Browser Path

1. Open the OpenPlazma Lab.
2. Find the Investigation Workbench below the selected signal workspace.
3. Select `will-o-wisp-001`.
4. Inspect the Target, Missing observables, Unresolved artifacts, Diagnostic
   artifacts, and Claims sections.
5. Use Report Builder to keep a claim tied to explicit evidence artifact IDs.
6. Review the JSON preview before exporting.

The public browser path uses `STATIC_FIXTURE` data only. It does not fetch live
weather, astronomy, facility, or sensor data.

## Local Python Path

Install the SDK from the repository root if needed:

```sh
cd python/openplazma
python -m pip install -e ".[dev]"
cd ../..
```

Create a local report:

```sh
python notebooks/examples/will_o_wisp_investigation_report.py
```

The example writes:

```text
.openplazma/investigation-reports/will-o-wisp-001-investigation-report.json
```

The generated file is local output and must not be committed.

## Minimal Notebook Cells

```python
from pathlib import Path

import openplazma as op

repo = Path.cwd()
package = op.load_static_investigation_package(repo, "will-o-wisp-001")
summary = op.summarize_investigation_package(package)
summary
```

```python
report = op.create_investigation_report(
    package,
    next_observations=[
        "Add calibrated current, spectrum, neutron, gamma, and particle diagnostics before any fusion claim."
    ],
)
op.save_investigation_report(
    report,
    ".openplazma/investigation-reports/will-o-wisp-001-investigation-report.json",
    package=package,
)
```

## CI Check

Validate all static investigation packages and draft reports:

```sh
python scripts/validate-investigation-fixtures.py
```

This check is intentionally read-only. It validates fixture contracts and report
shape; it does not grade a claim as physically true.

## Mission Boundary

This tutorial is not a reactor workflow. It is an evidence workflow.

The package starts from an unknown luminous phenomenon. It does not assume the
light is plasma, and it does not assume plasma implies fusion. Human vision,
brightness traces, and visible spectra are useful evidence, but they cannot
separate plasma light, thermal light, chemical light, fusion products, and
instrument artifacts without calibration and additional diagnostics.
