from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SDK_ROOT = REPO_ROOT / "python" / "openplazma"
if str(PYTHON_SDK_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_SDK_ROOT))

import openplazma as op  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the frozen NOAA public observation lineage audit ensemble."
    )
    parser.add_argument("--run-store", default=".openplazma", help="Path to the local OpenPlazma RunStore.")
    parser.add_argument("--output-dir", default=None, help="Optional Observatory output directory.")
    parser.add_argument("--shot-id", default="noaa-swpc-l1-6h-20260612", help="Public observation snapshot shot id.")
    parser.add_argument(
        "--signal-id",
        action="append",
        dest="signal_ids",
        help="Signal id to include. Repeat for multiple signals. Defaults to the representative NOAA set.",
    )
    parser.add_argument(
        "--max-frequency-hz",
        type=float,
        default=None,
        help="Optional upper frequency bound for computed spectra.",
    )
    parser.add_argument("--clean", action="store_true", help="Remove the selected RunStore before running.")
    args = parser.parse_args()

    result = op.run_public_observation_lineage_audit_ensemble(
        repo_root=REPO_ROOT,
        run_store=Path(args.run_store),
        output_dir=Path(args.output_dir) if args.output_dir is not None else None,
        shot_id=args.shot_id,
        signal_ids=args.signal_ids,
        max_frequency_hz=args.max_frequency_hz,
        clean=args.clean,
    )
    print(f"OpenPlazma public observation lineage audit runGroup: {result['runGroupId']}")
    print(f"RunStore path: {result['runStorePath']}")
    print(f"Observatory path: {result['observatoryPath']}")
    for partition in result["partitions"]:
        print(
            "Partition "
            f"{partition['partitionId']} {partition['timeWindow']}: "
            f"{partition['runId']} audit={partition['auditStatus']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
