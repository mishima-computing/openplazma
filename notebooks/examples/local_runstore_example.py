from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_local_tracking_example():
    path = Path(__file__).with_name("local_tracking_notebook.py")
    spec = importlib.util.spec_from_file_location("openplazma_local_tracking_notebook", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load local_tracking_notebook.py.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    _load_local_tracking_example().main()
