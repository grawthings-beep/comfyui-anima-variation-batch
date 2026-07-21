# Third-Party Notices

## ComfyUI

The workflow examples in this repository are intended for
[Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI), which is licensed
under GPL-3.0.

The source code in this repository is distributed under GPL-3.0-only.

## Anima

This repository does not distribute Anima model, LoRA, or LLLite weights. The
official Anima model and derivatives, including the Pose and Depth LLLite
patches downloaded by the installer, are restricted to non-commercial model
use by the CircleStone Labs Non-Commercial License and may also be subject to
NVIDIA's license terms.

See the [official Anima model card](https://huggingface.co/circlestone-labs/Anima)
before using or distributing model derivatives.

The LLLite download metadata points to
[Comfy-Org/Anima-LLLite](https://huggingface.co/Comfy-Org/Anima-LLLite), which
mirrors the sample patches published by
[kohya-ss/Anima-LLLite](https://huggingface.co/kohya-ss/Anima-LLLite).

## Control preprocessors

The optional installer fetches
[ComfyUI ControlNet Aux](https://github.com/Fannovel16/comfyui_controlnet_aux),
[DWPose](https://github.com/IDEA-Research/DWPose), and
[Depth Anything V2](https://github.com/DepthAnything/Depth-Anything-V2)
components. Their upstream source repositories declare the Apache-2.0 license,
but individual detector weights, transitive components, and OpenPose-derived
code may carry additional terms. Nothing from those projects is copied into
this repository; users should review the upstream notices before installation
or redistribution.
