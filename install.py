#!/usr/bin/env python3
"""ComfyUI-Manager hook for the required workflow model assets."""

from scripts.install_anima_controls import main as install_anima_controls


# ControlNet Aux downloads its own preprocessor checkpoints on first use. Keep
# the Manager hook lightweight: install the two LLLite patches, AnimeSharp
# upscaler (~98 MB total), and workflow. The full installer eagerly installs
# the preprocessor checkpoints too.
MANAGER_INSTALL_ARGUMENTS = (
    "--skip-controlnet-aux",
    "--skip-python-deps",
    "--skip-preprocessor-models",
)


if __name__ == "__main__":
    install_anima_controls(list(MANAGER_INSTALL_ARGUMENTS))
