from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")


REPO_ROOT = Path(__file__).parents[3]
WORKBENCH_OPENPLAZMA = REPO_ROOT / "apps" / "workbench-lite" / "files" / "openplazma"


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_prepare_workbench_lite_outputs_current_fixture_files():
    prepare = load_module("prepare_workbench_lite", REPO_ROOT / "scripts" / "prepare-workbench-lite.py")

    assert prepare.main() == 0

    context = json.loads((WORKBENCH_OPENPLAZMA / "sample-experiment-context.json").read_text(encoding="utf-8"))
    signal = json.loads((WORKBENCH_OPENPLAZMA / "signals" / "plasma_current.json").read_text(encoding="utf-8"))

    assert context["shotRef"]["provider"] == "STATIC_FIXTURE"
    assert context["signals"][0]["signalId"] == "plasma-current"
    assert signal["signalId"] == "plasma-current"


def test_openplazma_lite_loads_fallback_context_and_signal():
    lite = load_module("openplazma_lite", WORKBENCH_OPENPLAZMA / "openplazma_lite.py")

    context = lite.load_context_from_file(WORKBENCH_OPENPLAZMA / "sample-experiment-context.json")
    signal = lite.load_signal(WORKBENCH_OPENPLAZMA / "signals" / "plasma_current.json")

    assert context["shotRef"]["provider"] == "STATIC_FIXTURE"
    assert signal["signalId"] == "plasma-current"


def test_openplazma_lite_plot_signal_runs_with_non_interactive_backend():
    lite = load_module("openplazma_lite_plot", WORKBENCH_OPENPLAZMA / "openplazma_lite.py")
    signal = lite.load_signal(WORKBENCH_OPENPLAZMA / "signals" / "plasma_current.json")

    figure = lite.plot_signal(signal, time_range=[0.0, 0.05])

    assert figure.axes[0].get_title() == "Plasma Current"
