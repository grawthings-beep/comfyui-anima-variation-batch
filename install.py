#!/usr/bin/env python3
"""ComfyUI-Manager hook for the required workflow model assets."""

from scripts.install_anima_controls import main as install_anima_controls


# ControlNet Aux downloads its own preprocessor checkpoints on first use. The
# Manager hook installs both required node packs, the two LLLite patches,
# AnimeSharp (~98 MB total), and the workflow. The full CLI installer can also
# preload the larger preprocessor checkpoints.
MANAGER_INSTALL_ARGUMENTS = (
    "--skip-preprocessor-models",
)


if __name__ == "__main__":
    install_anima_controls(list(MANAGER_INSTALL_ARGUMENTS))
