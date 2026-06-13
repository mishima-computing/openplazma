from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SDK_ROOT = REPO_ROOT / "python" / "openplazma"
EXAMPLE = REPO_ROOT / "notebooks" / "examples" / "investigation_session_run.py"
if str(PYTHON_SDK_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_SDK_ROOT))


def _load_example_main():
    spec = importlib.util.spec_from_file_location("openplazma_investigation_session_run", EXAMPLE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load investigation_session_run.py.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local OpenPlazma investigation session example.")
    parser.add_argument("--run-store", default=".openplazma", help="Path to the local OpenPlazma RunStore.")
    parser.add_argument("--clean", action="store_true", help="Remove the selected RunStore before running.")
    args = parser.parse_args()

    run_store = Path(args.run_store)
    if args.clean and run_store.exists():
        shutil.rmtree(run_store)

    run_id = _load_example_main()(run_store=run_store)
    print(f"OpenPlazma investigation session RunStore path: {run_store / 'runs' / run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
