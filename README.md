# ComfyUI Anima Hires-Fix Workflows

[![CI](https://github.com/grawthings-beep/comfyui-anima-variation-batch/actions/workflows/ci.yml/badge.svg)](https://github.com/grawthings-beep/comfyui-anima-variation-batch/actions/workflows/ci.yml)

This repository contains two Anima-focused 2-pass Hires-fix upscale example
workflows. The old experimental workflow set has been removed.

## Install

From the ComfyUI custom node directory:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/grawthings-beep/comfyui-anima-variation-batch.git \
  ComfyUI-AnimaHiresFixWorkflows
```

Restart ComfyUI, then load one of:

```text
example_workflows/anima_hiresfix_esrgan_2pass.json
example_workflows/anima_hiresfix_latent_2pass.json
```

For common RunPod images, the ComfyUI root is often one of:

```text
/opt/ComfyUI
/workspace/ComfyUI
/workspace/comfyui
```

## Hires-fix upscale workflows

Both workflows expect the Anima base stack:

```text
models/diffusion_models/anima-base-v1.0.safetensors
models/text_encoders/qwen_3_06b_base.safetensors
models/vae/qwen_image_vae.safetensors
```

`anima_hiresfix_esrgan_2pass.json` starts at 832x1216, upscales the first
pass with a 4x ESRGAN model, resizes to an effective 1.5x with Lanczos,
VAE-re-encodes, then runs a second pass. It additionally needs an anime ESRGAN
upscaler such as:

```text
models/upscale_models/4x-AnimeSharp.pth
```

The default second-pass denoise is `0.45`. Tune around `0.35` to `0.55`,
lowering it to preserve the first pass or raising it for stronger detail
redraw.

`anima_hiresfix_latent_2pass.json` uses only ComfyUI core nodes: it upscales
the latent by 1.5x with bislerp, then runs a second pass. The default
second-pass denoise is `0.55`. Tune around `0.50` to `0.60` depending on how
much structure you want the second pass to revise.

## Model downloads

For the ESRGAN Hires-fix workflow:

```bash
COMFY=/workspace/ComfyUI
[ -d "$COMFY" ] || COMFY=/workspace/comfyui
[ -d "$COMFY" ] || COMFY=/opt/ComfyUI

mkdir -p "$COMFY/models/upscale_models"
wget -O "$COMFY/models/upscale_models/4x-AnimeSharp.pth" \
  "https://objectstorage.us-phoenix-1.oraclecloud.com/n/ax6ygfvpvzka/b/open-modeldb-files/o/4x-FatePlus-lite.pth"
```

## License

GPL-3.0-only. See `LICENSE`.

This repository does not distribute Anima, Qwen, or upscaler weights. Check the
license of every model used in your workflow. The official Anima model and
derivatives are restricted to non-commercial use unless a commercial license is
obtained.

- [Official Anima model card](https://huggingface.co/circlestone-labs/Anima)
- [ComfyUI](https://github.com/Comfy-Org/ComfyUI)
