from __future__ import annotations

import re
from typing import Any

from ._validation import require_keys, require_mapping, require_string

SUPPORTED_DATA_PROVIDERS = {"STATIC_FIXTURE", "LOCAL_SIGNAL_FILE"}
LOCAL_SIGNAL_VALIDATION_STATUS = "schema_validated"

_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def validate_data_provider(provider: Any, label: str) -> str:
    require_string(provider, label)
    if provider not in SUPPORTED_DATA_PROVIDERS:
        raise ValueError(f"{label} must be STATIC_FIXTURE or LOCAL_SIGNAL_FILE.")
    return provider


def validate_source_ref(source: dict[str, Any], label: str) -> dict[str, Any]:
    source = require_mapping(source, label)
    require_keys(source, ["provider", "sourceLabel"], label)
    provider = validate_data_provider(source["provider"], f"{label}.provider")
    require_string(source["sourceLabel"], f"{label}.sourceLabel")

    if source.get("inspiredBy") is not None and source["inspiredBy"] != "FAIR_MAST":
        raise ValueError(f"{label}.inspiredBy must be FAIR_MAST when provided.")

    if provider == "LOCAL_SIGNAL_FILE":
        require_keys(source, ["uri", "sha256", "validationStatus"], label)
        require_string(source["uri"], f"{label}.uri")
        require_string(source["sha256"], f"{label}.sha256")
        require_string(source["validationStatus"], f"{label}.validationStatus")
        if not _SHA256_RE.fullmatch(source["sha256"]):
            raise ValueError(f"{label}.sha256 must be a lowercase SHA-256 hex digest.")
        if source["validationStatus"] != LOCAL_SIGNAL_VALIDATION_STATUS:
            raise ValueError(f"{label}.validationStatus must be {LOCAL_SIGNAL_VALIDATION_STATUS}.")

    return source
