# Real Data Fixtures

OpenPlazma keeps small public-observation snapshots under `data/fixtures/real/`.

These files are not live telemetry. They are frozen local snapshots with raw source files, digests, provenance, and a normalized `openplazma.study_record` payload. They are intended for testing ingestion, schema validation, Observatory export, and analysis workflows against measured data without adding a network dependency to normal tests.

## NOAA SWPC L1 Solar Wind And GOES X-Ray Snapshot

The first real fixture is:

```text
data/fixtures/real/noaa-swpc-l1-6h-20260612/
```

It includes:

- raw NOAA SWPC plasma JSON: `raw/plasma-6-hour.json`
- raw NOAA SWPC magnetometer JSON: `raw/mag-6-hour.json`
- raw NOAA SWPC GOES X-ray JSON: `raw/xrays-6-hour.json`
- source provenance and raw-file SHA-256 digests: `source-provenance.json`
- normalized OpenPlazma study record: `study-record.json`

The normalized record preserves:

- solar wind proton density, speed, and proton temperature
- interplanetary magnetic field `Bt` and GSM `Bz`
- GOES X-ray corrected flux, observed flux, and electron-correction traces for the `0.05-0.4 nm` and `0.1-0.8 nm` bands

This deliberately keeps light as a time-varying spectral measurement instead of collapsing it into a binary light/no-light flag.

## Public Observation Campaign

The NOAA snapshot can now be run through a read-only investigation session,
RunStore logging, and static Observatory export:

```sh
python3 scripts/run-public-observation-campaign.py --run-store .openplazma/public-observation --clean
```

The campaign loads only the frozen local fixture. It does not fetch live NOAA
data, read facility telemetry, or expose facility control. It logs the public
snapshot, source provenance, selected signals, spectrum/frequency artifacts,
investigation package, session, assessment, and report to RunStore before
exporting the local Observatory.

The default NOAA evidence package is intentionally conservative: the fusion
disposition is `unsupported` because the public snapshot has useful signal and
frequency metadata but no calibrated fusion-product or fusion-condition
evidence. The generated report lists calibrated product and condition
measurements as next observations.

## Refreshing

To fetch a fresh NOAA SWPC 6-hour snapshot and regenerate the normalized fixture:

```sh
.venv/bin/python scripts/fetch-noaa-swpc-real-fixture.py
```

The script downloads from SWPC public JSON endpoints and updates `data/fixtures/real/manifest.json`.

## Limitations

- SWPC real-time endpoints are mutable operational products.
- The repository snapshot is frozen; future endpoint data will differ.
- OpenPlazma normalizes and validates the payload but does not apply independent instrument calibration.
- L1 solar wind observations are not direct solar-core measurements.
- GOES X-ray and solar wind observations do not by themselves prove fusion reaction conditions.
- These fixtures are read-only analysis data and provide no command/control path.
