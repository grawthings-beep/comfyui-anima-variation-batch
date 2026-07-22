#!/usr/bin/env python3
"""Self-bootstrap dependencies for direct-clone and baked ComfyUI images."""

from __future__ import annotations

import importlib.util
import pathlib
import traceback

REPO_ROOT = pathlib.Path(__file__).resolve().parent
INSTALLER_PATH = REPO_ROOT / "scripts" / "install_anima_controls.py"


def load_installer():
    # Loading by file path avoids adding this repository to sys.path. A
    # top-level path entry here can shadow ComfyUI's own modules during boot.
    spec = importlib.util.spec_from_file_location(
        "anima_controls_bootstrap_installer",
        INSTALLER_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load installer: {INSTALLER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main


def bootstrap() -> None:
    # ComfyUI executes this file before it imports torch or discovers custom
    # nodes. This makes dependencies cloned here visible during the same boot.
    comfy_root = REPO_ROOT.parents[1]
    install_anima_controls = load_installer()
    install_anima_controls(
        [
            "--root",
            str(comfy_root),
            "--skip-preprocessor-models",
        ]
    )


try:
    bootstrap()
except BaseException:  # ComfyUI must log the real bootstrap failure clearly.
    print("[Anima controls] automatic bootstrap failed:")
    traceback.print_exc()
