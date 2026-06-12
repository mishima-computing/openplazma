from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import math
import re
from typing import Any

_ISO_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")


def require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object.")
    return dict(value)


def require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list.")
    return value


def require_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{name} must be a non-empty string.")
    return value


def require_iso_datetime(value: Any, name: str) -> str:
    timestamp = require_string(value, name)
    if _ISO_DATETIME_RE.fullmatch(timestamp) is None:
        raise ValueError(f"{name} must be an ISO datetime with a timezone offset.")
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO datetime with a timezone offset.") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must be an ISO datetime with a timezone offset.")
    return timestamp


def require_finite_number(value: Any, name: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number.")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number.")
    if positive and number <= 0:
        raise ValueError(f"{name} must be positive.")
    if nonnegative and number < 0:
        raise ValueError(f"{name} must be nonnegative.")
    return number


def require_number_list(value: Any, name: str) -> list[float]:
    values = require_list(value, name)
    for item in values:
        if not isinstance(item, (int, float)) or isinstance(item, bool):
            raise ValueError(f"{name} must contain only numbers.")
    return [float(item) for item in values]


def require_keys(value: Mapping[str, Any], keys: list[str], name: str) -> None:
    missing = [key for key in keys if key not in value]
    if missing:
        raise ValueError(f"{name} is missing required field(s): {', '.join(missing)}.")
