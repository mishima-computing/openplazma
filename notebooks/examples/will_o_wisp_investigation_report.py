from __future__ import annotations

import os
from pathlib import Path

import openplazma as op


REPO_ROOT = Path(__file__).resolve().parents[2]


def main(output_dir: str | Path | None = None) -> Path:
    # STATIC_FIXTURE-only, local-only investigation report example for Python or local Jupyter use.
    selected_output_dir = Path(output_dir or os.environ.get("OPENPLAZMA_INVESTIGATION_OUTPUT_DIR", ".openplazma/investigation-reports"))
    package = op.load_static_investigation_package(REPO_ROOT, "will-o-wisp-001")
    summary = op.summarize_investigation_package(package)
    report = op.create_investigation_report(
        package,
        next_observations=[
            "Add calibrated current, spectrum, neutron, gamma, and particle diagnostics before any fusion claim."
        ],
    )

    output_path = selected_output_dir / "will-o-wisp-001-investigation-report.json"
    op.save_investigation_report(report, output_path, package=package)

    print(f"OpenPlazma investigation package: {summary['title']}")
    print(f"Fusion status: {summary['fusionStatus']}")
    print(f"Report written to {output_path}")
    return output_path


if __name__ == "__main__":
    main()
