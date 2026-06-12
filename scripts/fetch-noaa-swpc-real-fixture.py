#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "data" / "fixtures" / "real" / "noaa-swpc-l1-6h-20260612"
REAL_MANIFEST = REPO_ROOT / "data" / "fixtures" / "real" / "manifest.json"

SOURCES = {
    "plasma-6-hour.json": "https://services.swpc.noaa.gov/products/solar-wind/plasma-6-hour.json",
    "mag-6-hour.json": "https://services.swpc.noaa.gov/products/solar-wind/mag-6-hour.json",
    "xrays-6-hour.json": "https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json",
}

SOURCE_PAGES = [
    "https://www.swpc.noaa.gov/products/real-time-solar-wind",
    "https://www.swpc.noaa.gov/products/goes-x-ray-flux",
    "https://www.swpc.noaa.gov/content/data-access",
]


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_noaa_time(value: str) -> datetime:
    if "T" in value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)


def finite_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def table_rows(payload: list[list[Any]]) -> list[dict[str, Any]]:
    header = payload[0]
    return [dict(zip(header, row, strict=False)) for row in payload[1:]]


def make_series(
    *,
    signal_id: str,
    label: str,
    quantity: str,
    unit: str,
    timestamps: list[datetime],
    values: list[float],
    epoch: datetime,
) -> dict[str, Any]:
    paired = sorted(zip(timestamps, values, strict=True), key=lambda item: item[0])
    unique_times: list[float] = []
    unique_values: list[float] = []
    last_time: datetime | None = None
    for timestamp, value in paired:
        if timestamp == last_time:
            continue
        unique_times.append(round((timestamp - epoch).total_seconds(), 3))
        unique_values.append(value)
        last_time = timestamp
    return {
        "kind": "openplazma.signal_series",
        "version": "0.1.0",
        "signalId": signal_id,
        "label": label,
        "quantity": quantity,
        "unit": unit,
        "timeUnit": "s",
        "time": unique_times,
        "values": unique_values,
    }


def series_from_table(
    payload: list[list[Any]],
    *,
    signal_id: str,
    label: str,
    quantity: str,
    unit: str,
    column: str,
    epoch: datetime,
) -> dict[str, Any]:
    timestamps: list[datetime] = []
    values: list[float] = []
    for row in table_rows(payload):
        value = finite_float(row.get(column))
        if value is None:
            continue
        timestamps.append(parse_noaa_time(row["time_tag"]))
        values.append(value)
    return make_series(
        signal_id=signal_id,
        label=label,
        quantity=quantity,
        unit=unit,
        timestamps=timestamps,
        values=values,
        epoch=epoch,
    )


def series_from_xray(
    payload: list[dict[str, Any]],
    *,
    energy: str,
    field: str,
    signal_id: str,
    label: str,
    quantity: str,
    epoch: datetime,
) -> dict[str, Any]:
    timestamps: list[datetime] = []
    values: list[float] = []
    for row in payload:
        if row.get("energy") != energy:
            continue
        value = finite_float(row.get(field))
        if value is None:
            continue
        timestamps.append(parse_noaa_time(row["time_tag"]))
        values.append(value)
    return make_series(
        signal_id=signal_id,
        label=label,
        quantity=quantity,
        unit="W/m^2",
        timestamps=timestamps,
        values=values,
        epoch=epoch,
    )


def series_range(series: dict[str, Any]) -> tuple[float, float]:
    values = series["values"]
    return min(values), max(values)


def first_timestamp(*payloads: Any) -> datetime:
    timestamps: list[datetime] = []
    for payload in payloads:
        if isinstance(payload, list) and payload and isinstance(payload[0], list):
            timestamps.extend(parse_noaa_time(row["time_tag"]) for row in table_rows(payload) if row.get("time_tag"))
        else:
            timestamps.extend(parse_noaa_time(row["time_tag"]) for row in payload if row.get("time_tag"))
    return min(timestamps)


def last_timestamp(*payloads: Any) -> datetime:
    timestamps: list[datetime] = []
    for payload in payloads:
        if isinstance(payload, list) and payload and isinstance(payload[0], list):
            timestamps.extend(parse_noaa_time(row["time_tag"]) for row in table_rows(payload) if row.get("time_tag"))
        else:
            timestamps.extend(parse_noaa_time(row["time_tag"]) for row in payload if row.get("time_tag"))
    return max(timestamps)


