from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = REPO_ROOT / "dist"
PAGES_DIR = DIST_ROOT / "pages"
LAB_BUILD_DIR = DIST_ROOT / "pages-lab"
WORKBENCH_LITE_DIR = REPO_ROOT / "apps" / "workbench-lite"
WORKBENCH_OUTPUT_DIR = WORKBENCH_LITE_DIR / "_output"
PAGES_WORKBENCH_DIR = PAGES_DIR / "workbench"

LAB_BASE_PATH = "./"
PAGES_WORKBENCH_LITE_URL = "/openplazma/workbench/lab/index.html?path=openplazma/experiment_notebook.ipynb"


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print(f"Running: {' '.join(command)}")
    subprocess.run(command, cwd=REPO_ROOT, env=env, check=True)


def command_on_path(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise RuntimeError(f"Could not find required command on PATH: {name}")
    return executable


def jupyter_lite_command() -> list[str]:
    jupyter = shutil.which("jupyter")
    if jupyter is not None:
        return [jupyter, "lite"]

    jupyter_lite = shutil.which("jupyter-lite")
    if jupyter_lite is not None:
        return [jupyter_lite]

    scripts_dir = Path(sys.executable).resolve().parent / ("Scripts" if os.name == "nt" else "bin")
    executable = scripts_dir / ("jupyter-lite.exe" if os.name == "nt" else "jupyter-lite")
    if executable.exists():
        return [str(executable)]

    raise RuntimeError("Could not find jupyter lite or jupyter-lite on PATH.")


def clean_outputs() -> None:
    for path in [PAGES_DIR, LAB_BUILD_DIR, WORKBENCH_OUTPUT_DIR]:
        if path.exists():
            shutil.rmtree(path)


def build_lab() -> None:
    env = {
        **os.environ,
        "VITE_OPENPLAZMA_BASE_PATH": LAB_BASE_PATH,
    }
    run(
        [
            command_on_path("corepack"),
            "pnpm",
            "--filter",
            "@openplazma/lab",
            "exec",
            "vite",
            "build",
            "--outDir",
            "../../dist/pages-lab",
            "--emptyOutDir",
        ],
        env=env,
    )


def build_workbench() -> None:
    command = jupyter_lite_command()
    run(
        [
            *command,
            "build",
            "--lite-dir",
            "apps/workbench-lite",
            "--output-dir",
            "apps/workbench-lite/_output",
        ]
    )
    run(
        [
            *command,
            "check",
            "--lite-dir",
            "apps/workbench-lite",
            "--output-dir",
            "apps/workbench-lite/_output",
        ]
    )


def assemble_pages_site() -> None:
    shutil.copytree(LAB_BUILD_DIR, PAGES_DIR)
    shutil.copytree(WORKBENCH_OUTPUT_DIR, PAGES_WORKBENCH_DIR)
    (PAGES_DIR / ".nojekyll").write_text("", encoding="utf-8")
    shutil.rmtree(LAB_BUILD_DIR)


def main() -> int:
    clean_outputs()
    run([sys.executable, "scripts/prepare-workbench-lite.py"])
    build_lab()
    build_workbench()
    assemble_pages_site()
    print("Pages site built:")
    print(f"- Lab: {PAGES_DIR / 'index.html'}")
    print(f"- Workbench: {PAGES_WORKBENCH_DIR / 'lab' / 'index.html'}")
    print(f"- No Jekyll marker: {PAGES_DIR / '.nojekyll'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
