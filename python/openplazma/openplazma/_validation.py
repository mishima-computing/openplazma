from __future__ import annotations

from collections.abc import Mapping
from typing import Any


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