def relpath(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch a small NOAA SWPC real-observation fixture.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    output = args.output.resolve()
    raw_dir = output / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    retrieved_at = utc_now()
    raw_files: list[dict[str, Any]] = []
    payloads: dict[str, Any] = {}
    for name, url in SOURCES.items():
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read()
        raw_path = raw_dir / name
        raw_path.write_bytes(content)
        raw_files.append(
            {
                "name": name,
                "url": url,
                "path": relpath(raw_path),
                "sha256": sha256_bytes(content),
                "bytes": len(content),
            }
        )
        payloads[name] = json.loads(content.decode("utf-8"))

    bundle_seed = json.dumps(raw_files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    bundle_sha256 = sha256_bytes(bundle_seed)
    provenance = {
        "kind": "openplazma.source_provenance",
        "version": "0.1.0",
        "provider": "NOAA_SWPC",
        "sourceLabel": "NOAA SWPC RTSW and GOES X-ray 6-hour public JSON snapshot",
        "retrievedAt": retrieved_at,
        "sourcePages": SOURCE_PAGES,
        "rawFiles": raw_files,
        "bundleSha256": bundle_sha256,
        "limitations": [
            "SWPC real-time endpoints are mutable operational data products.",
            "OpenPlazma stores this as a frozen local snapshot and does not apply additional calibration.",
        ],
    }
    provenance_path = output / "source-provenance.json"
    write_json(provenance_path, provenance)

    plasma = payloads["plasma-6-hour.json"]
    mag = payloads["mag-6-hour.json"]
    xrays = payloads["xrays-6-hour.json"]
    epoch = first_timestamp(plasma, mag, xrays)
    end = last_timestamp(plasma, mag, xrays)

    signals = [
        series_from_table(
            plasma,
            signal_id="solar-wind-proton-density",
            label="Solar Wind Proton Density",
            quantity="proton_density",
            unit="cm^-3",
            column="density",
            epoch=epoch,
        ),
        series_from_table(
            plasma,
            signal_id="solar-wind-speed",
            label="Solar Wind Speed",
            quantity="bulk_speed",
            unit="km/s",
            column="speed",
            epoch=epoch,
        ),
        series_from_table(
            plasma,
            signal_id="solar-wind-proton-temperature",
            label="Solar Wind Proton Temperature",
            quantity="proton_temperature",
            unit="K",
            column="temperature",
            epoch=epoch,
        ),
        series_from_table(
            mag,
            signal_id="imf-bt",
            label="Interplanetary Magnetic Field Bt",
            quantity="magnetic_field_magnitude",
            unit="nT",
            column="bt",
            epoch=epoch,
        ),
        series_from_table(
            mag,
            signal_id="imf-bz-gsm",
            label="Interplanetary Magnetic Field Bz GSM",
            quantity="magnetic_field_z_gsm",
            unit="nT",
            column="bz_gsm",
            epoch=epoch,
        ),
        series_from_xray(
            xrays,
            energy="0.05-0.4nm",
            field="flux",
            signal_id="goes-xray-short-flux",
            label="GOES X-ray Flux 0.05-0.4 nm",
            quantity="xray_flux_corrected_short_band",
            epoch=epoch,
        ),
        series_from_xray(
            xrays,
            energy="0.05-0.4nm",
            field="observed_flux",
            signal_id="goes-xray-short-observed-flux",
            label="GOES Observed X-ray Flux 0.05-0.4 nm",
            quantity="xray_flux_observed_short_band",
            epoch=epoch,
        ),
        series_from_xray(
            xrays,
            energy="0.05-0.4nm",
            field="electron_correction",
            signal_id="goes-xray-short-electron-correction",
            label="GOES X-ray Electron Correction 0.05-0.4 nm",
            quantity="xray_flux_electron_correction_short_band",
            epoch=epoch,
        ),
        series_from_xray(
            xrays,
            energy="0.1-0.8nm",
            field="flux",
            signal_id="goes-xray-long-flux",
            label="GOES X-ray Flux 0.1-0.8 nm",
            quantity="xray_flux_corrected_long_band",
            epoch=epoch,
        ),
        series_from_xray(
            xrays,
            energy="0.1-0.8nm",
            field="observed_flux",
            signal_id="goes-xray-long-observed-flux",
            label="GOES Observed X-ray Flux 0.1-0.8 nm",
            quantity="xray_flux_observed_long_band",
            epoch=epoch,
        ),
        series_from_xray(
            xrays,
            energy="0.1-0.8nm",
            field="electron_correction",
            signal_id="goes-xray-long-electron-correction",
            label="GOES X-ray Electron Correction 0.1-0.8 nm",
            quantity="xray_flux_electron_correction_long_band",
            epoch=epoch,
        ),
    ]

    shot_id = output.name
    source_ref = {
        "provider": "NOAA_SWPC",
        "sourceLabel": provenance["sourceLabel"],
        "uri": relpath(provenance_path),
        "sha256": bundle_sha256,
        "validationStatus": "schema_validated",
    }
    density_min, density_max = series_range(signals[0])
    bz_min, bz_max = series_range(signals[4])
    xray_min, xray_max = series_range(signals[8])

    signal_refs = [
        {
            "signalId": signal["signalId"],
            "label": signal["label"],
            "quantity": signal["quantity"],
            "unit": signal["unit"],
        }
        for signal in signals
    ]
    record = {
        "kind": "openplazma.study_record",
        "version": "0.1.0",
        "studyId": f"{shot_id}-study",
        "createdAt": retrieved_at,
        "source": {**source_ref, "shotId": shot_id},
        "shotRef": {"provider": "NOAA_SWPC", "shotId": shot_id},
        "signalsViewed": signal_refs,
        "observations": [
            {
                "text": (
                    "This record bundles NOAA SWPC public JSON measurements for solar wind plasma, "
                    "interplanetary magnetic field, and GOES X-ray flux."
                )
            },
            {
                "text": f"Solar wind proton density ranges from {density_min:g} to {density_max:g} cm^-3.",
                "signalId": "solar-wind-proton-density",
            },
            {
                "text": f"IMF Bz GSM ranges from {bz_min:g} to {bz_max:g} nT.",
                "signalId": "imf-bz-gsm",
            },
            {
                "text": f"GOES 0.1-0.8 nm corrected X-ray flux ranges from {xray_min:g} to {xray_max:g} W/m^2.",
                "signalId": "goes-xray-long-flux",
            },
            {
                "text": "The X-ray channels preserve wavelength-band and brightness variation instead of a binary light/no-light flag."
            },
        ],
        "limitations": [
            "NOAA SWPC public web observation snapshot only.",
            "SWPC real-time endpoints are mutable; this repository stores the downloaded snapshot and raw-file digests.",
            "OpenPlazma performs schema normalization only and does not apply independent instrument calibration.",
            "L1 solar wind observations are not direct solar-core measurements.",
            "GOES X-ray flux and solar wind observations do not by themselves prove fusion reaction conditions.",
            "Read-only analysis and decision support.",
            "No command/control path or hazardous operating procedure.",
        ],
        "context": {
            "kind": "openplazma.experiment_context",
            "version": "0.1.0",
            "contextId": f"ctx-{shot_id}",
            "projectId": "openplazma",
            "datasetId": "real-observation-v0",
            "campaign": "solar-public-web-snapshot",
            "description": "Read-only public NOAA SWPC solar plasma and X-ray observation snapshot.",
            "safetyClassification": "public-web-observation",
            "createdAt": retrieved_at,
            "target": {
                "type": "public_observation_dataset",
                "id": shot_id,
                "label": "NOAA SWPC public 6-hour snapshot",
            },
            "source": source_ref,
            "capabilities": {
                "readData": True,
                "writeArtifacts": True,
                "runSimulation": False,
                "submitComputeJob": False,
                "readFacilityTelemetry": False,
                "controlFacility": False,
            },
            "shotRef": {"provider": "NOAA_SWPC", "shotId": shot_id},
            "signals": signal_refs,
            "view": {"timeRange": [0, round((end - epoch).total_seconds(), 3)]},
            "observations": [
                {
                    "text": "Use this context as a real-data seed for public observation analysis, not as live telemetry."
                }
            ],
            "limitations": [
                "NOAA SWPC public web observation snapshot only.",
                "Read-only analysis and decision support.",
                "No command/control path or hazardous operating procedure.",
            ],
        },
        "shot": {
            "kind": "openplazma.shot_metadata",
            "version": "0.1.0",
            "shotId": shot_id,
            "displayName": "NOAA SWPC L1 Solar Wind and GOES X-ray 6-hour Snapshot",
            "sourceLabel": provenance["sourceLabel"],
            "deviceName": "DSCOVR/ACE RTSW and GOES primary XRS",
            "recordedAt": epoch.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "source": {
                "kind": "measured",
                **source_ref,
                "license": "NOAA public data",
            },
            "signalIds": [signal["signalId"] for signal in signals],
            "tags": ["real-data", "noaa-swpc", "solar-wind", "goes-xray", "public-web-observation"],
            "notes": (
                f"Frozen snapshot from {epoch.isoformat().replace('+00:00', 'Z')} "
                f"to {end.isoformat().replace('+00:00', 'Z')}."
            ),
        },
        "signals": signals,
    }

    write_json(output / "study-record.json", record)
    write_json(
        REAL_MANIFEST,
        {
            "kind": "openplazma.fixture_manifest",
            "version": "0.1.0",
            "provider": "NOAA_SWPC",
            "datasetId": "real-observation-v0",
            "shots": [
                {
                    "shotId": shot_id,
                    "path": relpath(output / "study-record.json"),
                }
            ],
        },
    )


if __name__ == "__main__":
    main()
