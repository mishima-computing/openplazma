from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import openplazma as op


REPO_ROOT = Path(__file__).parents[3]


def test_plot_signal_runs_with_non_interactive_backend():
    signal = op.load_static_signal(REPO_ROOT, "sample-001", "plasma-current")
    figure = op.plot_signal(signal, time_range=[0.0, 0.05], markers=[0.02])

    assert figure.axes[0].get_title() == "Plasma Current"
