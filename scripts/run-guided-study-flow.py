from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SDK_ROOT = REPO_ROOT / "python" / "openplazma"
GUIDED_EXAMPLE = REPO_ROOT / "notebooks" / "examples" / "read_the_signal_guided_flow.py"
if str(PYTHON_SDK_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_SDK_ROOT))

import openplazma as op  # noqa: E402


def _load_guided_example_main():
    spec = importlib.util.spec_from_file_location("openplazma_guided_flow_example", GUIDED_EXAMPLE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load guided StudyFlow example.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local OpenPlazma guided StudyFlow smoke workflow.")
    parser.add_argument("--run-store", default=".openplazma", help="Path to the local OpenPlazma RunStore.")
    parser.add_argument("--clean", action="store_true", help="Remove the selected RunStore before running.")
    args = parser.parse_args()

    run_store = Path(args.run_store)
    if args.clean and run_store.exists():
        shutil.rmtree(run_store)

    guided_main = _load_guided_example_main()
    run_a = guided_main(run_store=run_store)
    run_b = guided_main(run_store=run_store)
    observatory_dir = op.export_observatory_html(run_store=run_store)
    compare_path = op.export_observatory_compare_html(run_a, run_b, run_store=run_store)

    print(f"OpenPlazma guided StudyFlow Run A: {run_store / 'runs' / run_a}")
    print(f"OpenPlazma guided StudyFlow Run B: {run_store / 'runs' / run_b}")
    print(f"OpenPlazma Observatory index: {observatory_dir / 'index.html'}")
    print(f"OpenPlazma Observatory compare page: {compare_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
