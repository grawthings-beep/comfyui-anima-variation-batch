#!/usr/bin/env python3
"""ComfyUI-Manager hook for the small, required Anima LLLite assets."""

from scripts.install_anima_controls import main as install_anima_controls


# ControlNet Aux downloads its own preprocessor checkpoints on first use. Keep
# the Manager hook lightweight: install only the two LLLite patches (~31 MB)
# and the workflow. The full installer remains available for eager setup.
MANAGER_INSTALL_ARGUMENTS = (
    "--skip-controlnet-aux",
    "--skip-python-deps",
    "--skip-preprocessor-models",
)


if __name__ == "__main__":
    install_anima_controls(list(MANAGER_INSTALL_ARGUMENTS))
