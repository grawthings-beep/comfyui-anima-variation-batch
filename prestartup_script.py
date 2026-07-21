#!/usr/bin/env python3
"""Self-bootstrap dependencies for direct-clone and baked ComfyUI images."""

from __future__ import annotations

import pathlib
import sys
import traceback

REPO_ROOT = pathlib.Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    # ComfyUI loads prestartup scripts with importlib, which does not guarantee
    # that the custom-node repository itself is importable.
    sys.path.insert(0, str(REPO_ROOT))

from scripts.install_anima_controls import main as install_anima_controls


def bootstrap() -> None:
    # ComfyUI executes this file before it imports torch or discovers custom
    # nodes. This makes dependencies cloned here visible during the same boot.
    comfy_root = REPO_ROOT.parents[1]
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
