from __future__ import annotations

import importlib.util
import runpy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def load_pages_build_module():
    spec = importlib.util.spec_from_file_location(
        "openplazma_build_pages_site",
        REPO_ROOT / "scripts" / "build-pages-site.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pages_build_script_constants() -> None:
    script = runpy.run_path(REPO_ROOT / "scripts" / "build-pages-site.py")

    assert script["PAGES_DIR"] == REPO_ROOT / "dist" / "pages"
    assert script["PAGES_WORKBENCH_DIR"] == REPO_ROOT / "dist" / "pages" / "workbench"
    assert script["LAB_BASE_PATH"] == "./"
    assert (
        script["PAGES_WORKBENCH_LITE_URL"]
        == "/openplazma/workbench/lab/index.html?path=openplazma/experiment_notebook.ipynb"
    )


def test_hygiene_rejects_pages_build_outputs() -> None:
    script = runpy.run_path(REPO_ROOT / "scripts" / "check-public-repo-hygiene.py")

    assert script["path_reasons"]("dist/pages/index.html")
    assert script["path_reasons"]("dist/pages/workbench/lab/index.html")
    assert script["path_reasons"]("apps/workbench-lite/_output/lab/index.html")


def test_jupyter_lite_command_falls_back_to_current_venv_scripts_dir(tmp_path, monkeypatch):
    module = load_pages_build_module()
    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    fake_python = venv_bin / "python"
    fake_python.write_text("", encoding="utf-8")
    fake_jupyter_lite = venv_bin / "jupyter-lite"
    fake_jupyter_lite.write_text("#!/bin/sh\n", encoding="utf-8")
    fake_jupyter_lite.chmod(0o755)

    monkeypatch.setattr(module.shutil, "which", lambda _name: None)
    monkeypatch.setattr(module.sys, "executable", str(fake_python))

    assert module.jupyter_lite_command() == [str(fake_jupyter_lite)]
