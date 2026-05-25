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
    parser = argparse.ArgumentParser(description="Export a read-only local OpenPlazma Observatory HTML report.")
    parser.add_argument("--run-store", default=".openplazma", help="Path to the local OpenPlazma RunStore.")
    parser.add_argument("--output-dir", default=None, help="Optional output directory. Defaults to RUN_STORE/observatory.")
    parser.add_argument("--compare", nargs=2, metavar=("RUN_A", "RUN_B"), help="Also export a compare page for two Run IDs.")
    args = parser.parse_args()

    try:
        if args.compare:
            compare_path = op.export_observatory_compare_html(
                args.compare[0],
                args.compare[1],
                run_store=args.run_store,
                output_dir=args.output_dir,
            )
            output_dir = compare_path.parents[1]
        else:
            output_dir = op.export_observatory_html(run_store=args.run_store, output_dir=args.output_dir)
    except (FileNotFoundError, ValueError) as error:
        print(f"Could not export Observatory: {error}", file=sys.stderr)
        return 1

    print(f"OpenPlazma Observatory written to {Path(output_dir) / 'index.html'}")
    if args.compare:
        print(f"OpenPlazma Observatory compare page written to {compare_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
