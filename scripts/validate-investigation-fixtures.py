from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SDK_ROOT = REPO_ROOT / "python" / "openplazma"

if str(PYTHON_SDK_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_SDK_ROOT))

import openplazma as op  # noqa: E402


def main() -> int:
    entries = op.list_static_investigation_packages(REPO_ROOT)
    if not entries:
        raise ValueError("No static investigation packages are registered.")

    for entry in entries:
        package = op.load_static_investigation_package(REPO_ROOT, entry["packageId"])
        report = op.create_investigation_report(package)
        op.validate_investigation_report(report, package=package)

    print(f"Validated {len(entries)} static investigation package(s) and draft report(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
